// Home must fit one Pixel 6a screen (1080x2400, dpr 2.625, status bar 132 px,
// nav bar 63 px) without any vertical scrolling, and the primary actions must
// stay reachable: the Ask tile, then both buttons inside its sheet.

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/home_screen.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';

import '../support/fake_controller.dart';
import '../support/fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<void> pump(
    WidgetTester tester,
    FakeController controller, {
    double textScale = 1,
  }) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.625;
    const insets = FakeViewPadding(top: 132, bottom: 63);
    tester.view.padding = insets;
    tester.view.viewPadding = insets;
    addTearDown(tester.view.reset);
    tester.platformDispatcher.textScaleFactorTestValue = textScale;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await tester.pumpWidget(
      MaterialApp(
        theme: buildDarkTheme(),
        home: HomeScreen(controller: controller),
      ),
    );
    await tester.pump();
  }

  DailyStatus fourEarners(DateTime now, {DateTime? published}) =>
      DailyStatus.parse(
        statusJson(
          published: published ?? now,
          earners: [
            for (final n in ['workout', 'reading', 'anki', 'steps'])
              {
                'name': n,
                'label': n,
                'status': n == 'reading' ? 'done' : 'todo',
                'shutdown_minutes': 60,
                'gaming_minutes': 60,
              },
          ],
          todo: [
            for (final n in ['workout', 'anki', 'steps'])
              {
                'name': n,
                'label': n,
                'status': 'todo',
                'shutdown_after': '22:00',
              },
          ],
        ),
      );

  void expectNoVerticalScroll(WidgetTester tester) {
    for (final s in tester.stateList<ScrollableState>(
      find.byType(Scrollable),
    )) {
      if (s.widget.axis != Axis.vertical) continue;
      expect(
        s.position.maxScrollExtent,
        0,
        reason: 'a vertical Scrollable scrolls: ${s.widget}',
      );
    }
  }

  Future<void> expectReachable(WidgetTester tester) async {
    expectNoVerticalScroll(tester);
    await tester.tap(find.byKey(const Key('tile-ask')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('action-refresh')));
    await tester.tap(find.byKey(const Key('action-rest')));
    await tester.pumpAndSettle();
  }

  testWidgets('signed in, 4 earners, todo list: fits, actions reachable', (
    tester,
  ) async {
    final now = DateTime.now();
    final controller = FakeController(
      outcomeWith(published: now, status: fourEarners(now), fetchedAt: now),
    );
    await pump(tester, controller);
    await expectReachable(tester);
    expect(controller.refreshRequests, 1);
  });

  testWidgets('error line and offline banner still fit', (tester) async {
    final now = DateTime.now();
    final old = now.subtract(const Duration(hours: 3));
    final controller = FakeController(
      outcomeWith(
        published: old,
        status: fourEarners(now, published: old),
        fetchedAt: now,
        lastError: 'Could not reach Firebase: ${'offline ' * 40}',
      ),
    );
    await pump(tester, controller);
    expect(find.byKey(const Key('home-error')), findsOneWidget);
    await expectReachable(tester);
  });

  testWidgets('largest font: pages sideways, still no vertical scroll', (
    tester,
  ) async {
    final now = DateTime.now();
    final controller = FakeController(
      outcomeWith(published: now, status: fourEarners(now), fetchedAt: now),
    );
    await pump(tester, controller, textScale: 2);
    expectNoVerticalScroll(tester);
  });
}
