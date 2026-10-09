// coverage:ignore-file
/// Daily limits: today's shutdown time and gaming budget, published by the PC
/// to Firebase, plus requests for the PC to refresh or declare a rest day.
library;

import 'dart:async';

import 'package:daily_limits/screens/home_screen.dart';
import 'package:daily_limits/services/background.dart';
import 'package:daily_limits/services/notifier.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initNotifications();
  await registerBackgroundRefresh();
  runApp(const DailyLimitsApp());
  // After the first frame so the permission dialog does not block startup.
  unawaited(requestNotificationPermission());
}

/// Root widget.
class DailyLimitsApp extends StatelessWidget {
  /// Creates the app.
  const new({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Daily limits',
    theme: buildDarkTheme(),
    home: const HomeScreen(),
  );
}
