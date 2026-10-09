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
  });

  /// Whether this device holds a Firebase session.
  final bool signedIn;

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

/// Runs one pass. Never throws: a failed read is recorded in the cache.
Future<SyncOutcome> syncOnce({StoreOpener open = openClient}) async {
  final cache = await LocalCache.load();
  RemoteStore? client;
  try {
    client = await open();
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
    await collectAnswers(client, cache);
    client.close();
  }
  final (status, parseError) = parseCached(cache.statusText);
  if (status != null) await maybeNotifyGaming(status, cache);
  await cache.save();
  await scheduleShutdownWarnings(status);
  await updateHomeWidget(status);
  return SyncOutcome(
    signedIn: client != null,
    cache: cache,
    status: status,
    parseError: parseError,
  );
}

/// Reads answers for every unanswered request in [cache], including ones
/// already timed out, and marks a pending one older than [kAnswerTimeout] as
/// timed out. Returns whether anything changed.
Future<bool> collectAnswers(RemoteStore client, LocalCache cache) async {
  var changed = false;
  for (final request in [...cache.requests]) {
    if (request.isAnswered) continue;
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
        DateTime.now().difference(request.createdAt) > kAnswerTimeout) {
      cache.replaceRequest(request.settle(timedOut: true));
      changed = true;
    }
  }
  return changed;
}
