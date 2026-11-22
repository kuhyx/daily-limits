import 'package:crdt_sync_flutter/testing/fake_secure_storage.dart';
import 'package:daily_limits/screens/settings_screen.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';

import '../support/fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    installFakeSecureStorage();
    installPlatformFakes(tempDir());
  });

  Future<void> pump(WidgetTester tester, Widget home) async {
    tester.view.physicalSize = const Size(800, 3000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(home: home));
  }

  testWidgets('SettingsScreen tooltips', (tester) async {
    await pump(tester, const SettingsScreen());
    expect(find.byTooltip('Sync'), findsOneWidget);
    expect(find.byTooltip('Widget'), findsOneWidget);
    expect(find.byTooltip('Notify'), findsOneWidget);
  });
}
