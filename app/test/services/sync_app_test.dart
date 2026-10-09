import 'package:crdt_sync_flutter/testing/fake_secure_storage.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/fakes.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    installFakeSecureStorage();
    installPlatformFakes(tempDir());
  });

  test('paths follow the Firebase contract', () {
    expect(kStatusPath, 'daily_limits/status.json');
    expect(requestPath('u'), 'daily_limits/requests/u.json');
    expect(resultPath('u'), 'daily_limits/results/u.json');
  });

  test('a device with no stored session is signed out', () async {
    expect(await openClient(), isNull);
    expect(await kSignIn.probeSession(), isFalse);
  });

  test('Google is offered only where it can work', () {
    // The test host is Linux with no Desktop client configured: no button.
    expect(kSignIn.googleAvailable, isFalse);
    expect(kSignIn.googleUnavailableReason, contains('Android only'));
  });

  test('Google sign-in with no token yields no client', () async {
    expect(await kSignIn.googleSignIn!(), isNull);
  });

  test('deviceId is a persisted per-install uuid', () async {
    expect(await deviceId(), hasLength(36));
  });
}
