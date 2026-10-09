import 'dart:convert';

import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

void main() {
  test('RequestKind.fromWire defaults unknown values to refresh', () {
    expect(RequestKind.fromWire('rest_day'), RequestKind.restDay);
    expect(RequestKind.fromWire('refresh'), RequestKind.refresh);
    expect(RequestKind.fromWire('bogus'), RequestKind.refresh);
    expect(RequestKind.fromWire(null), RequestKind.refresh);
  });

  test('RequestResult round-trips and tolerates missing fields', () {
    const r = RequestResult(ok: true, message: 'done');
    final back = RequestResult.fromJson(r.toJson());
    expect(back.ok, isTrue);
    expect(back.message, 'done');
    final empty = RequestResult.fromJson(const {});
    expect(empty.ok, isFalse);
    expect(empty.message, '');
  });

  group('SentRequest', () {
    final created = DateTime.fromMillisecondsSinceEpoch(1791540000000);

    test('round-trips through the cache form', () {
      final r = SentRequest(
        id: 'a',
        kind: RequestKind.restDay,
        date: '2026-10-10',
        createdAt: created,
        result: const RequestResult(ok: false, message: 'no'),
      );
      final back = SentRequest.fromJson(
        jsonDecode(jsonEncode(r.toJson())) as Map<String, dynamic>,
      );
      expect(back.id, 'a');
      expect(back.kind, RequestKind.restDay);
      expect(back.date, '2026-10-10');
      expect(back.createdAt, created);
      expect(back.result!.message, 'no');
      expect(back.timedOut, isFalse);
      expect(back.isPending, isFalse);
    });

    test('reads a pending entry with no result', () {
      final back = SentRequest.fromJson({
        'id': 'b',
        'kind': 'refresh',
        'created_at': 1,
        'result': null,
        'timed_out': true,
      });
      expect(back.result, isNull);
      expect(back.timedOut, isTrue);
      expect(back.isPending, isFalse);
    });

    test('settle records an answer or a timeout', () {
      final r = SentRequest(
        id: 'c',
        kind: RequestKind.refresh,
        createdAt: created,
      );
      expect(r.isPending, isTrue);
      expect(r.settle(timedOut: true).isPending, isFalse);
      expect(r.settle(timedOut: true).isAnswered, isFalse);
      expect(
        r.settle(result: const RequestResult(ok: true, message: '')).isAnswered,
        isTrue,
      );
      final answered = r.settle(
        result: const RequestResult(ok: true, message: ''),
      );
      expect(answered.result!.ok, isTrue);
      expect(answered.id, 'c');
    });
  });

  test('sendRequest writes the contract under requests/<id>.json', () async {
    final store = FakeStore();
    final sent = await sendRequest(
      store,
      kind: RequestKind.restDay,
      deviceId: 'phone-1',
      date: '2026-10-10',
    );
    final body =
        jsonDecode(store.files[requestPath(sent.id)]!) as Map<String, dynamic>;
    expect(body['id'], sent.id);
    expect(body['kind'], 'rest_day');
    expect(body['date'], '2026-10-10');
    expect(body['device_id'], 'phone-1');
    expect(body['created_at'], isA<int>());
    expect(sent.isPending, isTrue);
  });

  test('readResult is null until the PC answers', () async {
    final store = FakeStore();
    expect(await readResult(store, 'x'), isNull);
    store.files[resultPath('x')] = jsonEncode({'ok': true, 'message': 'ok'});
    final r = await readResult(store, 'x');
    expect(r!.ok, isTrue);
    expect(r.message, 'ok');
  });
}
