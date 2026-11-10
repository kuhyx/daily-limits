/// The cards inside `StatusView`: shutdown, gaming, how to extend, earners.
///
/// Text-free (textgate): every value is a number, a time or a glyph; the old
/// wording survives only as the spoken `semanticLabel`.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/status_parts.dart';
import 'package:daily_limits/ui/earner_icons.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// Applied shutdown, the registry's answer when it differs, floor → ceiling.
class ShutdownCard extends StatelessWidget {
  /// Creates the card.
  const new({required this.status, super.key});

  /// What the PC published.
  final DailyStatus status;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.colorScheme.onSurfaceVariant;
    final resolved = status.resolved;
    final applied = status.applied;
    return StatusSection(
      icon: Icons.power_settings_new,
      spoken: 'Shutdown',
      children: [
        Text(
          '$kShutdownIcon ${applied ?? '--:--'}',
          semanticsLabel: applied == null ? 'No shutdown applied' : null,
          style: theme.textTheme.headlineMedium,
        ),
        if (resolved != null && resolved != applied)
          GlyphValue(
            icon: Icons.calculate,
            value: resolved,
            spoken: 'Registry resolves to $resolved',
          ),
        GlyphValue(
          icon: Icons.height,
          value: '${status.floor ?? '?'} → ${status.ceiling ?? '?'}',
          spoken: 'Floor ${status.floor} to ceiling ${status.ceiling}',
          color: muted,
        ),
      ],
    );
  }
}

/// Minutes left, used of budget, and the ceiling, for the gaming day.
class GamingCard extends StatelessWidget {
  /// Creates the card.
  const new({required this.status, required this.today, super.key});

  /// What the PC published.
  final DailyStatus status;

  /// Today's calendar day; a different gaming day is shown with its date.
  final String today;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final muted = theme.colorScheme.onSurfaceVariant;
    final left = status.leftMinutes;
    final used = status.usedMinutes;
    final budget = compactMinutes(status.budgetMinutes);
    return StatusSection(
      icon: Icons.sports_esports,
      spoken: 'Gaming',
      children: [
        if (status.gamingDay != today)
          GlyphValue(
            icon: Icons.event,
            value: status.gamingDay,
            spoken: 'Gaming day ${status.gamingDay}',
          ),
        Text(
          '🎮 ${left == null ? '?' : compactMinutes(left)}',
          semanticsLabel: left == null ? 'Gaming left could not check' : null,
          style: theme.textTheme.headlineMedium,
        ),
        GlyphValue(
          icon: Icons.hourglass_bottom,
          value: '${used == null ? '?' : compactMinutes(used)} / $budget',
          spoken: used == null
              ? 'Used could not check, budget $budget'
              : 'Used ${compactMinutes(used)} of $budget',
        ),
        GlyphValue(
          icon: Icons.vertical_align_top,
          value: compactMinutes(status.ceilingMinutes),
          spoken: 'Ceiling ${compactMinutes(status.ceilingMinutes)}',
          color: muted,
        ),
      ],
    );
  }
}

/// What can still extend the shutdown: `💪 → 20:50`, `?` when unchecked.
class ExtendLine extends StatelessWidget {
  /// Creates the line.
  const new({required this.todo, super.key});

  /// The earners still to do.
  final List<TodoItem> todo;

  @override
  Widget build(BuildContext context) {
    return StatusSection(
      icon: Icons.more_time,
      spoken: 'To extend',
      children: [
        Text(
          [for (final t in todo) _extendItem(t)].join('   '),
          semanticsLabel: [
            for (final t in todo) '${t.label} until ${t.shutdownAfter}',
          ].join(', '),
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ],
    );
  }
}

/// Each earner's glyph and a done / to do / could-not-check mark.
class EarnersCard extends StatelessWidget {
  /// Creates the card.
  const new({required this.earners, super.key});

  /// The earners the PC reported.
  final List<EarnerState> earners;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = context.statusColors;
    return StatusSection(
      icon: Icons.emoji_events,
      spoken: 'Earners',
      children: [
        if (earners.isEmpty)
          Icon(
            Icons.remove,
            color: theme.colorScheme.outline,
            semanticLabel: 'None',
          ),
        for (final e in earners)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
            child: Row(
              children: [
                SizedBox(
                  width: AppSpacing.xl,
                  child: ExcludeSemantics(
                    child: Text(
                      earnerIcon(e.name),
                      style: theme.textTheme.titleMedium,
                    ),
                  ),
                ),
                Icon(
                  key: Key('earner-${e.name}-${e.status}'),
                  switch (e.status) {
                    'done' => Icons.check_circle,
                    'todo' => Icons.radio_button_unchecked,
                    _ => Icons.help_outline,
                  },
                  color: switch (e.status) {
                    'done' => colors.success,
                    'todo' => theme.colorScheme.onSurface,
                    _ => colors.warning,
                  },
                  semanticLabel: switch (e.status) {
                    'done' => '${e.label} done',
                    'todo' => '${e.label} to do',
                    _ => '${e.label} could not check',
                  },
                ),
              ],
            ),
          ),
      ],
    );
  }
}

/// `💪 → 20:50`, with a `?` when the PC could not check it.
String _extendItem(TodoItem t) {
  final mark = t.status == 'unknown' ? ' ?' : '';
  return '${earnerIcon(t.name)} → ${t.shutdownAfter}$mark';
}
