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
    expect(find.text('Sync settings'), findsOneWidget);
    expect(find.text('Add widget to home screen'), findsOneWidget);
    expect(find.text('Send a test notification'), findsOneWidget);
  });

  testWidgets('Add widget asks the launcher to pin it', (tester) async {
    await pump(tester);
    await tester.tap(find.text('Add widget to home screen'));
    await tester.pump();
    expect(log.named('requestPinWidget'), hasLength(1));
  });

  testWidgets('Send a test notification shows it', (tester) async {
    await pump(tester);
    await tester.tap(find.text('Send a test notification'));
    await tester.pump();
    expect(log.named('requestNotificationsPermission'), isNotEmpty);
    expect(log.titles('show'), ['Daily limits: test notification']);
  });

  testWidgets('Sync settings opens the shared sync screen', (tester) async {
    await pump(tester);
    await tester.tap(find.text('Sync settings'));
    await tester.pumpAndSettle();
    expect(find.byType(SyncSettingsScreen), findsOneWidget);
  });
}
