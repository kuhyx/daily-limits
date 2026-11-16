/// The read-only half of the main screen: shutdown, gaming, how to extend,
/// and the earners. Greyed as a whole when the PC is offline.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/status_cards.dart';
import 'package:daily_limits/screens/status_parts.dart';
import 'package:design_system/design_system.dart';
import 'package:material_ui/material_ui.dart';

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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        OfflineBanner(since: status.publishedAt),
        const SizedBox(height: AppSpacing.md),
        GreyedOut(child: body),
      ],
    );
  }
}

/// The "PC is off, these are its last values" card.
class OfflineBanner extends StatelessWidget {
  /// Creates the banner.
  const new({required this.since, super.key});

  /// When the PC last published.
  final DateTime since;

  @override
  Widget build(BuildContext context) {
    final at = hhmm(since);
    return Card(
      key: const Key('status-offline'),
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        // Desktop with a slash + the last publish time.
        child: GlyphValue(
          icon: Icons.desktop_access_disabled,
          value: at,
          spoken: 'PC offline since $at, showing the last values it published',
        ),
      ),
    );
  }
}

/// Desaturated and dimmed, so stale numbers never read as live.
class GreyedOut extends StatelessWidget {
  /// Creates the wrapper.
  const new({required this.child, super.key});

  /// What to grey.
  final Widget child;

  @override
  Widget build(BuildContext context) => Opacity(
    opacity: 0.5,
    child: ColorFiltered(
      colorFilter: const ColorFilter.matrix(_greyscale),
      child: child,
    ),
  );
}

const List<double> _greyscale = [
  0.2126, 0.7152, 0.0722, 0, 0, //
  0.2126, 0.7152, 0.0722, 0, 0, //
  0.2126, 0.7152, 0.0722, 0, 0, //
  0, 0, 0, 1, 0, //
];
