/// Test doubles shared by the suite: an in-memory [RemoteStore], the status
/// JSON the PC publishes, and channel fakes for every plugin the app calls.
///
/// No mocking library, as in todo and book-guard: each plugin is faked at its
/// method channel, so the real plugin Dart code runs on top.
library;

import 'dart:convert';
import 'dart:io';

import 'package:crdt_sync/crdt_sync.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_test/flutter_test.dart';

/// An in-memory Firebase stand-in, keyed by logical path.
class FakeStore implements RemoteStore {
  /// Creates a store holding [files].
  new([Map<String, String>? files]) : files = {...?files};

  /// What is "in Firebase".
  final Map<String, String> files;

  /// Paths whose reads throw, as a network failure would.
  final Set<String> failingReads = {};

  /// Whether every write throws.
  bool failWrites = false;

  /// How many times [close] was called.
  int closed = 0;

  @override
  Future<String?> getFileText(String path) async {
    if (failingReads.contains(path)) throw const SocketException('offline');
    return files[path];
  }

  @override
  Future<void> putFileText(
    String path,
    String text, {
    required String message,
  }) async {
    if (failWrites) throw const SocketException('offline');
    files[path] = text;
  }

  @override
  Future<void> deleteFile(String path, {String message = ''}) async =>
      files.remove(path);

  @override
  Future<List<String>> listDirectory(String path) async => [
    for (final k in files.keys)
      if (k.startsWith('$path/')) k.substring(path.length + 1),
  ];

  @override
  Future<bool> canAccessRemote() async => true;

  @override
  void close() => closed++;
}

/// The PC's `status.json`, with every field overridable.
String statusJson({
  required DateTime published,
  String? date,
  String? applied = '22:00',
  String? resolved = '20:00',
  String? floor = '18:00',
  String? ceiling = '23:00',
  String? gamingDay,
  int budget = 300,
  int? used = 120,
  int ceilingMinutes = 480,
  List<Map<String, Object?>>? earners,
  List<Map<String, Object?>>? todo,
}) => jsonEncode({
  'date': date ?? _iso(published),
  'published_at': published.millisecondsSinceEpoch / 1000,
  'device_id': 'pc',
  'shutdown': {
    'applied': applied,
    'resolved': resolved,
    'floor': floor,
    'ceiling': ceiling,
  },
  'gaming': {
    'day': gamingDay ?? _iso(published),
    'budget_minutes': budget,
    'used_minutes': used,
    'ceiling_minutes': ceilingMinutes,
  },
  'earners':
      earners ??
      [
        {
          'name': 'workout',
          'label': 'workout',
          'status': 'todo',
          'shutdown_minutes': 120,
          'gaming_minutes': 120,
        },
        {
          'name': 'reading',
          'label': 'reading',
          'status': 'done',
          'shutdown_minutes': 60,
          'gaming_minutes': 60,
        },
      ],
  'todo':
      todo ??
      [
        {
          'name': 'workout',
          'label': 'workout',
          'status': 'todo',
          'shutdown_after': '22:00',
        },
      ],
});

String _iso(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-'
    '${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

/// Every plugin call the app made, by channel short name.
class PluginLog {
  /// `notifications`, `home_widget` calls, in order.
  final List<MethodCall> calls = [];

  /// Calls to [method] on any channel.
  List<MethodCall> named(String method) => [
    for (final c in calls)
      if (c.method == method) c,
  ];

  /// Ids passed to `show`.
  List<int> get shownIds => [
    for (final c in named('show')) (c.arguments as Map)['id'] as int,
  ];

  /// Titles of everything `show`n or `zonedSchedule`d.
  List<String> titles(String method) => [
    for (final c in named(method)) (c.arguments as Map)['title'] as String,
  ];

  /// What the widget was last given for [key].
  Object? widgetData(String key) {
    for (final c in named('saveWidgetData').reversed) {
      final args = c.arguments as Map;
      if (args['id'] == key) return args['data'];
    }
    return null;
  }
}

/// Knobs the platform fakes read at call time.
class PlatformKnobs {
  /// What `canScheduleExactNotifications` answers.
  bool exactAlarms = true;

  /// What `requestNotificationsPermission` answers.
  bool? permission = true;
}

/// Installs the channel fakes for the current test and returns the call log.
///
/// [supportDir] backs `getApplicationSupportDirectory` (the cache file lives
/// there). Removed again on tear down.
PluginLog installPlatformFakes(Directory supportDir, {PlatformKnobs? knobs}) {
  final log = PluginLog();
  final k = knobs ?? PlatformKnobs();
  final messenger =
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
  AndroidFlutterLocalNotificationsPlugin.registerWith();

  final handlers = <String, Future<Object?>? Function(MethodCall)>{
    'plugins.flutter.io/path_provider': (call) async => supportDir.path,
    'home_widget': (call) async {
      log.calls.add(call);
      return true;
    },
    'dexterous.com/flutter/local_notifications': (call) async {
      log.calls.add(call);
      return switch (call.method) {
        'initialize' => true,
        'canScheduleExactNotifications' => k.exactAlarms,
        'requestNotificationsPermission' => k.permission,
        _ => null,
      };
    },
    'plugins.flutter.io/shared_preferences': (call) async =>
        call.method.startsWith('getAll') ? <String, Object>{} : true,
  };
  for (final MapEntry(:key, :value) in handlers.entries) {
    messenger.setMockMethodCallHandler(MethodChannel(key), value);
  }
  addTearDown(() {
    for (final key in handlers.keys) {
      messenger.setMockMethodCallHandler(MethodChannel(key), null);
    }
  });
  return log;
}

/// A fresh temp directory, deleted on tear down.
Directory tempDir() {
  final dir = Directory.systemTemp.createTempSync('daily_limits_test');
  addTearDown(() => dir.deleteSync(recursive: true));
  return dir;
}
