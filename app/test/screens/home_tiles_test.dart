// The home screen's tiles, split from home_screen_test.dart (250-line cap).
import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/home_screen.dart';
import 'package:daily_limits/screens/status_cards.dart';
import 'package:daily_limits/screens/status_view.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';

import '../support/fake_controller.dart';
import '../support/fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<void> pump(WidgetTester tester, Widget home) async {
    tester.view.physicalSize = const Size(800, 3000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(theme: buildDarkTheme(), home: home));
  }

  testWidgets('tap and long-press open the same sheet per tile', (
    tester,
  ) async {
    final controller = FakeController(outcomeWith(published: DateTime.now()));
    await pump(tester, HomeScreen(controller: controller));
    for (final (key, card) in [
      ('tile-shutdown', ShutdownCard),
      ('tile-gaming', GamingCard),
      ('tile-earners', EarnersCard),
    ]) {
      await tester.tap(find.byKey(Key(key)));
      await tester.pumpAndSettle();
      expect(find.byType(card), findsOneWidget);
      await tester.tapAt(const Offset(10, 10));
      await tester.pumpAndSettle();
      await tester.longPress(find.byKey(Key(key)));
      await tester.pumpAndSettle();
      expect(find.byType(card), findsOneWidget);
      await tester.tapAt(const Offset(10, 10));
      await tester.pumpAndSettle();
    }
  });

  testWidgets('no gaming budget: the gaming tile is gone', (tester) async {
    final status = DailyStatus.parse(
      statusJson(published: DateTime.now(), gamingEnforced: false),
    );
    final controller = FakeController(
      outcomeWith(published: DateTime.now(), status: status),
    );
    await pump(tester, HomeScreen(controller: controller));
    expect(find.byKey(const Key('tile-gaming')), findsNothing);
    for (final key in ['tile-shutdown', 'tile-earners', 'tile-ask']) {
      expect(find.byKey(Key(key)), findsOneWidget);
    }
  });

  testWidgets('no status: tiles read ? and open nothing', (tester) async {
    final controller = FakeController(emptyOutcome());
    await pump(tester, HomeScreen(controller: controller));
    expect(find.text('?'), findsNWidgets(3));
    await tester.tap(find.byKey(const Key('tile-gaming')));
    await tester.pumpAndSettle();
    expect(find.byType(BottomSheet), findsNothing);
  });

  testWidgets('offline PC: banner and greyed tiles', (tester) async {
    final old = DateTime.now().subtract(const Duration(hours: 3));
    final controller = FakeController(outcomeWith(published: old));
    await pump(tester, HomeScreen(controller: controller));
    expect(find.byKey(const Key('status-offline')), findsOneWidget);
    expect(find.byType(GreyedOut), findsOneWidget);
  });

  testWidgets('ask tile shows a pending spinner and a timeout mark', (
    tester,
  ) async {
    final now = DateTime.now();
    SentRequest req(RequestKind k, {bool timedOut = false}) =>
        SentRequest(id: 'x', kind: k, createdAt: now, timedOut: timedOut);
    final controller = FakeController(
      outcomeWith(published: now, requests: [req(RequestKind.refresh)]),
    );
    await pump(tester, HomeScreen(controller: controller));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    controller.show(
      outcomeWith(
        published: now,
        requests: [req(RequestKind.restDay, timedOut: true)],
      ),
    );
    await tester.pump();
    expect(find.byIcon(Icons.schedule), findsOneWidget);
  });
}
