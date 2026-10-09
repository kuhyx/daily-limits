import 'package:crdt_sync_flutter/testing/fake_secure_storage.dart';
import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/actions_card.dart';
import 'package:daily_limits/screens/home_screen.dart';
import 'package:daily_limits/screens/settings_screen.dart';
import 'package:daily_limits/screens/status_view.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

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

  testWidgets('starts the controller and shows a spinner while loading', (
    tester,
  ) async {
    final controller = FakeController(null);
    await pump(tester, HomeScreen(controller: controller));
    expect(controller.starts, 1);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.byType(ActionsCard), findsNothing);
  });

  testWidgets('not signed in: empty state and disabled actions', (
    tester,
  ) async {
    final controller = FakeController(emptyOutcome(signedIn: false));
    await pump(tester, HomeScreen(controller: controller));
    expect(find.text('Not signed in'), findsOneWidget);
    expect(find.byType(StatusView), findsNothing);
    final refresh = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(refresh.onPressed, isNull);
  });

  testWidgets('signed in with no status: nothing published yet', (
    tester,
  ) async {
    final controller = FakeController(emptyOutcome());
    await pump(tester, HomeScreen(controller: controller));
    expect(find.text('Nothing published yet'), findsOneWidget);
    expect(find.text('Not signed in'), findsNothing);
    // Empty footer: nothing about publish or read times.
    expect(find.textContaining('read '), findsNothing);
  });

  testWidgets('unreadable status shows the error, not "nothing yet"', (
    tester,
  ) async {
    final controller = FakeController(
      emptyOutcome(parseError: 'Unreadable status from the PC: boom'),
    );
    await pump(tester, HomeScreen(controller: controller));
    expect(find.text('Unreadable status from the PC: boom'), findsOneWidget);
    expect(find.text('Nothing published yet'), findsNothing);
  });

  testWidgets('shows the last cache error', (tester) async {
    final controller = FakeController(
      emptyOutcome(lastError: 'Could not reach Firebase: offline'),
    );
    await pump(tester, HomeScreen(controller: controller));
    expect(find.text('Could not reach Firebase: offline'), findsOneWidget);
  });

  testWidgets('status present: view, actions and footer with both times', (
    tester,
  ) async {
    final published = DateTime.now();
    final fetched = published.add(const Duration(minutes: 1));
    final controller = FakeController(
      outcomeWith(published: published, fetchedAt: fetched),
    );
    await pump(tester, HomeScreen(controller: controller));
    expect(find.byType(StatusView), findsOneWidget);
    expect(find.byType(ActionsCard), findsOneWidget);
    expect(find.text('Nothing published yet'), findsNothing);
    expect(
      find.text('Published ${hhmm(published)} · read ${hhmm(fetched)}'),
      findsOneWidget,
    );
  });

  testWidgets('footer with only a read time', (tester) async {
    final fetched = DateTime.now();
    final controller = FakeController(outcomeReadOnly(fetched));
    await pump(tester, HomeScreen(controller: controller));
    expect(find.text('read ${hhmm(fetched)}'), findsOneWidget);
  });

  testWidgets('pull to refresh calls refresh', (tester) async {
    final controller = FakeController(outcomeWith(published: DateTime.now()));
    // Default 800x600 surface: the content must overflow to be draggable.
    await tester.pumpWidget(
      MaterialApp(
        theme: buildDarkTheme(),
        home: HomeScreen(controller: controller),
      ),
    );
    final before = controller.refreshes;
    await tester.fling(find.byType(ListView), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();
    expect(controller.refreshes, before + 1);
  });

  testWidgets('app resume refreshes, other lifecycle states do not', (
    tester,
  ) async {
    final controller = FakeController(emptyOutcome());
    await pump(tester, HomeScreen(controller: controller));
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    expect(controller.refreshes, 0);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    expect(controller.refreshes, 1);
  });

  testWidgets('Settings opens and refreshes again after popping', (
    tester,
  ) async {
    installFakeSecureStorage();
    installPlatformFakes(tempDir());
    final controller = FakeController(emptyOutcome());
    await pump(tester, HomeScreen(controller: controller));
    await tester.tap(find.byTooltip('Settings'));
    await tester.pumpAndSettle();
    expect(find.byType(SettingsScreen), findsOneWidget);
    expect(controller.refreshes, 0);
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.byType(SettingsScreen), findsNothing);
    expect(controller.refreshes, 1);
  });

  testWidgets('rebuilds when the controller publishes a new outcome', (
    tester,
  ) async {
    final controller = FakeController(null);
    await pump(tester, HomeScreen(controller: controller));
    controller.show(emptyOutcome(signedIn: false));
    await tester.pump();
    expect(find.text('Not signed in'), findsOneWidget);
  });

  testWidgets('disposing the screen disposes its controller', (tester) async {
    final controller = FakeController(null);
    await pump(tester, HomeScreen(controller: controller));
    await tester.pumpWidget(const SizedBox());
    expect(controller.disposed, isTrue);
  });

  testWidgets('without a controller it makes its own and reads Firebase', (
    tester,
  ) async {
    installFakeSecureStorage();
    installPlatformFakes(tempDir());
    // Mount inside runAsync so the controller's first pass (real file IO)
    // starts in the real zone.
    await tester.runAsync(() async {
      await pump(tester, const HomeScreen());
      await Future<void>.delayed(const Duration(milliseconds: 500));
    });
    await tester.pump();
    expect(find.text('Not signed in'), findsOneWidget);
    // Unmount: cancels the controller's once-a-minute timer.
    await tester.pumpWidget(const SizedBox());
  });
}
