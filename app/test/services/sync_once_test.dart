import 'dart:convert';

import 'package:crdt_sync/crdt_sync.dart';
import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:daily_limits/services/sync_once.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late PluginLog log;

  setUp(() => log = installPlatformFakes(tempDir()));

  Future<RemoteStore?> Function() opener(RemoteStore? store) =>
      () async => store;

  SentRequest pending(
    String id, {
    RequestKind kind = RequestKind.refresh,
    Duration age = Duration.zero,
  }) => SentRequest(
    id: id,
    kind: kind,
    date: kind == RequestKind.restDay ? '2026-10-10' : null,
    createdAt: DateTime.now().subtract(age),
  );

  test('parseCached: nothing, a status, or an error', () {
    expect(parseCached(null), (null, null));
    final (status, error) = parseCached(statusJson(published: DateTime.now()));
    expect(status!.applied, '22:00');
    expect(error, isNull);
    final (none, why) = parseCached('{');
    expect(none, isNull);
    expect(why, startsWith('Unreadable status from the PC'));
  });

  test('a signed-in pass caches the status and updates everything', () async {
    final store = FakeStore({
      kStatusPath: statusJson(published: DateTime.now(), used: 295),
    });
    final out = await syncOnce(open: opener(store));
    expect(out.signedIn, isTrue);
    expect(out.status!.applied, '22:00');
    expect(out.parseError, isNull);
    expect(out.cache.fetchedAt, isNotNull);
    expect(out.cache.lastError, isNull);
    expect(store.closed, 1);
    expect(log.titles('show'), ['Gaming: 5m left']);
    expect(log.named('updateWidget'), hasLength(1));
    expect((await LocalCache.load()).statusText, isNotNull);
  });

  test('signed out: no client, keeps the cached status', () async {
    await LocalCache(statusText: statusJson(published: DateTime.now())).save();
    final out = await syncOnce(open: opener(null));
    expect(out.signedIn, isFalse);
    expect(out.status, isNotNull);
  });

  test('a failing sign-in is recorded, not thrown', () async {
    final out = await syncOnce(open: () async => throw StateError('nope'));
    expect(out.signedIn, isFalse);
    expect(out.cache.lastError, startsWith('Sign-in failed'));
    expect(out.status, isNull);
  });

  test('a failed read is recorded and the old status kept', () async {
    await LocalCache(statusText: statusJson(published: DateTime.now())).save();
    final store = FakeStore()..failingReads.add(kStatusPath);
    final out = await syncOnce(open: opener(store));
    expect(out.cache.lastError, startsWith('Could not reach Firebase'));
    expect(out.status, isNotNull);
  });

  test('an unreadable status surfaces as parseError', () async {
    final out = await syncOnce(open: opener(FakeStore({kStatusPath: '[]'})));
    expect(out.status, isNull);
    expect(out.parseError, isNotNull);
  });

  group('collectAnswers', () {
    test('settles answered requests and notifies rest days', () async {
      final cache = LocalCache(
        requests: [
          pending('a'),
          pending('b', kind: RequestKind.restDay),
          pending('done').settle(timedOut: true),
        ],
      );
      final store = FakeStore({
        resultPath('a'): jsonEncode({'ok': true, 'message': 'republished'}),
        resultPath('b'): jsonEncode({'ok': false, 'message': 'refused: x'}),
      });
      expect(await collectAnswers(store, cache), isTrue);
      expect(cache.requests.every((r) => !r.isPending), isTrue);
      expect(log.titles('show'), ['Rest day refused: 2026-10-10']);
    });

    test('times out old requests, retries failed and young ones', () async {
      final cache = LocalCache(
        requests: [
          pending('old', age: kAnswerTimeout + const Duration(seconds: 1)),
          pending('young'),
          pending('broken'),
        ],
      );
      final store = FakeStore()..failingReads.add(resultPath('broken'));
      expect(await collectAnswers(store, cache), isTrue);
      expect(cache.requests[0].timedOut, isTrue);
      expect(cache.requests[1].isPending, isTrue);
      expect(cache.requests[2].isPending, isTrue);
    });

    test('collects a late answer to a timed-out request', () async {
      final late = pending(
        'late',
        kind: RequestKind.restDay,
        age: const Duration(minutes: 9),
      ).settle(timedOut: true);
      final cache = LocalCache(requests: [late]);
      final store = FakeStore({
        resultPath('late'): jsonEncode({'ok': true, 'message': 'declared'}),
      });
      expect(await collectAnswers(store, cache), isTrue);
      final settled = cache.requests.single;
      expect(settled.isAnswered, isTrue);
      expect(settled.result!.message, 'declared');
      expect(log.titles('show'), ['Rest day declared: 2026-10-10']);
    });

    test('a timed-out request with no answer stays as it is', () async {
      final cache = LocalCache(
        requests: [
          pending('t', age: const Duration(minutes: 9)).settle(timedOut: true),
        ],
      );
      expect(await collectAnswers(FakeStore(), cache), isFalse);
      expect(cache.requests.single.timedOut, isTrue);
    });

    test('an answered request is not read again', () async {
      final cache = LocalCache(
        requests: [
          pending('a')
              .settle(result: const RequestResult(ok: true, message: '')),
        ],
      );
      final store = FakeStore({
        resultPath('a'): jsonEncode({'ok': false, 'message': 'other'}),
      });
      expect(await collectAnswers(store, cache), isFalse);
      expect(cache.requests.single.result!.ok, isTrue);
    });

    test('reports no change when nothing moved', () async {
      final cache = LocalCache(requests: [pending('young')]);
      expect(await collectAnswers(FakeStore(), cache), isFalse);
    });
  });
}
