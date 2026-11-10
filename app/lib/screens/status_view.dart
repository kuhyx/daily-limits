/// The read-only half of the main screen: shutdown, gaming, how to extend,
/// and the earners. Greyed as a whole when the PC is offline.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/status_cards.dart';
import 'package:daily_limits/screens/status_parts.dart';
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
        ShutdownCard(status: status),
        const SizedBox(height: AppSpacing.md),
        GamingCard(status: status, today: isoDay(now)),
        if (status.todo.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          ExtendLine(todo: status.todo),
        ],
        const SizedBox(height: AppSpacing.md),
        EarnersCard(earners: status.earners),
      ],
    );
    if (!offline) return body;
    final theme = Theme.of(context);
    final since = hhmm(status.publishedAt);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          key: const Key('status-offline'),
          color: theme.colorScheme.surfaceContainerHighest,
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            // Desktop with a slash + the last publish time: the PC is off and
            // the cards below are its last values.
            child: GlyphValue(
              icon: Icons.desktop_access_disabled,
              value: since,
              spoken:
                  'PC offline since $since, showing the last values '
                  'it published',
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
