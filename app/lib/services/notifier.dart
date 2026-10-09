/// Local notifications only (no FCM): shutdown warnings scheduled on the
/// phone, the gaming "10 min left" once per gaming day, and rest-day answers.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

const int _shutdown30Id = 10;
const int _shutdown10Id = 11;
const int _gamingId = 20;
const int _restDayId = 30;
const int _testId = 99;

const _limits = AndroidNotificationDetails(
  'limits',
  'Shutdown and gaming',
  channelDescription: 'Shutdown approaching and gaming time running out',
  importance: Importance.high,
  priority: Priority.high,
);

const _answers = AndroidNotificationDetails(
  'answers',
  'PC answers',
  channelDescription: 'Whether the PC accepted a rest day',
);

final FlutterLocalNotificationsPlugin _plugin =
    FlutterLocalNotificationsPlugin();
bool _ready = false;

/// Initialises the plugin in the current isolate (UI or background).
Future<void> initNotifications() async {
  if (_ready) return;
  // Scheduling uses absolute instants in UTC, so only the UTC zone is needed
  // and no device-zone lookup is required.
  tz_data.initializeTimeZones();
  await _plugin.initialize(
    settings: const InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    ),
  );
  _ready = true;
}

AndroidFlutterLocalNotificationsPlugin? get _android => _plugin
    .resolvePlatformSpecificImplementation<
      AndroidFlutterLocalNotificationsPlugin
    >();

/// Asks for POST_NOTIFICATIONS (Android 13+). Returns whether it is granted.
Future<bool> requestNotificationPermission() async =>
    await _android?.requestNotificationsPermission() ?? false;

/// (Re)schedules the 30- and 10-minute shutdown warnings from [status].
///
/// Idempotent: both are cancelled first, so a changed applied time simply
/// replaces them. Nothing is scheduled when the status is not for today or
/// has no applied time, or when the warning time has already passed.
Future<void> scheduleShutdownWarnings(DailyStatus? status) async {
  await initNotifications();
  await _plugin.cancel(id: _shutdown30Id);
  await _plugin.cancel(id: _shutdown10Id);
  final now = DateTime.now();
  if (status == null || status.date != isoDay(now)) return;
  final shutdown = todayAt(status.applied, now);
  if (shutdown == null) return;
  final exact = await _android?.canScheduleExactNotifications() ?? false;
  final mode = exact
      ? AndroidScheduleMode.exactAllowWhileIdle
      : AndroidScheduleMode.inexactAllowWhileIdle;
  for (final (id, minutes) in [(_shutdown30Id, 30), (_shutdown10Id, 10)]) {
    final at = shutdown.subtract(Duration(minutes: minutes));
    if (!at.isAfter(now)) continue;
    await _plugin.zonedSchedule(
      id: id,
      scheduledDate: tz.TZDateTime.from(at.toUtc(), tz.UTC),
      notificationDetails: const NotificationDetails(android: _limits),
      androidScheduleMode: mode,
      title: 'PC shuts down in $minutes min',
      body: 'Shutdown at ${status.applied}.',
    );
  }
}

/// Fires the gaming warning once per gaming day when ≤ 10 min are left.
///
/// Only for a fresh status: a stale one would warn about minutes that may
/// already be gone. Records the day in [cache]; the caller saves it.
Future<void> maybeNotifyGaming(DailyStatus status, LocalCache cache) async {
  final left = status.leftMinutes;
  if (left == null || left > 10) return;
  if (status.isOffline(DateTime.now())) return;
  if (cache.gamingNotifiedDay == status.gamingDay) return;
  await initNotifications();
  await _plugin.show(
    id: _gamingId,
    title: left > 0
        ? 'Gaming: ${compactMinutes(left)} left'
        : 'Gaming time used up',
    body:
        'Budget ${compactMinutes(status.budgetMinutes)} for '
        '${status.gamingDay}.',
    notificationDetails: const NotificationDetails(android: _limits),
  );
  cache.gamingNotifiedDay = status.gamingDay;
}

/// Tells the user whether the PC declared or refused a rest day.
Future<void> notifyRestDayResult(SentRequest request) async {
  final result = request.result;
  if (result == null) return;
  await initNotifications();
  await _plugin.show(
    id: _restDayId,
    title: result.ok
        ? 'Rest day declared: ${request.date}'
        : 'Rest day refused: ${request.date}',
    body: result.message,
    notificationDetails: const NotificationDetails(android: _answers),
  );
}

/// A visible test notification, from Settings.
Future<void> showTestNotification() async {
  await initNotifications();
  await _plugin.show(
    id: _testId,
    title: 'Daily limits: test notification',
    body: 'Notifications from this app reach you.',
    notificationDetails: const NotificationDetails(android: _limits),
  );
}
