/// The 15-minute background refresh (workmanager): one [syncOnce] pass, so
/// the widget, the shutdown warnings and the offline greying stay current
/// while the app is closed.
library;

import 'package:daily_limits/services/sync_once.dart';
import 'package:flutter/widgets.dart';
import 'package:workmanager/workmanager.dart';

const String _uniqueName = 'daily_limits.refresh';
const String _taskName = 'refresh';

// Two one-line delegations to the real workmanager, which `flutter test`
// cannot run (its platform side is the Android job scheduler). What they
// delegate to -- [backgroundTask] and [registerRefreshWith] -- is tested.
// coverage:ignore-start

/// Workmanager's entry point; runs in its own isolate.
@pragma('vm:entry-point')
void callbackDispatcher() => Workmanager().executeTask(backgroundTask);

/// Registers the periodic task with the real workmanager.
Future<void> registerBackgroundRefresh() => registerRefreshWith(Workmanager());

// coverage:ignore-end

/// One background run: a [syncOnce] pass. Reports success even when the pass
/// recorded an error, so workmanager does not back off and retry early.
Future<bool> backgroundTask(
  String task,
  Map<String, dynamic>? inputData, {
  Future<SyncOutcome> Function() sync = syncOnce,
}) async {
  WidgetsFlutterBinding.ensureInitialized();
  await sync();
  return true;
}

/// Registers the periodic task with [wm]. `keep` leaves an existing schedule
/// alone, so every app launch can call this safely.
Future<void> registerRefreshWith(Workmanager wm) async {
  await wm.initialize(callbackDispatcher);
  await wm.registerPeriodicTask(
    _uniqueName,
    _taskName,
    frequency: const Duration(minutes: 15),
    existingWorkPolicy: ExistingPeriodicWorkPolicy.keep,
  );
}
