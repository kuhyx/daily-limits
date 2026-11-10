import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/status_view.dart';
import 'package:daily_limits/ui/earner_icons.dart';
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
    expect(find.byIcon(Icons.power_settings_new), findsOneWidget);
    expect(find.text('$kShutdownIcon 22:00'), findsOneWidget);
    // Registry answer differs from applied: calculator glyph + its time.
    expect(find.byIcon(Icons.calculate), findsOneWidget);
    expect(find.bySemanticsLabel('Registry resolves to 20:00'), findsOneWidget);
    expect(find.text('18:00 → 23:00'), findsOneWidget);
    expect(find.byIcon(Icons.sports_esports), findsOneWidget);
    expect(find.byIcon(Icons.more_time), findsOneWidget);
    expect(find.byIcon(Icons.emoji_events), findsOneWidget);
    expect(find.byKey(const Key('status-offline')), findsNothing);
    expect(find.byType(ColorFiltered), findsNothing);
  });

  testWidgets('offline: banner with the publish time and greyscale', (
    tester,
  ) async {
    final published = now.subtract(const Duration(hours: 2));
    await pump(tester, statusJson(published: published));
    final banner = find.byKey(const Key('status-offline'));
    expect(banner, findsOneWidget);
    expect(
      find.descendant(
        of: banner,
        matching: find.byIcon(Icons.desktop_access_disabled),
      ),
      findsOneWidget,
    );
    expect(
      find.descendant(of: banner, matching: find.text(hhmm(published))),
      findsOneWidget,
    );
    expect(find.byType(ColorFiltered), findsOneWidget);
    expect(find.byType(Opacity), findsWidgets);
  });

  testWidgets('resolved equal to applied hides the registry line', (
    tester,
  ) async {
    await pump(tester, statusJson(published: now, resolved: '22:00'));
    expect(find.byIcon(Icons.calculate), findsNothing);
  });

  testWidgets('null resolved also hides the registry line', (tester) async {
    await pump(tester, statusJson(published: now, resolved: null));
    expect(find.byIcon(Icons.calculate), findsNothing);
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
    expect(find.text('$kShutdownIcon --:--'), findsOneWidget);
    expect(
      find.bySemanticsLabel(RegExp('No shutdown applied')),
      findsOneWidget,
    );
    expect(find.text('? → ?'), findsOneWidget);
  });

  testWidgets('another gaming day is shown with its date', (tester) async {
    await pump(tester, statusJson(published: now, gamingDay: '2026-10-08'));
    expect(find.byIcon(Icons.event), findsOneWidget);
    expect(find.text('2026-10-08'), findsOneWidget);
  });

  testWidgets('today as gaming day: no date row', (tester) async {
    await pump(tester, statusJson(published: now));
    expect(find.byIcon(Icons.event), findsNothing);
  });

  testWidgets('used minutes known: left and used of budget', (tester) async {
    await pump(tester, statusJson(published: now));
    expect(find.text('🎮 3h00'), findsOneWidget);
    expect(find.text('2h00 / 5h00'), findsOneWidget);
    expect(find.text('8h00'), findsOneWidget);
    expect(find.bySemanticsLabel('Used 2h00 of 5h00'), findsOneWidget);
  });

  testWidgets('used minutes unknown: question marks', (tester) async {
    await pump(tester, statusJson(published: now, used: null));
    expect(find.text('🎮 ?'), findsOneWidget);
    expect(find.text('? / 5h00'), findsOneWidget);
    expect(
      find.bySemanticsLabel('Used could not check, budget 5h00'),
      findsOneWidget,
    );
  });

  testWidgets('empty todo hides the extend line', (tester) async {
    await pump(tester, statusJson(published: now, todo: noEarners));
    expect(find.byIcon(Icons.more_time), findsNothing);
  });

  testWidgets('unknown todo item is marked ?', (tester) async {
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
    expect(find.text('💪 → 21:00 ?   📖 → 22:00'), findsOneWidget);
  });

  testWidgets('no earners shows a dash', (tester) async {
    await pump(tester, statusJson(published: now, earners: noEarners));
    expect(find.byIcon(Icons.remove), findsOneWidget);
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
    Icon mark(String key) => tester.widget<Icon>(find.byKey(Key(key)));
    expect(mark('earner-workout-done').icon, Icons.check_circle);
    expect(mark('earner-reading-todo').icon, Icons.radio_button_unchecked);
    expect(mark('earner-anki-unknown').icon, Icons.help_outline);
    expect(mark('earner-anki-unknown').semanticLabel, 'anki could not check');
    expect(find.byIcon(Icons.remove), findsNothing);
  });
}
