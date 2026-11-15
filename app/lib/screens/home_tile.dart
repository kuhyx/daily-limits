/// One square on the home grid: a glyph and one headline value. Tap and
/// long-press open the same sheet (no gesture-only feature).
library;

import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// A tappable tile.
class HomeTile extends StatelessWidget {
  /// Creates the tile.
  const new({
    required this.icon,
    required this.spoken,
    required this.onOpen,
    this.value,
    this.badge,
    super.key,
  });

  /// The glyph that names the tile.
  final IconData icon;

  /// What a screen reader says.
  final String spoken;

  /// The headline number or time, or null for a glyph-only tile.
  final String? value;

  /// A state mark under the glyph (spinner, warning).
  final Widget? badge;

  /// Opens the tile's sheet; null disables the tile.
  final VoidCallback? onOpen;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Semantics(
      button: true,
      label: spoken,
      excludeSemantics: true,
      child: Card(
        margin: EdgeInsets.zero,
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onOpen,
          onLongPress: onOpen,
          child: Center(
            child: FittedBox(
              fit: BoxFit.scaleDown,
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(icon, size: 48),
                    if (value != null) ...[
                      const SizedBox(height: AppSpacing.sm),
                      Text(value!, style: theme.textTheme.headlineMedium),
                    ],
                    if (badge != null) ...[
                      const SizedBox(height: AppSpacing.sm),
                      badge!,
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
