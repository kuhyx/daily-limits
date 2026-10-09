/// The read-only half of the main screen: shutdown, gaming, how to extend,
/// and the earners. Greyed as a whole when the PC is offline.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/ui/earner_icons.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// Renders a [DailyStatus].
class StatusView extends StatelessWidget {
  /// Creates the view.
  const new({required this.status, required this.now, super.key});

  /// What the PC published.
  final DailyStatus status;

  /// The clock used for "today" and "offline" decisions.
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final offline = status.isOffline(now);
    final body = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _ShutdownCard(status: status),
        const SizedBox(height: AppSpacing.md),
        _GamingCard(status: status, today: isoDay(now)),
        if (status.todo.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          _ExtendLine(todo: status.todo),
        ],
        const SizedBox(height: AppSpacing.md),
        _EarnersCard(earners: status.earners),
      ],
    );
    if (!offline) return body;
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          color: theme.colorScheme.surfaceContainerHighest,
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Text(
              'PC offline since ${hhmm(status.publishedAt)} — '
              'showing the last values it published.',
              style: theme.textTheme.bodyLarge,
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        // Greyed: desaturated and dimmed, so stale numbers never read as live.
        Opacity(
          opacity: 0.5,
          child: ColorFiltered(
            colorFilter: const ColorFilter.matrix(_greyscale),
            child: body,
          ),
        ),
      ],
    );
  }
}

const List<double> _greyscale = [
  0.2126, 0.7152, 0.0722, 0, 0, //
  0.2126, 0.7152, 0.0722, 0, 0, //
  0.2126, 0.7152, 0.0722, 0, 0, //
  0, 0, 0, 1, 0, //
];

class _ShutdownCard extends StatelessWidget {
  const new({required this.status});

  final DailyStatus status;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.colorScheme.onSurfaceVariant;
    final resolved = status.resolved;
    return _Section(
      title: 'Shutdown',
      children: [
        Text(
          '$kShutdownIcon ${status.applied ?? 'none applied'}',
          style: theme.textTheme.headlineMedium,
        ),
        if (resolved != null && resolved != status.applied)
          Text(
            'Registry resolves to $resolved',
            style: theme.textTheme.bodyLarge,
          ),
        Text(
          'Floor ${status.floor ?? '?'} → ceiling ${status.ceiling ?? '?'}',
          style: theme.textTheme.bodyLarge?.copyWith(color: muted),
        ),
      ],
    );
  }
}

class _GamingCard extends StatelessWidget {
  const new({required this.status, required this.today});

  final DailyStatus status;
  final String today;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.colorScheme.onSurfaceVariant;
    final left = status.leftMinutes;
    final used = status.usedMinutes;
    return _Section(
      title: status.gamingDay == today
          ? 'Gaming'
          : 'Gaming (day ${status.gamingDay})',
      children: [
        Text(
          left == null ? '🎮 ? left' : '🎮 ${compactMinutes(left)} left',
          style: theme.textTheme.headlineMedium,
        ),
        Text(
          used == null
              ? 'Used: could not check · budget '
                    '${compactMinutes(status.budgetMinutes)}'
              : 'Used ${compactMinutes(used)} of '
                    '${compactMinutes(status.budgetMinutes)}',
          style: theme.textTheme.bodyLarge,
        ),
        Text(
          'Ceiling ${compactMinutes(status.ceilingMinutes)}',
          style: theme.textTheme.bodyLarge?.copyWith(color: muted),
        ),
      ],
    );
  }
}

class _ExtendLine extends StatelessWidget {
  const new({required this.todo});

  final List<TodoItem> todo;

  @override
  Widget build(BuildContext context) {
    final items = [for (final t in todo) _extendItem(t)];
    return _Section(
      title: 'To extend',
      children: [
        Text(items.join(', '), style: Theme.of(context).textTheme.bodyLarge),
      ],
    );
  }
}

class _EarnersCard extends StatelessWidget {
  const new({required this.earners});

  final List<EarnerState> earners;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = context.statusColors;
    return _Section(
      title: 'Earners',
      children: [
        if (earners.isEmpty) Text('None', style: theme.textTheme.bodyLarge),
        for (final e in earners)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
            child: Row(
              children: [
                SizedBox(
                  width: AppSpacing.xl,
                  child: Text(
                    earnerIcon(e.name),
                    style: theme.textTheme.titleMedium,
                  ),
                ),
                Expanded(
                  child: Text(e.label, style: theme.textTheme.bodyLarge),
                ),
                Text(
                  switch (e.status) {
                    'done' => 'done',
                    'todo' => 'to do',
                    _ => 'could not check',
                  },
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: switch (e.status) {
                      'done' => colors.success,
                      'todo' => theme.colorScheme.onSurface,
                      _ => colors.warning,
                    },
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  const new({required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: theme.textTheme.labelLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            ...children,
          ],
        ),
      ),
    );
  }
}

/// `💪 Workout → 20:50`, marked `(?)` when the PC could not check it.
String _extendItem(TodoItem t) {
  final mark = t.status == 'unknown' ? ' (?)' : '';
  return '${earnerIcon(t.name)} ${t.label} → ${t.shutdownAfter}$mark';
}
