/// The detail sheets behind the home tiles. Each rebuilds from the
/// controller, so a request line updates while its sheet is open.
library;

import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/actions_card.dart';
import 'package:daily_limits/screens/status_cards.dart';
import 'package:daily_limits/services/limits_controller.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// Which sheet a tile opens.
enum HomeSheet {
  /// Applied shutdown, registry answer, floor to ceiling, how to extend.
  shutdown,

  /// Minutes left, used of budget, ceiling.
  gaming,

  /// Every earner's state.
  earners,

  /// Refresh now, declare rest day, their request lines.
  ask,
}

/// Opens [sheet] over the home grid; its body scrolls inside the sheet only.
Future<void> showHomeSheet(
  BuildContext context,
  LimitsController controller,
  HomeSheet sheet,
) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  showDragHandle: true,
  useSafeArea: true,
  builder: (_) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) => SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        0,
        AppSpacing.md,
        AppSpacing.md,
      ),
      child: _body(context, controller, sheet),
    ),
  ),
);

Widget _body(BuildContext context, LimitsController controller, HomeSheet s) {
  final outcome = controller.outcome;
  final status = outcome?.status;
  final now = DateTime.now();
  return Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    mainAxisSize: MainAxisSize.min,
    children: switch (s) {
      HomeSheet.shutdown => [
        if (status != null) ShutdownCard(status: status),
        if (status != null && status.todo.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          ExtendLine(todo: status.todo),
        ],
      ],
      HomeSheet.gaming => [
        if (status != null) GamingCard(status: status, today: isoDay(now)),
      ],
      HomeSheet.earners => [
        if (status != null) EarnersCard(earners: status.earners),
      ],
      HomeSheet.ask => [
        ActionsCard(
          controller: controller,
          signedIn: (outcome?.signedIn ?? false) && !(outcome?.locked ?? true),
        ),
      ],
    },
  );
}
