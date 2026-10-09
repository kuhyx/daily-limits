/// UI state for the main screen: the latest sync outcome plus the two
/// actions (refresh request, rest-day request) and polling for their answers.
library;

import 'dart:async';

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:daily_limits/services/sync_once.dart';
import 'package:flutter/foundation.dart';

/// Holds the latest [SyncOutcome] and drives the actions.
class LimitsController extends ChangeNotifier {
  /// Creates a controller. The defaults are the real ones; tests pass an
  /// in-memory store, a fixed device id and short intervals.
  new({
    this._open = openClient,
    this._device = deviceId,
    this._pollEvery = const Duration(seconds: 5),
    this._statusEvery = const Duration(minutes: 1),
  });

  final StoreOpener _open;
  final Future<String> Function() _device;

  /// How often a pending request is checked while the app is open.
  final Duration _pollEvery;

  /// How often the status is re-read while the app is open.
  final Duration _statusEvery;

  SyncOutcome? _outcome;
  bool _loading = false;
  Future<void>? _inFlight;
  bool _again = false;
  String? _actionError;
  Timer? _poll;
  Timer? _statusTimer;

  /// Set by [dispose]. A pass can still be running then (the screen closed
  /// mid-refresh); it must neither notify nor arm a new poll timer.
  bool _disposed = false;

  /// The latest outcome, or null before the first pass finishes.
  SyncOutcome? get outcome => _outcome;

  /// Whether a sync pass is running.
  bool get loading => _loading;

  /// Why the last action could not be sent.
  String? get actionError => _actionError;

  /// The parsed status, if any.
  DailyStatus? get status => _outcome?.status;

  /// The newest request of [kind] this phone sent, if any.
  SentRequest? latest(RequestKind kind) {
    final all = _outcome?.cache.requests ?? const <SentRequest>[];
    for (final r in all.reversed) {
      if (r.kind == kind) return r;
    }
    return null;
  }

  /// Starts the first pass and the once-a-minute status re-read.
  void start() {
    unawaited(refresh());
    _statusTimer = Timer.periodic(_statusEvery, (_) => unawaited(refresh()));
  }

  /// Re-reads everything from Firebase (no request written).
  ///
  /// A call while a pass is running does not start a second one, but it is
  /// not dropped either: the running pass goes round once more, so a request
  /// sent mid-pass still shows as "waiting" as soon as it can.
  Future<void> refresh() async {
    final running = _inFlight;
    if (running != null) {
      _again = true;
      await running;
      return;
    }
    final pass = _run();
    _inFlight = pass;
    try {
      await pass;
    } finally {
      _inFlight = null;
    }
  }

  Future<void> _run() async {
    _loading = true;
    _notify();
    try {
      do {
        _again = false;
        _outcome = await syncOnce(open: _open);
      } while (_again);
    } finally {
      _loading = false;
      _notify();
    }
    _schedulePoll();
  }

  /// Asks the PC to republish now.
  Future<void> requestRefresh() => _send(RequestKind.refresh);

  /// Asks the PC to make [day] a rest day.
  Future<void> declareRestDay(DateTime day) =>
      _send(RequestKind.restDay, date: isoDay(day));

  Future<void> _send(RequestKind kind, {String? date}) async {
    _actionError = null;
    final client = await _open();
    if (client == null) {
      _actionError = 'Sign in first (Settings).';
      _notify();
      return;
    }
    try {
      final sent = await sendRequest(
        client,
        kind: kind,
        deviceId: await _device(),
        date: date,
      );
      final cache = await LocalCache.load();
      cache.requests.add(sent);
      await cache.save();
    } on Object catch (error) {
      _actionError = 'Could not send the request: $error';
    } finally {
      client.close();
    }
    await refresh();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void _schedulePoll() {
    if (_disposed) return;
    final pending = _outcome?.cache.requests.any((r) => r.isPending) ?? false;
    _poll?.cancel();
    if (!pending) return;
    _poll = Timer(_pollEvery, _pollOnce);
  }

  Future<void> _pollOnce() async {
    final client = await _open();
    if (client == null) return;
    final cache = await LocalCache.load();
    final changed = await collectAnswers(client, cache);
    client.close();
    if (!changed) {
      _schedulePoll();
      return;
    }
    await cache.save();
    // An answered refresh means the PC has republished: read it.
    await refresh();
  }

  @override
  void dispose() {
    _disposed = true;
    _poll?.cancel();
    _statusTimer?.cancel();
    super.dispose();
  }
}
