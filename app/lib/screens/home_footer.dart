/// The home screen's footer: publish and read times plus the kuhy credit.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/services/sync_once.dart';
import 'package:design_system/design_system.dart';
import 'package:kuhy_credit/kuhy_credit.dart';
import 'package:material_ui/material_ui.dart';

/// Upload and download time stamps above the shared credit.
class HomeFooter extends StatelessWidget {
  /// Creates the footer for [outcome] and its parsed [status].
  const new({required this.outcome, required this.status, super.key});

  /// The last sync, whose fetch time is the download stamp.
  final SyncOutcome outcome;

  /// The published status, whose publish time is the upload stamp.
  final DailyStatus? status;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final fetched = outcome.cache.fetchedAt;
    final published = status?.publishedAt;
    final hasTimestamps = published != null || fetched != null;
    final muted = theme.colorScheme.onSurfaceVariant;
    final style = theme.textTheme.bodySmall?.copyWith(color: muted);
    // Upload = when the PC published, download = when this phone read it.
    Widget stamp(IconData icon, DateTime at, String spoken) => MergeSemantics(
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: muted, semanticLabel: spoken),
          const SizedBox(width: AppSpacing.xs),
          ExcludeSemantics(child: Text(hhmm(at), style: style)),
        ],
      ),
    );
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (hasTimestamps) ...[
          Wrap(
            alignment: WrapAlignment.center,
            spacing: AppSpacing.md,
            children: [
              if (published != null)
                stamp(Icons.upload, published, 'Published ${hhmm(published)}'),
              if (fetched != null)
                stamp(Icons.download, fetched, 'read ${hhmm(fetched)}'),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
        ],
        const KuhyCredit(size: 24),
      ],
    );
  }
}
