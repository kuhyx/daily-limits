/// One full sync pass, shared by the app and the 15-minute background task:
/// read the status, collect answers to unanswered requests, then update the
/// cache, the widget and the notifications from whatever is now known.
library;

import 'package:crdt_sync/crdt_sync.dart';
import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/services/home_widget_sync.dart';
import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/notifier.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_app.dart';

/// What a sync pass found.
class SyncOutcome {
  /// Creates an outcome.
  const new({
    required this.signedIn,
    required this.cache,
    this.status,
    this.parseError,
    this.locked = false,
  });

  /// Whether this device holds a Firebase session.
  final bool signedIn;

  /// Signed in, but the end-to-end key is unavailable (no or a wrong
  /// passphrase): nothing was read or written.
  final bool locked;

  /// The cache after the pass (status text, requests, last error).
  final LocalCache cache;

  /// The parsed status, or null when there is none or it is unreadable.
  final DailyStatus? status;

  /// Why the cached status text could not be parsed.
  final String? parseError;
}

/// Parses the cached status text, returning (status, error).
(DailyStatus?, String?) parseCached(String? text) {
  if (text == null) return (null, null);
  try {
    return (DailyStatus.parse(text), null);
  } on Object catch (error) {
    return (null, 'Unreadable status from the PC: $error');
  }
}

/// An outcome from the cached status text alone, with no Firebase read.
SyncOutcome cachedOutcome(LocalCache cache) {
  final (status, parseError) = parseCached(cache.statusText);
  return SyncOutcome(
    signedIn: cache.statusText != null,
    cache: cache,
    status: status,
    parseError: parseError,
  );
}

/// Runs one pass. Never throws: a failed read is recorded in the cache.
Future<SyncOutcome> syncOnce({
  StoreOpener open = openClient,
  Future<String> Function() device = deviceId,
}) async {
  final cache = await LocalCache.load();
  RemoteStore? client;
  var locked = false;
  try {
    client = await open();
  } on SyncLockedException {
    locked = true;
  } on Object catch (error) {
    cache.lastError = 'Sign-in failed: $error';
  }
  if (client != null) {
    try {
      cache
        ..statusText = await client.getFileText(kStatusPath)
        ..fetchedAt = DateTime.now()
        ..lastError = null;
    } on Object catch (error) {
      cache.lastError = 'Could not reach Firebase: $error';
    }
    await uploadQueued(client, cache, await device());
    await collectAnswers(client, cache);
    client.close();
  }
  final (status, parseError) = parseCached(cache.statusText);
  if (status != null) await maybeNotifyGaming(status, cache);
  await cache.save();
  await scheduleShutdownWarnings(status);
  await updateHomeWidget(status);
  return SyncOutcome(
    signedIn: client != null || locked,
    locked: locked,
    cache: cache,
    status: status,
    parseError: parseError,
  );
}

/// Uploads every queued request in [cache] to Firebase, marking each as sent.
/// A failed upload leaves the request queued; it is retried on the next sync.
/// Returns whether any was sent.
Future<bool> uploadQueued(
  RemoteStore client,
  LocalCache cache,
  String deviceId,
) async {
  var anySent = false;
  for (final request in [...cache.requests]) {
    if (!request.isQueued) continue;
    try {
      final sent = await uploadRequest(client, request, deviceId: deviceId);
      cache.replaceRequest(sent);
      anySent = true;
    } on Object {
      // Leave it queued; retry on the next sync.
    }
  }
  return anySent;
}

/// Reads answers for every sent, unanswered request in [cache], including
/// ones already timed out. Marks a sent pending one older than
/// [kAnswerTimeout] (from its upload time) as timed out. Queued requests are
/// skipped: they are not in Firebase yet. Returns whether anything changed.
Future<bool> collectAnswers(RemoteStore client, LocalCache cache) async {
  var changed = false;
  for (final request in [...cache.requests]) {
    if (request.isAnswered || request.isQueued) continue;
    RequestResult? result;
    try {
      result = await readResult(client, request.id);
    } on Object {
      result = null; // A failed read is retried on the next poll.
    }
    if (result != null) {
      final settled = request.settle(result: result);
      cache.replaceRequest(settled);
      if (settled.kind == RequestKind.restDay) {
        await notifyRestDayResult(settled);
      }
      changed = true;
    } else if (request.isPending &&
        DateTime.now().difference(request.sentAt!) > kAnswerTimeout) {
      cache.replaceRequest(request.settle(timedOut: true));
      changed = true;
    }
  }
  return changed;
}
