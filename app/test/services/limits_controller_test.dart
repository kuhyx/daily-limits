import 'dart:convert';

import 'package:crdt_sync/crdt_sync.dart';
import 'package:daily_limits/services/limits_controller.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

/// Waits (in real time) until [done] holds, failing after two seconds.
Future<void> until(bool Function() done) async {
  final deadline = DateTime.now().add(const Duration(seconds: 2));
  while (!done()) {
    if (DateTime.now().isAfter(deadline)) fail('condition never held');
    await Future<void>.delayed(const Duration(milliseconds: 5));
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late FakeStore store;
  late RemoteStore? current;
  late int opens;
  late LimitsController controller;

  setUp(() {
    installPlatformFakes(tempDir());
    store = FakeStore({kStatusPath: statusJson(published: DateTime.now())});
    current = store;
    opens = 0;
    controller = LimitsController(
      open: () async {
        opens++;
        return current;
      },
      device: () async => 'phone-1',
      pollEvery: const Duration(milliseconds: 10),
      statusEvery: const Duration(milliseconds: 30),
    );
    // Dispose stops the timers, but a pass already running finishes on its
    // own; let it, before the plugin fakes are removed under it.
    addTearDown(() async {
      controller.dispose();
      await until(() => !controller.loading);
    });
  });

  test('starts empty, then holds the first pass', () async {
    expect(controller.outcome, isNull);
    expect(controller.status, isNull);
    expect(controller.latest(RequestKind.refresh), isNull);
    var notified = 0;
    controller
      ..addListener(() => notified++)
      ..start();
    expect(controller.loading, isTrue);
    await until(() => controller.outcome != null && !controller.loading);
    expect(controller.status!.applied, '22:00');
    expect(notified, greaterThanOrEqualTo(2));
  });

  test('re-reads the status on the timer', () async {
    controller.start();
    await until(() => opens >= 3);
  });

  test('a refresh during a pass makes it go round once more', () async {
    final first = controller.refresh();
    final second = controller.refresh();
    await Future.wait([first, second]);
    expect(opens, 2);
  });

  test('a request needs a signed-in device', () async {
    current = null;
    await controller.declareRestDay(DateTime(2026, 10, 10));
    expect(controller.actionError, 'Sign in first (Settings).');
  });

  test('a failed write is reported', () async {
    store.failWrites = true;
    await controller.requestRefresh();
    expect(controller.actionError, startsWith('Could not send the request'));
    expect(controller.latest(RequestKind.refresh), isNull);
  });

  test('a sent request waits, then shows the PC answer', () async {
    await controller.declareRestDay(DateTime(2026, 10, 10));
    expect(controller.actionError, isNull);
    final sent = controller.latest(RequestKind.restDay)!;
    expect(sent.date, '2026-10-10');
    expect(sent.isPending, isTrue);
    final body =
        jsonDecode(store.files[requestPath(sent.id)]!) as Map<String, dynamic>;
    expect(body['device_id'], 'phone-1');

    // A few polls find nothing; then the PC answers.
    final before = opens;
    await until(() => opens >= before + 2);
    store.files[resultPath(sent.id)] = jsonEncode({
      'ok': true,
      'message': 'declared',
    });
    await until(
      () => controller.latest(RequestKind.restDay)?.isPending == false,
    );
    expect(controller.latest(RequestKind.restDay)!.result!.message, 'declared');
  });

  test('polling stops while the device is signed out', () async {
    await controller.requestRefresh();
    current = null;
    final before = opens;
    await until(() => opens > before);
    await Future<void>.delayed(const Duration(milliseconds: 40));
    expect(opens, before + 1);
  });
}
