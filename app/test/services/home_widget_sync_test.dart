import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/services/home_widget_sync.dart';
import 'package:daily_limits/ui/earner_icons.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final now = DateTime.now();

  DailyStatus status({
    DateTime? published,
    int? used = 120,
    List<Map<String, Object?>>? todo,
  }) => DailyStatus.parse(
    statusJson(published: published ?? now, used: used, todo: todo),
  );

  group('widgetLine', () {
    test('shutdown, gaming left and what still extends', () {
      expect(
        widgetLine(status(), now),
        '$kShutdownIcon 22:00 · 🎮 3h00 left · +💪',
      );
    });

    test('shows the budget when use is unknown, and no empty extend part', () {
      expect(
        widgetLine(status(used: null, todo: const []), now),
        '$kShutdownIcon 22:00 · 🎮 5h00 budget',
      );
    });

    test('marks an offline PC', () {
      final stale = status(
        published: now.subtract(const Duration(minutes: 30)),
      );
      expect(widgetLine(stale, now), endsWith('(offline)'));
    });

    test('a placeholder before any status, and --:-- with none applied', () {
      expect(widgetLine(null, now), 'Daily limits: no data yet');
      final none = DailyStatus.parse(statusJson(published: now, applied: null));
      expect(widgetLine(none, now), startsWith('$kShutdownIcon --:--'));
    });
  });

  test('earnerIcon falls back to a bullet', () {
    expect(earnerIcon('reading'), '📖');
    expect(earnerIcon('unknown-earner'), '•');
  });

  test('updateHomeWidget saves the line and the grey flag', () async {
    final log = installPlatformFakes(tempDir());
    await updateHomeWidget(status());
    expect(log.widgetData('line'), contains('22:00'));
    expect(log.widgetData('offline'), isFalse);
    expect(log.named('updateWidget'), hasLength(1));
    await updateHomeWidget(null);
    expect(log.widgetData('offline'), isTrue);
  });

  test('requestPinWidget asks the launcher for this provider', () async {
    final log = installPlatformFakes(tempDir());
    await requestPinWidget();
    final args = log.named('requestPinWidget').single.arguments as Map;
    expect(args['qualifiedAndroidName'], kWidgetProvider);
  });
}
