/// The one-line home-screen widget: `🔌 20:00 · 🎮 1h29 · +💪 +🧩`.
///
/// The Kotlin side (`DailyLimitsWidget.kt`) only renders what is saved here:
/// the line and whether to grey it out.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/ui/earner_icons.dart';
import 'package:home_widget/home_widget.dart';

/// Fully-qualified Android provider class.
const String kWidgetProvider = 'com.kuhy.daily_limits.DailyLimitsWidget';

/// The widget line before the PC has published anything (also the Kotlin
/// fallback before the first save).
const String kWidgetNoData = '⏳';

/// Appended when the PC is offline; the Kotlin side also greys the line.
const String kWidgetOffline = '💤';

/// The widget line for [status]; [kWidgetNoData] when there is none.
String widgetLine(DailyStatus? status, DateTime now) {
  if (status == null) return kWidgetNoData;
  final parts = <String>[
    '$kShutdownIcon ${status.applied ?? '--:--'}',
    _gamingPart(status),
  ];
  final extend = [for (final t in status.todo) '+${earnerIcon(t.name)}'];
  if (extend.isNotEmpty) parts.add(extend.join(' '));
  final line = parts.join(' · ');
  return status.isOffline(now) ? '$line $kWidgetOffline' : line;
}

/// `🎮 1h29` left, or `🎮 ?/5h00` (use unknown, budget) when not checked.
String _gamingPart(DailyStatus status) {
  final left = status.leftMinutes;
  return left == null
      ? '🎮 ?/${compactMinutes(status.budgetMinutes)}'
      : '🎮 ${compactMinutes(left)}';
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
