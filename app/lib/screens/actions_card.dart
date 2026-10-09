/// "Refresh now" and "Declare rest day", with each request's state:
/// waiting, the PC's answer, or "PC didn't answer" after 3 minutes.
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
      helpText: 'Rest day (future dates only)',
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
              onPressed: signedIn && !(refresh?.isPending ?? false)
                  ? controller.requestRefresh
                  : null,
              child: const Text('Refresh now'),
            ),
            if (refresh != null) _RequestLine(request: refresh),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(
              onPressed: signedIn && !(restDay?.isPending ?? false)
                  ? () => _pickRestDay(context)
                  : null,
              child: const Text('Declare rest day'),
            ),
            if (restDay != null) _RequestLine(request: restDay),
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.sm),
                child: Text(
                  error,
                  style: Theme.of(context).textTheme.bodyLarge
                      ?.copyWith(color: Theme.of(context).colorScheme.error),
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
    final (text, color) = switch ((result, request.timedOut)) {
      (null, true) => ("$what: PC didn't answer", colors.warning),
      (null, false) => ('$what: waiting for the PC…', null),
      (final r?, _) when r.ok => (
        '$what: ${_or(r.message, 'done')}',
        colors.success,
      ),
      (final r?, _) => (
        '$what refused: ${_or(_withoutVerdict(r.message), 'no reason')}',
        colors.danger,
      ),
    };
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: Row(
        children: [
          if (request.isPending)
            const Padding(
              padding: EdgeInsets.only(right: AppSpacing.sm),
              child: SizedBox.square(
                dimension: AppSpacing.md,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          Expanded(
            child: Text(
              text,
              style: theme.textTheme.bodyLarge?.copyWith(color: color),
            ),
          ),
        ],
      ),
    );
  }
}

String _or(String value, String fallback) => value.isEmpty ? fallback : value;

/// [message] without a leading "refused: ": the PC's message already says it,
/// and the line above prints the verdict itself.
String _withoutVerdict(String message) =>
    message.replaceFirst(RegExp(r'^refused:\s*', caseSensitive: false), '');
