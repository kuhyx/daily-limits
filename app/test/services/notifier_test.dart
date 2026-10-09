import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/notifier.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late PluginLog log;
  late PlatformKnobs knobs;

  setUp(() {
    knobs = PlatformKnobs();
    log = installPlatformFakes(tempDir(), knobs: knobs);
  });

  DailyStatus status({
    DateTime? published,
    String? applied,
    String? date,
    int? used,
  }) {
    final now = published ?? DateTime.now();
    return DailyStatus.parse(
      statusJson(published: now, applied: applied, date: date, used: used),
    );
  }

  test('initNotifications initialises the plugin only once', () async {
    await initNotifications();
    await initNotifications();
    // The plugin may already be initialised by an earlier test in this file.
    expect(log.named('initialize').length, lessThanOrEqualTo(1));
  });

  test('requestNotificationPermission reports the platform answer', () async {
    expect(await requestNotificationPermission(), isTrue);
    knobs.permission = null;
    expect(await requestNotificationPermission(), isFalse);
  });

  group('scheduleShutdownWarnings', () {
    Object? scheduleMode(PluginLog log) {
      final args = log.named('zonedSchedule').first.arguments as Map;
      return (args['platformSpecifics'] as Map)['scheduleMode'];
    }

    String inMinutes(int m) => hhmm(DateTime.now().add(Duration(minutes: m)));

    test('schedules both warnings, exact when allowed', () async {
      await scheduleShutdownWarnings(status(applied: inMinutes(60)));
      expect(log.named('cancel'), hasLength(2));
      expect(log.titles('zonedSchedule'), [
        'PC shuts down in 30 min',
        'PC shuts down in 10 min',
      ]);
      final mode = scheduleMode(log);
      expect(mode, 'exactAllowWhileIdle');
    });

    test('falls back to inexact alarms without the permission', () async {
      knobs.exactAlarms = false;
      await scheduleShutdownWarnings(status(applied: inMinutes(60)));
      final mode = scheduleMode(log);
      expect(mode, 'inexactAllowWhileIdle');
    });

    test('skips a warning whose time has passed', () async {
      await scheduleShutdownWarnings(status(applied: inMinutes(20)));
      expect(log.titles('zonedSchedule'), ['PC shuts down in 10 min']);
    });

    test(
      'only cancels for no status, another day or no applied time',
      () async {
        await scheduleShutdownWarnings(null);
        await scheduleShutdownWarnings(status(date: '2000-01-01'));
        await scheduleShutdownWarnings(status(applied: 'none'));
        expect(log.named('zonedSchedule'), isEmpty);
        expect(log.named('cancel'), hasLength(6));
      },
    );
  });

  group('maybeNotifyGaming', () {
    test('fires once per gaming day at 10 minutes left', () async {
      final cache = LocalCache();
      final s = status(used: 290);
      await maybeNotifyGaming(s, cache);
      await maybeNotifyGaming(s, cache);
      expect(log.titles('show'), ['Gaming: 10m left']);
      expect(cache.gamingNotifiedDay, s.gamingDay);
    });

    test('says "used up" at zero', () async {
      await maybeNotifyGaming(status(used: 300), LocalCache());
      expect(log.titles('show'), ['Gaming time used up']);
    });

    test('stays quiet with time left, unknown use or a stale status', () async {
      final cache = LocalCache();
      await maybeNotifyGaming(status(used: 100), cache);
      await maybeNotifyGaming(status(), cache); // use unknown
      await maybeNotifyGaming(
        status(
          used: 299,
          published: DateTime.now().subtract(const Duration(hours: 1)),
        ),
        cache,
      );
      expect(log.named('show'), isEmpty);
      expect(cache.gamingNotifiedDay, isNull);
    });
  });

  group('notifyRestDayResult', () {
    SentRequest restDay(RequestResult? result) => SentRequest(
      id: 'r',
      kind: RequestKind.restDay,
      date: '2026-10-10',
      createdAt: DateTime.now(),
      result: result,
    );

    test('titles the verdict', () async {
      await notifyRestDayResult(
        restDay(const RequestResult(ok: true, message: 'declared')),
      );
      await notifyRestDayResult(
        restDay(const RequestResult(ok: false, message: 'refused: past')),
      );
      expect(log.titles('show'), [
        'Rest day declared: 2026-10-10',
        'Rest day refused: 2026-10-10',
      ]);
    });

    test('does nothing without an answer', () async {
      await notifyRestDayResult(restDay(null));
      expect(log.named('show'), isEmpty);
    });
  });

  test('showTestNotification posts the test notification', () async {
    await showTestNotification();
    expect(log.titles('show'), ['Daily limits: test notification']);
  });
}
