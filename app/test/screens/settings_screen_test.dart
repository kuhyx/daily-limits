import 'package:crdt_sync_flutter/testing/fake_secure_storage.dart';
import 'package:daily_limits/screens/settings_screen.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sync_settings_ui/sync_settings_ui.dart';

import '../support/fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late PluginLog log;

  setUp(() {
    installFakeSecureStorage();
    log = installPlatformFakes(tempDir());
  });

  Future<void> pump(WidgetTester tester) => tester.pumpWidget(
    MaterialApp(theme: buildDarkTheme(), home: const SettingsScreen()),
  );

  testWidgets('lists the three tiles', (tester) async {
    await pump(tester);
    expect(find.byKey(const Key('settings-sync')), findsOneWidget);
    expect(find.byKey(const Key('settings-widget')), findsOneWidget);
    expect(find.byKey(const Key('settings-test-notify')), findsOneWidget);
  });

  testWidgets('Add widget asks the launcher to pin it', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('settings-widget')));
    await tester.pump();
    expect(log.named('requestPinWidget'), hasLength(1));
  });

  testWidgets('Send a test notification shows it', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('settings-test-notify')));
    await tester.pump();
    expect(log.named('requestNotificationsPermission'), isNotEmpty);
    expect(log.titles('show'), ['🔔']);
  });

  testWidgets('Sync settings opens the shared sync screen', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('settings-sync')));
    await tester.pumpAndSettle();
    expect(find.byType(SyncSettingsScreen), findsOneWidget);
  });
}
