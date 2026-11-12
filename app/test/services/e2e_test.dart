import 'dart:convert';

import 'package:crdt_sync/crdt_sync.dart';
import 'package:crdt_sync_flutter/testing/fake_secure_storage.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:daily_limits/services/sync_once.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

/// The PC's side: an encrypted store on the same raw "RTDB".
Future<EncryptingStore> pc(FakeStore raw) async {
  final state = await openEncryptedStore(
    store: raw,
    oldPrefix: kOldPrefix,
    readPassphrase: () async => 'test-passphrase',
    params: e2eArgon2Params,
  );
  return (state as E2eReady).store;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    installPlatformFakes(tempDir());
    installE2eTestStorage();
  });

  test('the paths are the shared layout of the old prefix', () {
    final layout = E2eLayout.of(kOldPrefix);
    expect(kOldPrefix, 'daily_limits');
    expect(kStatusPath, '${layout.prefix}/status.json');
    expect(requestPath('r'), '${layout.prefix}/requests/r.json');
    expect(resultPath('r'), '${layout.prefix}/results/r.json');
  });

  test('a request reaches Firebase sealed, and the PC can read it', () async {
    final raw = FakeStore();
    final store = await openEncrypted(() async => raw);
    final sent = await sendRequest(
      store!,
      kind: RequestKind.restDay,
      deviceId: 'phone-1',
      date: '2026-10-10',
    );
    final blob = raw.files[requestPath(sent.id)]!;
    for (final clear in ['"kind"', 'rest_day', '2026-10-10', 'phone-1']) {
      expect(blob, isNot(contains(clear)));
    }
    expect(raw.files.keys, everyElement(startsWith('daily_limits-e2e/')));
    final opened = await (await pc(raw)).getFileText(requestPath(sent.id));
    expect(jsonDecode(opened!), containsPair('kind', 'rest_day'));
  });

  test('a sealed status and result are read back in the clear', () async {
    final raw = FakeStore();
    final writer = await pc(raw);
    await writer.putFileText(
      kStatusPath,
      statusJson(published: DateTime.now()),
      message: 'pc',
    );
    await writer.putFileText(
      resultPath('a'),
      jsonEncode({'ok': true, 'message': 'declared'}),
      message: 'pc',
    );
    expect(raw.files[kStatusPath], isNot(contains('published_at')));
    final out = await syncOnce(open: () => openEncrypted(() async => raw));
    expect(out.locked, isFalse);
    expect(out.status!.applied, '22:00');
    final store = await openEncrypted(() async => raw);
    expect((await readResult(store!, 'a'))!.message, 'declared');
  });

  test('no passphrase: locked, nothing read or written, closed', () async {
    installFakeSecureStorage();
    final raw = FakeStore();
    final out = await syncOnce(open: () => openEncrypted(() async => raw));
    expect(out.locked, isTrue);
    expect(out.signedIn, isTrue);
    expect(out.status, isNull);
    expect(raw.files, isEmpty);
    expect(raw.closed, 1);
  });

  test('a wrong passphrase is locked too', () async {
    final raw = FakeStore();
    await pc(raw);
    installE2eTestStorage(passphrase: 'other');
    await expectLater(
      openEncrypted(() async => raw),
      throwsA(isA<SyncLockedException>()),
    );
    expect(raw.closed, 1);
  });

  test('signed out stays signed out, not locked', () async {
    expect(await openEncrypted(() async => null), isNull);
    final out = await syncOnce(open: () => openEncrypted(() async => null));
    expect(out.signedIn, isFalse);
    expect(out.locked, isFalse);
  });

  test('a network failure while opening closes the client', () async {
    final raw = FakeStore()..failingReads.add('daily_limits-e2e/e2e');
    await expectLater(openEncrypted(() async => raw), throwsException);
    expect(raw.closed, 1);
    final out = await syncOnce(open: () => openEncrypted(() async => raw));
    expect(out.locked, isFalse);
    expect(out.cache.lastError, startsWith('Sign-in failed'));
  });
}
