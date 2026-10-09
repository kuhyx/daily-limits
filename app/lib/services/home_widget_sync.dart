/// The one-line home-screen widget: `🔌 20:00 · 🎮 1h29 left · +💪 +🧩`.
///
/// The Kotlin side (`DailyLimitsWidget.kt`) only renders what is saved here:
/// the line and whether to grey it out.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/ui/earner_icons.dart';
import 'package:home_widget/home_widget.dart';

/// Fully-qualified Android provider class.
const String kWidgetProvider = 'com.kuhy.daily_limits.DailyLimitsWidget';

/// The widget line for [status]; a placeholder when there is none.
String widgetLine(DailyStatus? status, DateTime now) {
  if (status == null) return 'Daily limits: no data yet';
  final parts = <String>[
    '$kShutdownIcon ${status.applied ?? '--:--'}',
    _gamingPart(status),
  ];
  final extend = [for (final t in status.todo) '+${earnerIcon(t.name)}'];
  if (extend.isNotEmpty) parts.add(extend.join(' '));
  final line = parts.join(' · ');
  return status.isOffline(now) ? '$line (offline)' : line;
}

String _gamingPart(DailyStatus status) {
  final left = status.leftMinutes;
  return left == null
      ? '🎮 ${compactMinutes(status.budgetMinutes)} budget'
      : '🎮 ${compactMinutes(left)} left';
}

/// Saves the line for [status] and asks the launcher to redraw.
Future<void> updateHomeWidget(DailyStatus? status) async {
  final now = DateTime.now();
  final offline = status == null || status.isOffline(now);
  await HomeWidget.saveWidgetData<String>('line', widgetLine(status, now));
  await HomeWidget.saveWidgetData<bool>('offline', offline);
  await HomeWidget.updateWidget(qualifiedAndroidName: kWidgetProvider);
}

/// Asks the launcher to pin the widget (shows the system "Add" dialog).
Future<void> requestPinWidget() =>
    HomeWidget.requestPinWidget(qualifiedAndroidName: kWidgetProvider);
