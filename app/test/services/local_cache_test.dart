import 'dart:io';

import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

SentRequest _req(
  String id,
  DateTime at, {
  bool answered = false,
  bool timedOut = false,
}) => SentRequest(
  id: id,
  kind: RequestKind.refresh,
  createdAt: at,
  result: answered ? const RequestResult(ok: true, message: '') : null,
  timedOut: timedOut,
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory dir;

  setUp(() {
    dir = tempDir();
    installPlatformFakes(dir);
  });

  File cacheFile() => File('${dir.path}/daily_limits_cache.json');

  test('load is empty when there is no file yet', () async {
    final c = await LocalCache.load();
    expect(c.statusText, isNull);
    expect(c.fetchedAt, isNull);
    expect(c.requests, isEmpty);
  });

  test('load starts clean from a corrupt file', () async {
    cacheFile().writeAsStringSync('{not json');
    final c = await LocalCache.load();
    expect(c.requests, isEmpty);
  });

  test('save then load round-trips every field', () async {
    final now = DateTime.now();
    final fetched = DateTime.fromMillisecondsSinceEpoch(
      now.millisecondsSinceEpoch,
    );
    await LocalCache(
      statusText: '{}',
      fetchedAt: fetched,
      lastError: 'boom',
      requests: [_req('a', now)],
      gamingNotifiedDay: '2026-10-09',
    ).save();
    final c = await LocalCache.load();
    expect(c.statusText, '{}');
    expect(c.fetchedAt, fetched);
    expect(c.lastError, 'boom');
    expect(c.requests.single.id, 'a');
    expect(c.gamingNotifiedDay, '2026-10-09');
    expect(File('${cacheFile().path}.tmp').existsSync(), isFalse);
  });

  test('save keeps a request another writer added meanwhile', () async {
    final now = DateTime.now();
    final stale = await LocalCache.load();
    await LocalCache(requests: [_req('theirs', now)]).save();
    stale.requests.add(_req('mine', now.add(const Duration(seconds: 1))));
    await stale.save();
    final c = await LocalCache.load();
    expect(c.requests.map((r) => r.id), ['theirs', 'mine']);
  });

  test('save prunes requests older than two days', () async {
    final now = DateTime.now();
    await LocalCache(
      requests: [
        _req('old', now.subtract(const Duration(days: 3))),
        _req('new', now),
      ],
    ).save();
    expect((await LocalCache.load()).requests.map((r) => r.id), ['new']);
  });

  group('mergeRequests', () {
    final at = DateTime(2026, 10, 9);

    test('a settled copy beats a pending one, whichever side has it', () {
      final pending = _req('x', at);
      final settled = _req('x', at, answered: true);
      expect(
        LocalCache.mergeRequests([settled], [pending]).single.isPending,
        isFalse,
      );
      expect(
        LocalCache.mergeRequests([pending], [settled]).single.isPending,
        isFalse,
      );
      expect(
        LocalCache.mergeRequests([pending], [pending]).single.isPending,
        isTrue,
      );
    });

    test('answered beats timed out beats pending, whichever side', () {
      final pending = _req('x', at);
      final timedOut = _req('x', at, timedOut: true);
      final answered = _req('x', at, answered: true);
      for (final (a, b, winner) in [
        (answered, timedOut, answered),
        (timedOut, answered, answered),
        (timedOut, pending, timedOut),
        (pending, timedOut, timedOut),
        (timedOut, timedOut, timedOut),
      ]) {
        expect(LocalCache.mergeRequests([a], [b]).single, same(winner));
      }
    });

    test('on a tie the in-memory copy wins', () {
      final disk = _req('x', at, timedOut: true);
      final mine = _req('x', at, timedOut: true);
      expect(LocalCache.mergeRequests([disk], [mine]).single, same(mine));
    });

    test('sorts the union oldest first', () {
      final merged = LocalCache.mergeRequests(
        [_req('b', at.add(const Duration(minutes: 1)))],
        [_req('a', at)],
      );
      expect(merged.map((r) => r.id), ['a', 'b']);
    });
  });

  test('replaceRequest swaps only the matching id', () {
    final at = DateTime(2026, 10, 9);
    final c = LocalCache(requests: [_req('a', at), _req('b', at)])
      ..replaceRequest(_req('b', at, answered: true));
    expect(c.requests.first.isPending, isTrue);
    expect(c.requests.last.isPending, isFalse);
  });
}
