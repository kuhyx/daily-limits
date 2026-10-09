import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/status_view.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

void main() {
  final now = DateTime(2026, 10, 9, 14, 30);
  const noEarners = <Map<String, Object?>>[];

  Future<void> pump(WidgetTester tester, String json, {DateTime? at}) async {
    tester.view.physicalSize = const Size(800, 3000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: buildDarkTheme(),
        home: Scaffold(
          body: SingleChildScrollView(
            child: StatusView(status: DailyStatus.parse(json), now: at ?? now),
          ),
        ),
      ),
    );
  }

  testWidgets('online: all sections, no offline banner or greyscale', (
    tester,
  ) async {
    await pump(tester, statusJson(published: now));
    expect(find.text('Shutdown'), findsOneWidget);
    expect(find.textContaining('22:00'), findsWidgets);
    expect(find.text('Registry resolves to 20:00'), findsOneWidget);
    expect(find.text('Floor 18:00 → ceiling 23:00'), findsOneWidget);
    expect(find.text('Gaming'), findsOneWidget);
    expect(find.textContaining('PC offline'), findsNothing);
    expect(find.byType(ColorFiltered), findsNothing);
    expect(find.text('To extend'), findsOneWidget);
    expect(find.text('Earners'), findsOneWidget);
  });

  testWidgets('offline: banner with the publish time and greyscale', (
    tester,
  ) async {
    final published = now.subtract(const Duration(hours: 2));
    await pump(tester, statusJson(published: published));
    expect(
      find.text(
        'PC offline since ${hhmm(published)} — '
        'showing the last values it published.',
      ),
      findsOneWidget,
    );
    expect(find.byType(ColorFiltered), findsOneWidget);
    expect(find.byType(Opacity), findsWidgets);
  });

  testWidgets('resolved equal to applied hides the registry line', (
    tester,
  ) async {
    await pump(tester, statusJson(published: now, resolved: '22:00'));
    expect(find.textContaining('Registry resolves'), findsNothing);
  });

  testWidgets('null resolved also hides the registry line', (tester) async {
    await pump(tester, statusJson(published: now, resolved: null));
    expect(find.textContaining('Registry resolves'), findsNothing);
  });

  testWidgets('nothing applied and no floor or ceiling', (tester) async {
    await pump(
      tester,
      statusJson(
        published: now,
        applied: null,
        resolved: null,
        floor: null,
        ceiling: null,
      ),
    );
    expect(find.textContaining('none applied'), findsOneWidget);
    expect(find.text('Floor ? → ceiling ?'), findsOneWidget);
  });

  testWidgets('another gaming day is named in the title', (tester) async {
    await pump(tester, statusJson(published: now, gamingDay: '2026-10-08'));
    expect(find.text('Gaming (day 2026-10-08)'), findsOneWidget);
  });

  testWidgets('used minutes known: left and used shown', (tester) async {
    await pump(tester, statusJson(published: now));
    expect(find.textContaining('left'), findsWidgets);
    expect(find.textContaining('Used '), findsOneWidget);
    expect(find.textContaining('could not check'), findsNothing);
  });

  testWidgets('used minutes unknown: "? left" and "could not check"', (
    tester,
  ) async {
    await pump(tester, statusJson(published: now, used: null));
    expect(find.text('🎮 ? left'), findsOneWidget);
    expect(find.textContaining('Used: could not check'), findsOneWidget);
  });

  testWidgets('empty todo hides "To extend"', (tester) async {
    await pump(tester, statusJson(published: now, todo: noEarners));
    expect(find.text('To extend'), findsNothing);
  });

  testWidgets('unknown todo item is marked (?)', (tester) async {
    await pump(
      tester,
      statusJson(
        published: now,
        todo: [
          {
            'name': 'workout',
            'label': 'Workout',
            'status': 'unknown',
            'shutdown_after': '21:00',
          },
          {
            'name': 'reading',
            'label': 'Reading',
            'status': 'todo',
            'shutdown_after': '22:00',
          },
        ],
      ),
    );
    final text = tester
        .widgetList<Text>(find.textContaining('→ '))
        .map((t) => t.data!)
        .join('|');
    expect(text, contains('Workout → 21:00 (?)'));
    expect(text, contains('Reading → 22:00'));
    expect(text, isNot(contains('22:00 (?)')));
  });

  testWidgets('no earners shows None', (tester) async {
    await pump(tester, statusJson(published: now, earners: noEarners));
    expect(find.text('None'), findsOneWidget);
  });

  testWidgets('earner statuses: done, to do, could not check', (tester) async {
    Map<String, Object?> earner(String name, String status) => {
      'name': name,
      'label': name,
      'status': status,
    };
    await pump(
      tester,
      statusJson(
        published: now,
        todo: noEarners,
        earners: [
          earner('workout', 'done'),
          earner('reading', 'todo'),
          earner('anki', 'unknown'),
        ],
      ),
    );
    expect(find.text('done'), findsOneWidget);
    expect(find.text('to do'), findsOneWidget);
    expect(find.text('could not check'), findsOneWidget);
    expect(find.text('None'), findsNothing);
  });
}
