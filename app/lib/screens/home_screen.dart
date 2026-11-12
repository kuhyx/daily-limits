/// The main screen: today's limits from the PC, plus the two requests.
library;

import 'dart:async';

import 'package:crdt_sync_flutter/crdt_sync_flutter.dart';
import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/actions_card.dart';
import 'package:daily_limits/screens/settings_screen.dart';
import 'package:daily_limits/screens/status_view.dart';
import 'package:daily_limits/services/limits_controller.dart';
import 'package:daily_limits/services/sync_once.dart';
import 'package:design_system/design_system.dart';
import 'package:flutter/material.dart';

/// The app's home.
class HomeScreen extends StatefulWidget {
  /// Creates the screen. [controller] is for the on-device probe
  /// (`main_probe.dart`); the screen owns and disposes it either way.
  const new({super.key, this.controller});

  /// The controller to drive, or null for a fresh one.
  final LimitsController? controller;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  late final LimitsController _controller =
      widget.controller ?? LimitsController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _controller.start();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(_controller.refresh());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller.dispose();
    super.dispose();
  }

  Future<void> _openSettings() async {
    await Navigator.of(context)
        .push<void>(MaterialPageRoute(builder: (_) => const SettingsScreen()));
    // Back from sign-in: read straight away rather than in a minute.
    await _controller.refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        actions: [
          // The shared crdt-sync passphrase: closed lock while sync is locked.
          ListenableBuilder(
            listenable: _controller,
            builder: (context, _) => E2ePassphraseButton(
              key: const Key('home-e2e'),
              locked: _controller.outcome?.locked ?? false,
              onSaved: () => unawaited(_controller.refresh()),
            ),
          ),
          IconButton(
            key: const Key('home-settings'),
            icon: const Icon(Icons.settings, semanticLabel: 'Settings'),
            onPressed: _openSettings,
          ),
        ],
      ),
      body: ListenableBuilder(
        listenable: _controller,
        builder: (context, _) => RefreshIndicator(
          onRefresh: _controller.refresh,
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.md),
            children: _content(context, _controller.outcome),
          ),
        ),
      ),
    );
  }

  List<Widget> _content(BuildContext context, SyncOutcome? outcome) {
    if (outcome == null) {
      return const [
        Padding(
          padding: EdgeInsets.all(AppSpacing.xl),
          child: Center(child: CircularProgressIndicator()),
        ),
      ];
    }
    final now = DateTime.now();
    final status = outcome.status;
    final error = outcome.parseError ?? outcome.cache.lastError;
    return [
      if (!outcome.signedIn)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 48),
          child: Center(
            child: Icon(
              Icons.cloud_off,
              key: Key('home-signed-out'),
              size: 64,
              color: Colors.grey,
              semanticLabel: 'Not signed in',
            ),
          ),
        )
      else if (status == null && outcome.parseError == null)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 48),
          child: Center(
            child: Icon(
              Icons.hourglass_empty,
              key: Key('home-empty'),
              size: 64,
              color: Colors.grey,
              semanticLabel: 'Nothing published yet',
            ),
          ),
        ),
      if (status != null) StatusView(status: status, now: now),
      if (error != null) ...[
        const SizedBox(height: AppSpacing.md),
        Icon(
          Icons.error_outline,
          key: const Key('home-error'),
          color: Theme.of(context).colorScheme.error,
          semanticLabel: error,
        ),
      ],
      const SizedBox(height: AppSpacing.md),
      ActionsCard(
        controller: _controller,
        signedIn: outcome.signedIn && !outcome.locked,
      ),
      const SizedBox(height: AppSpacing.md),
      _Footer(outcome: outcome, status: status),
    ];
  }
}

class _Footer extends StatelessWidget {
  const new({required this.outcome, required this.status});

  final SyncOutcome outcome;
  final DailyStatus? status;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final fetched = outcome.cache.fetchedAt;
    final published = status?.publishedAt;
    if (published == null && fetched == null) return const SizedBox.shrink();
    final muted = theme.colorScheme.onSurfaceVariant;
    final style = theme.textTheme.bodySmall?.copyWith(color: muted);
    // Upload = when the PC published, download = when this phone read it.
    Widget stamp(IconData icon, DateTime at, String spoken) => MergeSemantics(
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: muted, semanticLabel: spoken),
          const SizedBox(width: AppSpacing.xs),
          ExcludeSemantics(child: Text(hhmm(at), style: style)),
        ],
      ),
    );
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: AppSpacing.md,
      children: [
        if (published != null)
          stamp(Icons.upload, published, 'Published ${hhmm(published)}'),
        if (fetched != null)
          stamp(Icons.download, fetched, 'read ${hhmm(fetched)}'),
      ],
    );
  }
}
