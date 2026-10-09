// coverage:ignore-file
/// On-device probe for the scheduled shutdown warning.
///
/// Schedules the real warnings through [scheduleShutdownWarnings] for a
/// fixture status whose shutdown is 11 minutes away, so the 10-minute warning
/// fires about a minute after launch through the same `zonedSchedule` →
/// exact alarm → receiver path the real 21:30/21:50 warnings use. It never
/// syncs, so nothing reschedules over the fixture while it waits.
///
/// Deploy with `phone_deploy.sh ... --release --target
/// lib/main_probe_shutdown.dart`, then redeploy the normal entry point: its
/// first pass cancels and replaces both warnings with the real ones.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/services/notifier.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initNotifications();
  final now = DateTime.now();
  final shutdown = now.add(const Duration(minutes: 11));
  final applied = '${_two(shutdown.hour)}:${_two(shutdown.minute)}';
  await scheduleShutdownWarnings(
    DailyStatus(
      date: isoDay(now),
      publishedAt: now,
      deviceId: 'probe',
      applied: applied,
      resolved: applied,
      floor: null,
      ceiling: null,
      gamingDay: isoDay(now),
      budgetMinutes: 0,
      usedMinutes: null,
      ceilingMinutes: 0,
      earners: const [],
      todo: const [],
    ),
  );
  runApp(
    MaterialApp(
      title: 'Daily limits (shutdown probe)',
      theme: buildDarkTheme(),
      home: Scaffold(
        body: Center(child: Text('Probe: shutdown $applied, warning at -10')),
      ),
    ),
  );
}

String _two(int n) => n.toString().padLeft(2, '0');
