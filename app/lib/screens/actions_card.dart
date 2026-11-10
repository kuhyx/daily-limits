/// "Refresh now" and "Declare rest day" as icon buttons, with each request's
/// state as a glyph: spinner while waiting, check or block for the PC's
/// answer, a clock for "no answer yet" after 3 minutes -- which an answer
/// arriving later still replaces.
library;

import 'package:daily_limits/services/limits_controller.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// The two actions. The PC enforces; these only ask.
class ActionsCard extends StatelessWidget {
  /// Creates the card.
  const new({required this.controller, required this.signedIn, super.key});

  /// Sends the requests.
  final LimitsController controller;

  /// Disables both actions until the device is signed in.
  final bool signedIn;

  Future<void> _pickRestDay(BuildContext context) async {
    final now = DateTime.now();
    final tomorrow = DateTime(now.year, now.month, now.day + 1);
    final day = await showDatePicker(
      context: context,
      initialDate: tomorrow,
      firstDate: tomorrow,
      lastDate: tomorrow.add(const Duration(days: 365)),
      // Blank header instead of our own caption; the picker's own framework
      // text is a follow-up (custom icon picker), per textgate decision 5.
      helpText: '',
    );
    if (day != null) await controller.declareRestDay(day);
  }

  @override
  Widget build(BuildContext context) {
    final refresh = controller.latest(RequestKind.refresh);
    final restDay = controller.latest(RequestKind.restDay);
    final error = controller.actionError;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            FilledButton(
              key: const Key('action-refresh'),
              onPressed: signedIn && !(refresh?.isPending ?? false)
                  ? controller.requestRefresh
                  : null,
              child: const Icon(Icons.refresh, semanticLabel: 'Refresh now'),
            ),
            if (refresh != null) _RequestLine(request: refresh),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(
              key: const Key('action-rest'),
              onPressed: signedIn && !(restDay?.isPending ?? false)
                  ? () => _pickRestDay(context)
                  : null,
              child: const Icon(
                Icons.beach_access,
                semanticLabel: 'Declare rest day',
              ),
            ),
            if (restDay != null) _RequestLine(request: restDay),
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.sm),
                child: Icon(
                  Icons.error_outline,
                  key: const Key('action-error'),
                  color: Theme.of(context).colorScheme.error,
                  semanticLabel: error,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _RequestLine extends StatelessWidget {
  const new({required this.request});

  final SentRequest request;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = context.statusColors;
    final what = request.kind == RequestKind.restDay
        ? 'Rest day ${request.date}'
        : 'Refresh';
    final result = request.result;
    // Glyph + colour per state; the old sentence (with the PC's message) is
    // spoken only. A pending request also spins.
    final (icon, color, spoken) = switch ((result, request.timedOut)) {
      (null, true) => (
        Icons.schedule,
        colors.warning,
        '$what: no answer yet (PC may be off)',
      ),
      (null, false) => (null, null, '$what: waiting for the PC'),
      (final r?, _) when r.ok => (
        Icons.check_circle,
        colors.success,
        '$what: ${_or(r.message, 'done')}',
      ),
      (final r?, _) => (
        Icons.block,
        colors.danger,
        '$what refused: ${_or(_withoutVerdict(r.message), 'no reason')}',
      ),
    };
    final date = request.date;
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: MergeSemantics(
        child: Row(
          key: Key('request-${request.kind.wire}'),
          children: [
            if (request.isPending)
              Semantics(
                label: spoken,
                child: const SizedBox.square(
                  dimension: AppSpacing.md,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            if (icon != null) Icon(icon, color: color, semanticLabel: spoken),
            if (date != null) ...[
              const SizedBox(width: AppSpacing.sm),
              ExcludeSemantics(
                child: Text(
                  date,
                  style: theme.textTheme.bodyLarge?.copyWith(color: color),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

String _or(String value, String fallback) => value.isEmpty ? fallback : value;

/// [message] without a leading "refused: ": the PC's message already says it,
/// and the line above prints the verdict itself.
String _withoutVerdict(String message) =>
    message.replaceFirst(RegExp(r'^refused:\s*', caseSensitive: false), '');
