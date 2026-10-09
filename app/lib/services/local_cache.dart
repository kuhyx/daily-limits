/// The phone's own memory: the last status it saw, the requests it sent, and
/// which one-shot notifications already fired.
///
/// A JSON file rather than shared_preferences, because both the UI isolate
/// and the workmanager isolate read and write it, and a file is re-read fresh
/// on every [LocalCache.load] (shared_preferences caches per isolate). Writes
/// go through a temp file + rename so a reader never sees half a file.
library;

import 'dart:convert';
import 'dart:io';

import 'package:daily_limits/services/requests.dart';
import 'package:path_provider/path_provider.dart';

/// Requests older than this are dropped from the cache entirely.
const Duration _keepRequestsFor = Duration(days: 2);

/// Everything the phone remembers between runs.
class LocalCache {
  /// Creates a cache snapshot.
  new({
    this.statusText,
    this.fetchedAt,
    this.lastError,
    List<SentRequest>? requests,
    this.gamingNotifiedDay,
  }) : requests = requests ?? <SentRequest>[];

  /// The raw text of the last status read from Firebase.
  String? statusText;

  /// When the phone last read the status successfully.
  DateTime? fetchedAt;

  /// Why the last read failed, or null when it succeeded.
  String? lastError;

  /// Requests this phone sent, newest last.
  List<SentRequest> requests;

  /// Gaming day the "10 min left" notification already fired for.
  String? gamingNotifiedDay;

  static Future<File> _file() async {
    final dir = await getApplicationSupportDirectory();
    return File('${dir.path}/daily_limits_cache.json');
  }

  /// Reads the cache, or an empty one when there is none or it is unreadable.
  static Future<LocalCache> load() async {
    final file = await _file();
    if (!file.existsSync()) return LocalCache();
    try {
      final map = jsonDecode(await file.readAsString()) as Map<String, dynamic>;
      final fetched = map['fetched_at'] as num?;
      return LocalCache(
        statusText: map['status_text'] as String?,
        fetchedAt: fetched == null
            ? null
            : DateTime.fromMillisecondsSinceEpoch(fetched.toInt()),
        lastError: map['last_error'] as String?,
        requests: [
          for (final r in map['requests'] as List? ?? const [])
            SentRequest.fromJson(r as Map<String, dynamic>),
        ],
        gamingNotifiedDay: map['gaming_notified_day'] as String?,
      );
    } on Object {
      // A corrupt cache only loses display history; start clean.
      return LocalCache();
    }
  }

  /// Writes the cache atomically, pruning requests older than two days.
  ///
  /// Requests are merged with what is on disk first. Two writers share this
  /// file -- a UI action and a sync pass in either isolate -- and each works
  /// on the snapshot it loaded, so a plain overwrite by a pass that started
  /// earlier would drop a request the other one just added.
  Future<void> save() async {
    final file = await _file();
    final onDisk = file.existsSync()
        ? (await load()).requests
        : const <SentRequest>[];
    final cutoff = DateTime.now().subtract(_keepRequestsFor);
    requests = [
      for (final r in mergeRequests(onDisk, requests))
        if (r.createdAt.isAfter(cutoff)) r,
    ];
    final tmp = File('${file.path}.tmp');
    await tmp.writeAsString(
      jsonEncode({
        'status_text': statusText,
        'fetched_at': fetchedAt?.millisecondsSinceEpoch,
        'last_error': lastError,
        'requests': [for (final r in requests) r.toJson()],
        'gaming_notified_day': gamingNotifiedDay,
      }),
      flush: true,
    );
    await tmp.rename(file.path);
  }

  /// The union of [onDisk] and [mine] by id, oldest first.
  ///
  /// The phone never deletes a request (only pruning does), so a union loses
  /// nothing. For an id in both, a settled copy beats a pending one: a
  /// request only ever moves from pending to settled.
  static List<SentRequest> mergeRequests(
    List<SentRequest> onDisk,
    List<SentRequest> mine,
  ) {
    final byId = <String, SentRequest>{for (final r in onDisk) r.id: r};
    for (final r in mine) {
      final other = byId[r.id];
      if (other == null || other.isPending || !r.isPending) byId[r.id] = r;
    }
    return byId.values.toList()
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
  }

  /// Replaces the tracked request with the same id.
  void replaceRequest(SentRequest updated) {
    requests = [
      for (final r in requests)
        if (r.id == updated.id) updated else r,
    ];
  }
}
