import 'package:daily_limits/services/background.dart';
import 'package:daily_limits/services/local_cache.dart';
import 'package:daily_limits/services/sync_once.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:workmanager/workmanager.dart';

/// Records what the app asks of workmanager; everything else is unexpected.
class _FakeWorkmanager implements Workmanager {
  Function? dispatcher;
  final List<(String, String, Duration?, ExistingPeriodicWorkPolicy?)>
  periodic = [];

  @override
  Future<void> initialize(
    Function callbackDispatcher, {
    bool isInDebugMode = false,
  }) async => dispatcher = callbackDispatcher;

  @override
  Future<void> registerPeriodicTask(
    String uniqueName,
    String taskName, {
    Duration? frequency,
    Duration? flexInterval,
    Map<String, dynamic>? inputData,
    Duration? initialDelay,
    Constraints? constraints,
    ExistingPeriodicWorkPolicy? existingWorkPolicy,
    BackoffPolicy? backoffPolicy,
    Duration? backoffPolicyDelay,
    String? tag,
    ForegroundServiceConfig? foregroundServiceConfig,
  }) async =>
      periodic.add((uniqueName, taskName, frequency, existingWorkPolicy));

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      fail('unexpected ${invocation.memberName}');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('registers one 15-minute task that survives relaunches', () async {
    final wm = _FakeWorkmanager();
    await registerRefreshWith(wm);
    expect(wm.dispatcher, same(callbackDispatcher));
    expect(wm.periodic, [
      (
        'daily_limits.refresh',
        'refresh',
        const Duration(minutes: 15),
        ExistingPeriodicWorkPolicy.keep,
      ),
    ]);
  });

  test('the task runs one sync pass and reports success', () async {
    var passes = 0;
    final ok = await backgroundTask(
      'refresh',
      null,
      sync: () async {
        passes++;
        return SyncOutcome(signedIn: false, cache: LocalCache());
      },
    );
    expect(ok, isTrue);
    expect(passes, 1);
  });
}
