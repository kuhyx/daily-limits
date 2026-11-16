/// The main screen: today's limits from the PC, plus the two requests.
library;

import 'dart:async';

import 'package:crdt_sync_flutter/crdt_sync_flutter.dart';
import 'package:daily_limits/model/status.dart';
import 'package:daily_limits/screens/home_sheets.dart';
import 'package:daily_limits/screens/home_tile.dart';
import 'package:daily_limits/screens/settings_screen.dart';
import 'package:daily_limits/screens/status_view.dart';
import 'package:daily_limits/services/limits_controller.dart';
import 'package:daily_limits/services/requests.dart';
import 'package:daily_limits/services/sync_once.dart';
import 'package:design_system/design_system.dart';
import 'package:material_ui/material_ui.dart';

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
        builder: (context, _) => _body(context, _controller.outcome),
      ),
    );
  }

  Widget _body(BuildContext context, SyncOutcome? outcome) {
    if (outcome == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final status = outcome.status;
    final error = outcome.parseError ?? outcome.cache.lastError;
    final offline = status?.isOffline(DateTime.now()) ?? false;
    Widget grid = LayoutBuilder(
      builder: (context, box) => RefreshIndicator(
        onRefresh: _controller.refresh,
        // Zero scroll extent: the pull gesture survives, nothing scrolls.
        // No overscroll indicator: Android's stretch would move the tiles.
        child: ScrollConfiguration(
          behavior: ScrollConfiguration.of(context).copyWith(overscroll: false),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            child: SizedBox(
              height: box.maxHeight,
              child: FitGrid(
                columns: 2,
                itemCount: 4,
                itemBuilder: (context, i) => _tile(context, outcome, i),
              ),
            ),
          ),
        ),
      ),
    );
    if (offline) grid = GreyedOut(child: grid);
    return Column(
      children: [
        if (!outcome.signedIn)
          const Padding(
            padding: EdgeInsets.all(AppSpacing.md),
            child: Icon(
              Icons.cloud_off,
              key: Key('home-signed-out'),
              size: 48,
              color: Colors.grey,
              semanticLabel: 'Not signed in',
            ),
          )
        else if (status == null && outcome.parseError == null)
          const Padding(
            padding: EdgeInsets.all(AppSpacing.md),
            child: Icon(
              Icons.hourglass_empty,
              key: Key('home-empty'),
              size: 48,
              color: Colors.grey,
              semanticLabel: 'Nothing published yet',
            ),
          ),
        if (offline && status != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            child: OfflineBanner(since: status.publishedAt),
          ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.all(AppSpacing.sm),
            child: Icon(
              Icons.error_outline,
              key: const Key('home-error'),
              color: Theme.of(context).colorScheme.error,
              semanticLabel: error,
            ),
          ),
        Expanded(child: grid),
        Padding(
          padding: const EdgeInsets.all(AppSpacing.sm),
          child: _Footer(outcome: outcome, status: status),
        ),
      ],
    );
  }

  Widget _tile(BuildContext context, SyncOutcome outcome, int i) {
    final status = outcome.status;
    void open(HomeSheet s) => unawaited(showHomeSheet(context, _controller, s));
    switch (i) {
      case 0:
        return HomeTile(
          key: const Key('tile-shutdown'),
          icon: Icons.power_settings_new,
          spoken: 'Shutdown',
          value: status == null ? '?' : (status.applied ?? '--:--'),
          onOpen: status == null ? null : () => open(HomeSheet.shutdown),
        );
      case 1:
        final left = status?.leftMinutes;
        return HomeTile(
          key: const Key('tile-gaming'),
          icon: Icons.sports_esports,
          spoken: 'Gaming',
          value: status == null || left == null ? '?' : compactMinutes(left),
          onOpen: status == null ? null : () => open(HomeSheet.gaming),
        );
      case 2:
        final earners = status?.earners ?? const <EarnerState>[];
        final done = earners.where((e) => e.status == 'done').length;
        return HomeTile(
          key: const Key('tile-earners'),
          icon: Icons.emoji_events,
          spoken: 'Earners',
          value: status == null ? '?' : '$done/${earners.length}',
          onOpen: status == null ? null : () => open(HomeSheet.earners),
        );
      default:
        return HomeTile(
          key: const Key('tile-ask'),
          icon: Icons.send,
          spoken: 'Ask the PC',
          badge: _askBadge(context),
          onOpen: () => open(HomeSheet.ask),
        );
    }
  }

  /// A spinner while a request waits, a warning once one got no answer.
  Widget? _askBadge(BuildContext context) {
    final reqs = [
      _controller.latest(RequestKind.refresh),
      _controller.latest(RequestKind.restDay),
    ].whereType<SentRequest>();
    if (reqs.any((r) => r.isPending)) {
      return const SizedBox.square(
        dimension: AppSpacing.lg,
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    }
    if (reqs.any((r) => r.timedOut && r.result == null)) {
      return Icon(
        Icons.schedule,
        color: context.statusColors.warning,
        semanticLabel: 'No answer yet',
      );
    }
    return null;
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
