import 'dart:convert';

import 'package:daily_limits/model/status.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

void main() {
  final published = DateTime(2026, 10, 9, 12, 30);

  group('DailyStatus.parse', () {
    test('reads every field of the contract', () {
      final s = DailyStatus.parse(statusJson(published: published));
      expect(s.date, '2026-10-09');
      expect(s.publishedAt, published);
      expect(s.deviceId, 'pc');
      expect(s.applied, '22:00');
      expect(s.resolved, '20:00');
      expect(s.floor, '18:00');
      expect(s.ceiling, '23:00');
      expect(s.gamingDay, '2026-10-09');
      expect(s.budgetMinutes, 300);
      expect(s.usedMinutes, 120);
      expect(s.ceilingMinutes, 480);
      expect(s.leftMinutes, 180);
      expect(s.earners.map((e) => e.name), ['workout', 'reading']);
      expect(s.earners.first.shutdownMinutes, 120);
      expect(s.earners.first.gamingMinutes, 120);
      expect(s.earners.last.status, 'done');
      expect(s.todo.single.shutdownAfter, '22:00');
      expect(s.todo.single.label, 'workout');
      expect(s.todo.single.status, 'todo');
    });

    test('fills optional values with their defaults', () {
      final s = DailyStatus.parse(
        jsonEncode({
          'date': '2026-10-09',
          'published_at': 1,
          'shutdown': <String, Object?>{},
          'gaming': {
            'day': '2026-10-09',
            'budget_minutes': 60,
            'ceiling_minutes': 480,
          },
          'earners': [
            {'name': 'anki', 'status': 'unknown'},
          ],
          'todo': [
            {'name': 'anki', 'shutdown_after': '21:00'},
          ],
        }),
      );
      expect(s.deviceId, '');
      expect(s.applied, isNull);
      expect(s.usedMinutes, isNull);
      expect(s.leftMinutes, isNull);
      expect(s.earners.single.label, 'anki');
      expect(s.earners.single.shutdownMinutes, 0);
      expect(s.earners.single.gamingMinutes, 0);
      expect(s.todo.single.label, 'anki');
      expect(s.todo.single.status, 'todo');
    });

    test('treats absent lists as empty', () {
      final map =
          jsonDecode(statusJson(published: published)) as Map<String, dynamic>
            ..remove('earners')
            ..remove('todo');
      final s = DailyStatus.parse(jsonEncode(map));
      expect(s.earners, isEmpty);
      expect(s.todo, isEmpty);
    });

    for (final (what, mutate)
        in <(String, void Function(Map<String, dynamic>))>[
          ('root not an object', (m) {}),
          ('shutdown not an object', (m) => m['shutdown'] = 'x'),
          ('date not a string', (m) => m['date'] = 3),
          ('published_at not a number', (m) => m['published_at'] = 'x'),
          ('earners not a list', (m) => m['earners'] = 'x'),
          ('earner not an object', (m) => m['earners'] = [1]),
        ]) {
      test('rejects $what', () {
        final map = jsonDecode(
          statusJson(published: published),
        ) as Map<String, dynamic>;
        mutate(map);
        final text = what.startsWith('root') ? '[1]' : jsonEncode(map);
        expect(() => DailyStatus.parse(text), throwsFormatException);
      });
    }
  });

  test('isOffline after 15 minutes without a publish', () {
    final s = DailyStatus.parse(statusJson(published: published));
    expect(s.isOffline(published.add(kOfflineAfter)), isFalse);
    expect(
      s.isOffline(published.add(kOfflineAfter + const Duration(seconds: 1))),
      isTrue,
    );
  });

  test('isoDay and hhmm pad to fixed width', () {
    final d = DateTime(2026, 1, 2, 3, 4);
    expect(isoDay(d), '2026-01-02');
    expect(hhmm(d), '03:04');
  });

  test('compactMinutes matches the PC bar', () {
    expect(compactMinutes(-5), '0m');
    expect(compactMinutes(45), '45m');
    expect(compactMinutes(60), '1h00');
    expect(compactMinutes(89), '1h29');
  });

  test('todayAt parses HH:MM and rejects anything else', () {
    final now = DateTime(2026, 10, 9, 13);
    expect(todayAt('21:30', now), DateTime(2026, 10, 9, 21, 30));
    expect(todayAt('7:05', now), DateTime(2026, 10, 9, 7, 5));
    expect(todayAt(null, now), isNull);
    expect(todayAt('21h30', now), isNull);
  });
}
