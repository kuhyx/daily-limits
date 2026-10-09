// coverage:ignore-file
/// On-device layout preview: fixture JSON through the real parser and the
/// real status view, fresh and offline, plus the widget line for each.
///
/// Deploy with `phone_deploy.sh ... --target lib/main_preview.dart`. Never
/// touches Firebase, notifications or the cache.
library;

import 'dart:convert';

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/status_view.dart';
import 'package:daily_limits/services/home_widget_sync.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

void main() => runApp(const _PreviewApp());

String _fixture(DateTime published, String gamingDay) => jsonEncode({
  'date': isoDay(DateTime.now()),
  'generated_at': published.toIso8601String(),
  'published_at': published.millisecondsSinceEpoch ~/ 1000,
  'device_id': 'pc-preview',
  'shutdown': {
    'applied': '20:00',
    'resolved': '20:30',
    'floor': '19:00',
    'ceiling': '23:00',
  },
  'gaming': {
    'day': gamingDay,
    'budget_minutes': 120,
    'used_minutes': 31,
    'ceiling_minutes': 180,
  },
  'earners': [
    for (final (name, label, status) in [
      ('workout', 'Workout', 'todo'),
      ('leetcode', 'LeetCode', 'todo'),
      ('reading', 'Reading', 'done'),
      ('anki', 'Anki', 'unknown'),
      ('automation', 'Automation', 'done'),
    ])
      {
        'name': name,
        'label': label,
        'status': status,
        'shutdown_minutes': 50,
        'gaming_minutes': 30,
      },
  ],
  'todo': [
    {
      'name': 'workout',
      'label': 'Workout',
      'status': 'todo',
      'shutdown_after': '20:50',
    },
    {
      'name': 'leetcode',
      'label': 'LeetCode',
      'status': 'todo',
      'shutdown_after': '21:40',
    },
    {
      'name': 'anki',
      'label': 'Anki',
      'status': 'unknown',
      'shutdown_after': '22:00',
    },
  ],
});

class _PreviewApp extends StatelessWidget {
  const new();

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final yesterday = now.subtract(const Duration(days: 1));
    final fresh = DailyStatus.parse(
      _fixture(now.subtract(const Duration(minutes: 2)), isoDay(now)),
    );
    final stale = DailyStatus.parse(
      _fixture(now.subtract(const Duration(minutes: 40)), isoDay(yesterday)),
    );
    return MaterialApp(
      theme: buildDarkTheme(),
      home: Scaffold(
        appBar: AppBar(title: const Text('Daily limits (preview)')),
        body: ListView(
          padding: const EdgeInsets.all(AppSpacing.md),
          children: [
            Text('Widget: ${widgetLine(fresh, now)}'),
            const SizedBox(height: AppSpacing.md),
            StatusView(status: fresh, now: now),
            const SizedBox(height: AppSpacing.xl),
            Text('Widget: ${widgetLine(stale, now)}'),
            const SizedBox(height: AppSpacing.md),
            StatusView(status: stale, now: now),
          ],
        ),
      ),
    );
  }
}
