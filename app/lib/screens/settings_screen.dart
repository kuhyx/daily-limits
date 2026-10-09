/// Settings: Firebase sign-in (the shared sync_settings_ui screen), the
/// home-screen widget, and a notification check.
library;

import 'package:crdt_sync_flutter/crdt_sync_flutter.dart';
import 'package:daily_limits/services/home_widget_sync.dart';
import 'package:daily_limits/services/notifier.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';
import 'package:sync_settings_ui/sync_settings_ui.dart';

/// The settings list.
class SettingsScreen extends StatelessWidget {
  /// Creates the screen.
  const new({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: [
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Sync settings'),
            subtitle: const Text('Firebase sign-in'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push<void>(
              MaterialPageRoute(builder: (_) => const _SyncScreen()),
            ),
          ),
          const ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('Add widget to home screen'),
            subtitle: Text('One line: shutdown, gaming left, extenders'),
            trailing: Icon(Icons.chevron_right),
            onTap: requestPinWidget,
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Send a test notification'),
            subtitle: const Text('Asks for the permission first if needed'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () async {
              await initNotifications();
              await requestNotificationPermission();
              await showTestNotification();
            },
          ),
        ],
      ),
    );
  }
}

/// The shared Sync settings screen, wired through [kSignIn].
///
/// The sync account is Google-only. One-tap works only for an APK signed with
/// the shared release key, whose SHA-1 is registered as this package's
/// Android OAuth client (`scripts/register_oauth_client.sh`); a debug build
/// gets the account picker and then a "canceled" error.
class _SyncScreen extends StatelessWidget {
  const new();

  @override
  Widget build(BuildContext context) => SyncSettingsScreen(
    accountLoader: loadAccount,
    accountSaver: saveAccount,
    accountClearer: clearAccount,
    sessionProbe: kSignIn.probeSession,
    firebaseFactory: kSignIn.openClient,
    googleFirebaseFactory: kSignIn.googleSignIn,
    googleAvailable: kSignIn.googleAvailable,
    googleUnavailableReason: kSignIn.googleUnavailableReason,
  );
}
