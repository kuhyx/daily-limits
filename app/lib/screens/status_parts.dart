/// Building blocks shared by the status cards and the offline banner: a
/// glyph + value row and a card with a leading section glyph.
library;

import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// A small glyph, then [value]; [spoken] is what a screen reader says.
class GlyphValue extends StatelessWidget {
  /// Creates the row.
  const new({
    required this.icon,
    required this.value,
    required this.spoken,
    this.color,
    super.key,
  });

  /// The glyph that names the value.
  final IconData icon;

  /// A number, time or date.
  final String value;

  /// The spoken-only description.
  final String spoken;

  /// Muted rows pass the muted colour.
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.bodyLarge?.copyWith(color: color);
    return MergeSemantics(
      child: Row(
        children: [
          Icon(icon, size: 20, color: color, semanticLabel: spoken),
          const SizedBox(width: AppSpacing.sm),
          ExcludeSemantics(child: Text(value, style: style)),
        ],
      ),
    );
  }
}

/// A card with a leading section glyph and its rows beside it.
class StatusSection extends StatelessWidget {
  /// Creates the section.
  const new({
    required this.icon,
    required this.spoken,
    required this.children,
    super.key,
  });

  /// The section's glyph.
  final IconData icon;

  /// The section's spoken name.
  final String spoken;

  /// The rows.
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, semanticLabel: spoken),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: children,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
