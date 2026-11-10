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
      appBar: AppBar(
        title: const Icon(Icons.settings, semanticLabel: 'Settings'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: [
          ListTile(
            key: const Key('settings-sync'),
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.sync, semanticLabel: 'Sync settings'),
            onTap: () => Navigator.of(context).push<void>(
              MaterialPageRoute(builder: (_) => const _SyncScreen()),
            ),
          ),
          const ListTile(
            key: Key('settings-widget'),
            contentPadding: EdgeInsets.zero,
            leading: Icon(
              Icons.widgets,
              semanticLabel: 'Add widget to home screen',
            ),
            onTap: requestPinWidget,
          ),
          ListTile(
            key: const Key('settings-test-notify'),
            contentPadding: EdgeInsets.zero,
            leading: const Icon(
              Icons.notifications_active,
              semanticLabel: 'Send a test notification',
            ),
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
