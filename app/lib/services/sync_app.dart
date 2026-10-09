/// The Firebase project this app reads and writes, and the logical paths.
///
/// Firebase is the only transport: there is no GitHub mirror here. The
/// account email and password live in the OS keystore (crdt_sync_flutter);
/// nothing below is a secret -- the Web API key ships inside every APK and the
/// security rules protect the data.
library;

import 'package:crdt_sync/crdt_sync.dart';
import 'package:crdt_sync_flutter/crdt_sync_flutter.dart';

/// The shared `kuhy-syncs` project. `databaseUrl` must be the regional host.
const SyncApp kSyncApp = SyncApp(
  project: FirebaseProject(
    apiKey: 'AIzaSyCF_sA3xCMehAYXK8eND-rAygb9NXXW_8E',
    databaseUrl:
        'https://kuhy-syncs-default-rtdb.europe-west1.firebasedatabase.app',
  ),
  expectedUid: 'OvA2REQyLIhAHOEjzwS1o877rgG3',
);

/// The PC's published status (logical crdt_sync path).
const String kStatusPath = 'daily_limits/status.json';

/// Where the phone drops a request for the PC.
String requestPath(String id) => 'daily_limits/requests/$id.json';

/// Where the PC answers request [id].
String resultPath(String id) => 'daily_limits/results/$id.json';

/// The project's **Web** OAuth client id: the audience Google mints the ID
/// token for. Android must ask for a token for the *web* client; an Android
/// client id here yields a token Firebase rejects with `audience mismatch`.
///
/// Public, like the API key. The Android OAuth client (package + signing
/// SHA-1, see `scripts/register_oauth_client.sh`) is what lets this APK ask
/// for it at all; it has no id to compile in.
const String kServerClientId =
    '845446124781-prdoherj0v64vc6egvvcp3l0693khaur.apps.googleusercontent.com';

/// No Desktop OAuth client: this app is Android-only.
const String kDesktopClientId = '';

/// How this device signs in to the shared Firebase project.
///
/// The seam for sign-in: the rest of the app only calls [openClient] and
/// [probeSession], so tests can swap the whole thing.
abstract interface class SignInBackend {
  /// A signed-in client, or null when this device has not signed in yet.
  Future<FirebaseRestClient?> openClient();

  /// Whether this device holds a Firebase session.
  Future<bool> probeSession();

  /// Interactive Google sign-in, or null when this backend has none.
  Future<FirebaseRestClient?> Function()? get googleSignIn;

  /// Whether the Google button can work at all.
  bool get googleAvailable;

  /// Why the Google button is disabled, when it is.
  String? get googleUnavailableReason;
}

/// The keystore session, plus Google one-tap through crdt_sync_flutter.
class GoogleSignInBackend implements SignInBackend {
  /// Creates the backend.
  const new();

  @override
  Future<FirebaseRestClient?> openClient() => openSync(kSyncApp);

  @override
  Future<bool> probeSession() => isSyncConfigured(kSyncApp);

  @override
  Future<FirebaseRestClient?> Function()? get googleSignIn => _google;

  static Future<FirebaseRestClient?> _google() => signInWithGoogle(
    kSyncApp,
    tokenFetcher: () => googleAnyIdToken(
      serverClientId: kServerClientId,
      desktopClientId: kDesktopClientId,
    ),
  );

  @override
  bool get googleAvailable => googleAnySignInSupported(
    serverClientId: kServerClientId,
    desktopClientId: kDesktopClientId,
  );

  @override
  String? get googleUnavailableReason => googleAvailable
      ? null
      : 'Google sign-in works on Android only. Use the account password '
            'below.';
}

/// The sign-in backend in use.
const SignInBackend kSignIn = GoogleSignInBackend();

/// Opens a signed-in store, or null when this device has not signed in.
///
/// What the services take instead of calling [openClient] directly, so a test
/// can hand them an in-memory store.
typedef StoreOpener = Future<RemoteStore?> Function();

/// A signed-in client, or null when this device has not signed in yet.
Future<FirebaseRestClient?> openClient() => kSignIn.openClient();

/// This install's persisted uuid (`crdt.nodeId`).
Future<String> deviceId() async => (await loadDeviceIdentity()).deviceId;
