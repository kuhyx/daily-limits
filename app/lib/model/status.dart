/// The PC's published `daily_limits/status.json`, parsed into typed values.
///
/// The PC owns every number here; the phone only displays them. Parsing is
/// strict about shape (a wrong type is a [FormatException], shown to the user
/// as "unreadable status") but lenient about absent optional values, which
/// the contract marks as nullable.
library;

import 'dart:convert';

/// How old a status may get before the PC counts as offline.
const Duration kOfflineAfter = Duration(minutes: 15);

/// One earner's state today (`earners[]`).
class EarnerState {
  /// Creates an earner row.
  const new({
    required this.name,
    required this.label,
    required this.status,
    required this.shutdownMinutes,
    required this.gamingMinutes,
  });

  /// Registry key: `workout`, `leetcode`, `reading`, `anki`, `automation`.
  final String name;

  /// Human label from the registry.
  final String label;

  /// `done`, `todo` or `unknown` ("could not check").
  final String status;

  /// Minutes of shutdown extension this earner is worth.
  final int shutdownMinutes;

  /// Minutes of gaming budget this earner is worth.
  final int gamingMinutes;
}

/// One not-yet-earned extension (`todo[]`).
class TodoItem {
  /// Creates a todo row.
  const new({
    required this.name,
    required this.label,
    required this.status,
    required this.shutdownAfter,
  });

  /// Registry key, as in [EarnerState.name].
  final String name;

  /// Human label.
  final String label;

  /// `todo` or `unknown`.
  final String status;

  /// The shutdown time once this is done, `HH:MM`.
  final String shutdownAfter;
}

/// The whole published status.
class DailyStatus {
  /// Creates a status.
  const new({
    required this.date,
    required this.publishedAt,
    required this.deviceId,
    required this.applied,
    required this.resolved,
    required this.floor,
    required this.ceiling,
    required this.gamingDay,
    required this.budgetMinutes,
    required this.usedMinutes,
    required this.ceilingMinutes,
    required this.earners,
    required this.todo,
  });

  /// Parses the JSON text stored at `daily_limits/status.json`.
  factory parse(String text) {
    final root = _map(jsonDecode(text), 'status');
    final shutdown = _map(root['shutdown'], 'shutdown');
    final gaming = _map(root['gaming'], 'gaming');
    return DailyStatus(
      date: _str(root['date'], 'date'),
      publishedAt: DateTime.fromMillisecondsSinceEpoch(
        (_num(root['published_at'], 'published_at') * 1000).round(),
      ),
      deviceId: root['device_id'] as String? ?? '',
      applied: shutdown['applied'] as String?,
      resolved: shutdown['resolved'] as String?,
      floor: shutdown['floor'] as String?,
      ceiling: shutdown['ceiling'] as String?,
      gamingDay: _str(gaming['day'], 'gaming.day'),
      budgetMinutes: _num(gaming['budget_minutes'], 'budget_minutes').round(),
      usedMinutes: (gaming['used_minutes'] as num?)?.round(),
      ceilingMinutes: _num(
        gaming['ceiling_minutes'],
        'ceiling_minutes',
      ).round(),
      earners: [
        for (final e in _list(root['earners'], 'earners'))
          EarnerState(
            name: _str(e['name'], 'earner.name'),
            label: e['label'] as String? ?? e['name'] as String,
            status: _str(e['status'], 'earner.status'),
            shutdownMinutes: (e['shutdown_minutes'] as num? ?? 0).round(),
            gamingMinutes: (e['gaming_minutes'] as num? ?? 0).round(),
          ),
      ],
      todo: [
        for (final t in _list(root['todo'], 'todo'))
          TodoItem(
            name: _str(t['name'], 'todo.name'),
            label: t['label'] as String? ?? t['name'] as String,
            status: t['status'] as String? ?? 'todo',
            shutdownAfter: _str(t['shutdown_after'], 'todo.shutdown_after'),
          ),
      ],
    );
  }

  /// Calendar day the shutdown values apply to, `YYYY-MM-DD`.
  final String date;

  /// When the PC published this (`published_at`).
  final DateTime publishedAt;

  /// The publishing PC's device id.
  final String deviceId;

  /// The shutdown time in force, `HH:MM`, or null when none is applied.
  final String? applied;

  /// What the registry resolves to today; may differ from [applied].
  final String? resolved;

  /// Earliest possible shutdown today.
  final String? floor;

  /// Latest reachable shutdown today.
  final String? ceiling;

  /// The gaming day (06:00 boundary), `YYYY-MM-DD`.
  final String gamingDay;

  /// Gaming minutes allowed this gaming day.
  final int budgetMinutes;

  /// Gaming minutes used, or null when the PC could not tell.
  final int? usedMinutes;

  /// The most the budget can reach today.
  final int ceilingMinutes;

  /// Every earner and whether it is done.
  final List<EarnerState> earners;

  /// What is still left to extend shutdown.
  final List<TodoItem> todo;

  /// Gaming minutes left, or null when [usedMinutes] is unknown.
  int? get leftMinutes {
    final used = usedMinutes;
    return used == null ? null : budgetMinutes - used;
  }

  /// Whether the PC has stopped publishing (status older than 15 min).
  bool isOffline(DateTime now) => now.difference(publishedAt) > kOfflineAfter;
}

Map<String, dynamic> _map(Object? v, String what) => v is Map<String, dynamic>
    ? v
    : throw FormatException('$what is not an object');

List<Map<String, dynamic>> _list(Object? v, String what) {
  if (v == null) return const [];
  if (v is! List) throw FormatException('$what is not a list');
  return [for (final e in v) _map(e, what)];
}

String _str(Object? v, String what) =>
    v is String ? v : throw FormatException('$what is not a string');

num _num(Object? v, String what) =>
    v is num ? v : throw FormatException('$what is not a number');

/// `YYYY-MM-DD` of [d] in local time.
String isoDay(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${_two(d.month)}-${_two(d.day)}';

/// `HH:MM` of [d] in local time.
String hhmm(DateTime d) => '${_two(d.hour)}:${_two(d.minute)}';

String _two(int n) => n.toString().padLeft(2, '0');

/// `1h29`, `45m`, `0m` -- the PC bar's compact duration form.
String compactMinutes(int minutes) {
  final m = minutes < 0 ? 0 : minutes;
  if (m < 60) return '${m}m';
  return '${m ~/ 60}h${_two(m % 60)}';
}

/// Today at `HH:MM` local, or null when [value] is not that shape.
DateTime? todayAt(String? value, DateTime now) {
  final match = RegExp(r'^(\d{1,2}):(\d{2})$').firstMatch(value ?? '');
  if (match == null) return null;
  return DateTime(
    now.year,
    now.month,
    now.day,
    int.parse(match.group(1)!),
    int.parse(match.group(2)!),
  );
}
