// Guard for kuhy's textgate rule: nothing the app paints, posts or puts on
// the home-screen widget may carry a word. Numbers, times, dates, unit
// letters (`1h30`, `45m`) and emoji pass; any run of 2+ Latin letters fails.
// Spoken-only labels (semanticLabel) are not painted, so they are not read.

import 'package:crdt_sync_flutter/testing/fake_secure_storage.dart';
import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/actions_card.dart';
import 'package:daily_limits/screens/home_screen.dart';
import 'package:daily_limits/screens/settings_screen.dart';
import 'package:daily_limits/screens/status_view.dart';
import 'package:daily_limits/services/home_widget_sync.dart';
import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/notifier.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_once.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_controller.dart';
import 'support/fakes.dart';

final _word = RegExp('[A-Za-z]{2,}');

/// The app's proper noun: the OS-level name (channel name) may carry it.
const _appName = 'Daily limits';

/// Every painted string under the current tree.
List<String> _painted(WidgetTester tester) => [
  for (final w in tester.allWidgets)
    if (w is Text)
      w.data ?? w.textSpan?.toPlainText() ?? ''
    else if (w is RichText)
      w.text.toPlainText(),
];

void _expectNoWords(Iterable<String> texts, {Set<String> allowed = const {}}) {
  final worded = [
    for (final t in texts)
      if (!allowed.contains(t) && _word.hasMatch(t)) t,
  ];
  expect(worded, isEmpty, reason: 'visible words: $worded');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final now = DateTime.now();
  late PluginLog log;

  setUp(() {
    installFakeSecureStorage();
    log = installPlatformFakes(tempDir());
  });

  Future<void> pump(WidgetTester tester, Widget home) async {
    tester.view.physicalSize = const Size(800, 3000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(theme: buildDarkTheme(), home: home));
  }

  final unknownEarners = [
    {
      'name': 'anki',
      'label': 'anki',
      'status': 'unknown',
      'shutdown_minutes': 30,
      'gaming_minutes': 30,
    },
  ];
  final unknownTodo = [
    {
      'name': 'anki',
      'label': 'anki',
      'status': 'unknown',
      'shutdown_after': '21:30',
    },
  ];

  final statuses = <String, String>{
    'online': statusJson(published: now),
    'offline': statusJson(published: now.subtract(const Duration(hours: 3))),
    'unknowns': statusJson(
      published: now,
      applied: null,
      resolved: null,
      floor: null,
      ceiling: null,
      used: null,
      gamingDay: '2026-01-01',
      earners: unknownEarners,
      todo: unknownTodo,
    ),
    'no earners': statusJson(published: now, earners: const [], todo: const []),
  };

  for (final MapEntry(:key, :value) in statuses.entries) {
    testWidgets('StatusView $key paints no words', (tester) async {
      final status = DailyStatus.parse(value);
      await pump(
        tester,
        Scaffold(
          body: SingleChildScrollView(
            child: StatusView(status: status, now: now),
          ),
        ),
      );
      _expectNoWords(_painted(tester));
    });
  }

  SentRequest request(
    RequestKind kind, {
    RequestResult? result,
    bool timedOut = false,
  }) => SentRequest(
    id: 'id-${kind.wire}',
    kind: kind,
    date: kind == RequestKind.restDay ? '2026-10-10' : null,
    createdAt: now,
    result: result,
    timedOut: timedOut,
  );

  final requestSets = <String, List<SentRequest>>{
    'pending': [request(RequestKind.refresh), request(RequestKind.restDay)],
    'timed out': [
      request(RequestKind.refresh, timedOut: true),
      request(RequestKind.restDay, timedOut: true),
    ],
    'answered': [
      request(
        RequestKind.refresh,
        result: const RequestResult(ok: true, message: 'refreshed'),
      ),
      request(
        RequestKind.restDay,
        result: const RequestResult(ok: false, message: 'refused: past'),
      ),
    ],
  };

  for (final MapEntry(:key, :value) in requestSets.entries) {
    testWidgets('ActionsCard $key paints no words', (tester) async {
      final controller = FakeController(
        emptyOutcome(requests: value),
        actionError: 'Could not send the request: boom',
      );
      await pump(
        tester,
        Scaffold(body: ActionsCard(controller: controller, signedIn: true)),
      );
      _expectNoWords(_painted(tester));
    });
  }

  final outcomes = <String, SyncOutcome>{
    'signed out': emptyOutcome(signedIn: false),
    'empty': emptyOutcome(),
    'unreadable': emptyOutcome(parseError: 'Unreadable status from the PC'),
    'status and error': SyncOutcome(
      signedIn: true,
      status: DailyStatus.parse(statusJson(published: now)),
      cache: LocalCache(
        lastError: 'Could not reach Firebase: boom',
        fetchedAt: now,
      ),
    ),
  };

  for (final MapEntry(:key, :value) in outcomes.entries) {
    testWidgets('HomeScreen $key paints no words', (tester) async {
      await pump(tester, HomeScreen(controller: FakeController(value)));
      _expectNoWords(_painted(tester));
    });
  }

  testWidgets('SettingsScreen paints no words', (tester) async {
    await pump(tester, const SettingsScreen());
    _expectNoWords(_painted(tester));
  });

  test('home-screen widget line has no words', () {
    _expectNoWords([
      widgetLine(null, now),
      for (final json in statuses.values)
        widgetLine(DailyStatus.parse(json), now),
    ]);
  });

  test('notifications carry no words', () async {
    final soon = hhmm(now.add(const Duration(minutes: 45)));
    await scheduleShutdownWarnings(
      DailyStatus.parse(statusJson(published: now, applied: soon)),
    );
    final cache = LocalCache();
    await maybeNotifyGaming(
      DailyStatus.parse(statusJson(published: now, used: 295)),
      cache,
    );
    for (final ok in [true, false]) {
      await notifyRestDayResult(
        request(
          RequestKind.restDay,
          result: RequestResult(ok: ok, message: 'refused: past'),
        ),
      );
    }
    await showTestNotification();
    expect(log.named('show'), hasLength(4));
    expect(log.named('zonedSchedule'), isNotEmpty);
    for (final method in ['show', 'zonedSchedule']) {
      _expectNoWords([...log.titles(method), ...log.bodies(method)]);
      _expectNoWords(log.channelTexts(method), allowed: {_appName, ''});
    }
  });
}
