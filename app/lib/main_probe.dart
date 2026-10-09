// coverage:ignore-file
/// On-device probe for the refused rest-day round trip.
///
/// The real app, plus one rest-day request for *yesterday* sent through the
/// real controller once the first pass is done. screen-locker refuses past
/// dates, so this exercises send → Firebase → PC refusal → phone poll →
/// result line + notification without ever writing a rest day. The UI cannot
/// do this: its date picker starts at tomorrow.
///
/// Deploy with `phone_deploy.sh ... --release --target lib/main_probe.dart`,
/// then redeploy the normal entry point.
library;

import 'dart:async';

import 'package:daily_limits/screens/home_screen.dart';
import 'package:daily_limits/services/background.dart';
import 'package:daily_limits/services/limits_controller.dart';
import 'package:daily_limits/services/notifier.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initNotifications();
  await registerBackgroundRefresh();
  final controller = LimitsController();
  runApp(
    MaterialApp(
      title: 'Daily limits (probe)',
      theme: buildDarkTheme(),
      home: HomeScreen(controller: controller),
    ),
  );
  await controller.refresh();
  final yesterday = DateTime.now().subtract(const Duration(days: 1));
  unawaited(controller.declareRestDay(yesterday));
}
