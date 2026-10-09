/// The main screen: today's limits from the PC, plus the two requests.
library;

import 'dart:async';

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
        title: const Text('Daily limits'),
        actions: [
          IconButton(
            tooltip: 'Settings',
            icon: const Icon(Icons.settings),
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
        const EmptyState(
          icon: Icons.login,
          title: 'Not signed in',
          message:
              'Open Settings (top right) and sign in to Firebase sync '
              'to read the limits your PC publishes.',
        )
      else if (status == null && outcome.parseError == null)
        const EmptyState(
          icon: Icons.hourglass_empty,
          title: 'Nothing published yet',
          message:
              'The PC has not written daily_limits/status.json. '
              'This screen fills in as soon as it does.',
        ),
      if (status != null) StatusView(status: status, now: now),
      if (error != null) ...[
        const SizedBox(height: AppSpacing.md),
        Text(
          error,
          style: Theme.of(context).textTheme.bodyLarge
              ?.copyWith(color: Theme.of(context).colorScheme.error),
        ),
      ],
      const SizedBox(height: AppSpacing.md),
      ActionsCard(controller: _controller, signedIn: outcome.signedIn),
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
    final parts = [
      if (published != null) 'Published ${hhmm(published)}',
      if (fetched != null) 'read ${hhmm(fetched)}',
    ];
    if (parts.isEmpty) return const SizedBox.shrink();
    return Text(
      parts.join(' · '),
      textAlign: TextAlign.center,
      style: theme.textTheme.bodySmall?.copyWith(
        color: theme.colorScheme.onSurfaceVariant,
      ),
    );
  }
}
