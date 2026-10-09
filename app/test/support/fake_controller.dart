/// A [LimitsController] with no IO and no timers: screens are driven with a
/// preset [SyncOutcome] and every call is recorded.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/services/limits_controller.dart';
import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_once.dart';

import 'fakes.dart';

/// Records what the screens ask of the controller.
class FakeController extends LimitsController {
  /// Creates a controller showing [outcome] (null means "still loading").
  new(this._outcome, {this._actionError});

  SyncOutcome? _outcome;
  String? _actionError;

  /// How many times [start] ran.
  int starts = 0;

  /// How many times [refresh] ran.
  int refreshes = 0;

  /// How many times [requestRefresh] ran.
  int refreshRequests = 0;

  /// Days passed to [declareRestDay].
  final List<DateTime> restDays = [];

  /// Whether [dispose] ran.
  bool disposed = false;

  @override
  SyncOutcome? get outcome => _outcome;

  @override
  bool get loading => false;

  @override
  String? get actionError => _actionError;

  /// Swaps the outcome and rebuilds listeners.
  void show(SyncOutcome? outcome, {String? actionError}) {
    _outcome = outcome;
    _actionError = actionError;
    notifyListeners();
  }

  @override
  SentRequest? latest(RequestKind kind) {
    final all = _outcome?.cache.requests ?? const <SentRequest>[];
    for (final r in all.reversed) {
      if (r.kind == kind) return r;
    }
    return null;
  }

  @override
  void start() => starts++;

  @override
  Future<void> refresh() async => refreshes++;

  @override
  Future<void> requestRefresh() async => refreshRequests++;

  @override
  Future<void> declareRestDay(DateTime day) async => restDays.add(day);

  @override
  void dispose() {
    disposed = true;
    super.dispose();
  }
}

/// A signed-in outcome with a status published at [published].
SyncOutcome outcomeWith({
  required DateTime published,
  bool signedIn = true,
  DailyStatus? status,
  String? parseError,
  String? lastError,
  DateTime? fetchedAt,
  List<SentRequest> requests = const [],
}) => SyncOutcome(
  signedIn: signedIn,
  status: status ?? DailyStatus.parse(statusJson(published: published)),
  parseError: parseError,
  cache: LocalCache(
    fetchedAt: fetchedAt,
    lastError: lastError,
    requests: [...requests],
  ),
);

/// An outcome with no status at all.
SyncOutcome emptyOutcome({
  bool signedIn = true,
  String? parseError,
  String? lastError,
  List<SentRequest> requests = const [],
}) => SyncOutcome(
  signedIn: signedIn,
  parseError: parseError,
  cache: LocalCache(lastError: lastError, requests: [...requests]),
);

/// Signed in, no parsed status, but a successful read at [fetchedAt].
SyncOutcome outcomeReadOnly(DateTime fetchedAt) =>
    SyncOutcome(signedIn: true, cache: LocalCache(fetchedAt: fetchedAt));
