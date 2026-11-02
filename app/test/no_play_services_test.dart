import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// The APK must not link Google's proprietary sign-in libraries (googleid /
/// play-services-auth). Android signs in through crdt_sync_flutter's
/// google_account_token plugin (AccountManager). The `google_sign_in` family
/// would bring the Android implementation back, so it must not reappear in
/// the lockfile.
void main() {
  final lock = File('pubspec.lock').readAsStringSync();

  for (final package in [
    'google_sign_in',
    'google_sign_in_android',
    'google_sign_in_ios',
  ]) {
    test('$package is not in the lockfile', () {
      expect(lock, isNot(contains('\n  $package:\n')));
    });
  }

  test('the AccountManager plugin is', () {
    expect(lock, contains('\n  google_account_token:\n'));
  });
}
