import 'package:daily_limits/screens/actions_card.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fake_controller.dart';

void main() {
  final created = DateTime(2026, 10, 9, 12);
  SentRequest request({
    RequestKind kind = RequestKind.refresh,
    String? date,
    RequestResult? result,
    bool timedOut = false,
  }) => SentRequest(
    id: 'id-${kind.wire}',
    kind: kind,
    date: date,
    createdAt: created,
    result: result,
    timedOut: timedOut,
  );

  Future<FakeController> pump(
    WidgetTester tester, {
    List<SentRequest> requests = const [],
    bool signedIn = true,
    String? actionError,
  }) async {
    final controller = FakeController(
      emptyOutcome(requests: requests),
      actionError: actionError,
    );
    await tester.pumpWidget(
      MaterialApp(
        theme: buildDarkTheme(),
        home: Scaffold(
          body: SingleChildScrollView(
            child: ActionsCard(controller: controller, signedIn: signedIn),
          ),
        ),
      ),
    );
    return controller;
  }

  bool enabled(WidgetTester tester, String label) {
    final button = tester.widget<ButtonStyleButton>(
      find.ancestor(
        of: find.text(label),
        matching: find.byWidgetPredicate((w) => w is ButtonStyleButton),
      ),
    );
    return button.onPressed != null;
  }

  testWidgets('signed in: both buttons enabled, no request lines', (
    tester,
  ) async {
    await pump(tester);
    expect(enabled(tester, 'Refresh now'), isTrue);
    expect(enabled(tester, 'Declare rest day'), isTrue);
    expect(find.textContaining('waiting'), findsNothing);
  });

  testWidgets('signed out: both buttons disabled', (tester) async {
    await pump(tester, signedIn: false);
    expect(enabled(tester, 'Refresh now'), isFalse);
    expect(enabled(tester, 'Declare rest day'), isFalse);
  });

  testWidgets('pending requests disable their own button only', (tester) async {
    await pump(tester, requests: [request()]);
    expect(enabled(tester, 'Refresh now'), isFalse);
    expect(enabled(tester, 'Declare rest day'), isTrue);
    expect(find.text('Refresh: waiting for the PC…'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await pump(
      tester,
      requests: [request(kind: RequestKind.restDay, date: '2026-10-10')],
    );
    expect(enabled(tester, 'Refresh now'), isTrue);
    expect(enabled(tester, 'Declare rest day'), isFalse);
    expect(find.text('Rest day 2026-10-10: waiting for the PC…'), findsOne);
  });

  testWidgets('timed out request says no answer yet and re-enables', (
    tester,
  ) async {
    await pump(
      tester,
      requests: [
        request(timedOut: true),
        request(kind: RequestKind.restDay, date: '2026-10-10', timedOut: true),
      ],
    );
    expect(
      find.text(
        'Refresh: no answer yet (PC may be off); it will show here when it '
        'does',
      ),
      findsOneWidget,
    );
    expect(
      find.text(
        'Rest day 2026-10-10: no answer yet (PC may be off); it will show '
        'here when it does',
      ),
      findsOneWidget,
    );
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(enabled(tester, 'Refresh now'), isTrue);
    expect(enabled(tester, 'Declare rest day'), isTrue);
  });

  testWidgets('a late answer replaces the "no answer yet" line', (
    tester,
  ) async {
    final late = request(timedOut: true)
        .settle(result: const RequestResult(ok: true, message: 'republished'));
    await pump(tester, requests: [late]);
    expect(find.text('Refresh: republished'), findsOneWidget);
    expect(find.textContaining('no answer yet'), findsNothing);
  });

  testWidgets('ok result shows the message, or "done" when empty', (
    tester,
  ) async {
    await pump(
      tester,
      requests: [
        request(result: const RequestResult(ok: true, message: 'published')),
      ],
    );
    expect(find.text('Refresh: published'), findsOneWidget);
    await pump(
      tester,
      requests: [request(result: const RequestResult(ok: true, message: ''))],
    );
    expect(find.text('Refresh: done'), findsOneWidget);
  });

  testWidgets('refused result strips "refused: " and falls back', (
    tester,
  ) async {
    await pump(
      tester,
      requests: [
        request(
          kind: RequestKind.restDay,
          date: '2026-10-12',
          result: const RequestResult(
            ok: false,
            message: 'Refused: too many rest days',
          ),
        ),
      ],
    );
    expect(
      find.text('Rest day 2026-10-12 refused: too many rest days'),
      findsOneWidget,
    );
    await pump(
      tester,
      requests: [
        request(result: const RequestResult(ok: false, message: 'refused:')),
      ],
    );
    expect(find.text('Refresh refused: no reason'), findsOneWidget);
  });

  testWidgets('shows the action error', (tester) async {
    await pump(tester, actionError: 'Sign in first (Settings).');
    expect(find.text('Sign in first (Settings).'), findsOneWidget);
  });

  testWidgets('Refresh now calls requestRefresh', (tester) async {
    final controller = await pump(tester);
    await tester.tap(find.text('Refresh now'));
    await tester.pump();
    expect(controller.refreshRequests, 1);
  });

  testWidgets('picking a rest day calls declareRestDay', (tester) async {
    final controller = await pump(tester);
    await tester.tap(find.text('Declare rest day'));
    await tester.pumpAndSettle();
    expect(find.text('Rest day (future dates only)'), findsOneWidget);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    final now = DateTime.now();
    expect(controller.restDays, [DateTime(now.year, now.month, now.day + 1)]);
  });

  testWidgets('cancelling the picker declares nothing', (tester) async {
    final controller = await pump(tester);
    await tester.tap(find.text('Declare rest day'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(controller.restDays, isEmpty);
  });
}
