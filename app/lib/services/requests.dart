/// Requests the phone writes for the PC, and the PC's answers.
///
/// The PC enforces every limit; the phone only asks. The PC deletes each
/// request once it has written the result and prunes old results, so the phone
/// never deletes anything -- it just stops polling.
library;

import 'dart:convert';

import 'package:crdt_sync/crdt_sync.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:uuid/uuid.dart';

/// How long the phone waits for an answer before saying the PC did not reply.
const Duration kAnswerTimeout = Duration(minutes: 3);

/// A request kind: `refresh` or `rest_day`.
enum RequestKind {
  /// Ask the PC to republish the status now.
  refresh('refresh'),

  /// Ask the PC to declare a future day a rest day.
  restDay('rest_day');

  new(this.wire);

  /// The value on the wire.
  final String wire;

  /// Parses [wire], defaulting to [refresh] for anything unknown.
  static RequestKind fromWire(String? wire) =>
      wire == restDay.wire ? restDay : refresh;
}

/// The PC's answer to a request.
class RequestResult {
  /// Creates a result.
  const new({required this.ok, required this.message});

  /// Reads a result object (the PC's file, or the cached copy).
  factory fromJson(Map<String, dynamic> map) => RequestResult(
    ok: map['ok'] == true,
    message: map['message'] as String? ?? '',
  );

  /// Whether the PC did what was asked.
  final bool ok;

  /// The PC's explanation (refusal reason or confirmation).
  final String message;

  /// The cache form.
  Map<String, dynamic> toJson() => {'ok': ok, 'message': message};
}

/// A request this phone sent, as tracked in the local cache.
class SentRequest {
  /// Creates a tracked request.
  const new({
    required this.id,
    required this.kind,
    required this.createdAt,
    this.date,
    this.result,
    this.timedOut = false,
  });

  /// Reads one entry of the cache's `requests` list.
  factory fromJson(Map<String, dynamic> json) {
    final result = json['result'];
    return SentRequest(
      id: json['id'] as String,
      kind: RequestKind.fromWire(json['kind'] as String?),
      date: json['date'] as String?,
      createdAt: DateTime.fromMillisecondsSinceEpoch(
        ((json['created_at'] as num) * 1000).round(),
      ),
      result: result is Map<String, dynamic>
          ? RequestResult.fromJson(result)
          : null,
      timedOut: json['timed_out'] == true,
    );
  }

  /// The request uuid (also the file name).
  final String id;

  /// What was asked.
  final RequestKind kind;

  /// The rest day asked for, `YYYY-MM-DD`; null for a refresh.
  final String? date;

  /// When the phone wrote it.
  final DateTime createdAt;

  /// The PC's answer, once read.
  final RequestResult? result;

  /// Whether the phone gave up waiting ([kAnswerTimeout]).
  final bool timedOut;

  /// Still waiting for the PC.
  bool get isPending => result == null && !timedOut;

  /// A copy with the answer or the timeout recorded.
  SentRequest settle({RequestResult? result, bool timedOut = false}) =>
      SentRequest(
        id: id,
        kind: kind,
        date: date,
        createdAt: createdAt,
        result: result,
        timedOut: timedOut,
      );

  /// The cache form.
  Map<String, dynamic> toJson() => {
    'id': id,
    'kind': kind.wire,
    'date': date,
    'created_at': createdAt.millisecondsSinceEpoch / 1000,
    'result': result?.toJson(),
    'timed_out': timedOut,
  };
}

/// Writes a request for the PC from device [deviceId] and returns what was
/// sent.
Future<SentRequest> sendRequest(
  RemoteStore client, {
  required RequestKind kind,
  required String deviceId,
  String? date,
}) async {
  final created = DateTime.now();
  final id = const Uuid().v4();
  final body = jsonEncode({
    'id': id,
    'kind': kind.wire,
    'date': date,
    'created_at': created.millisecondsSinceEpoch ~/ 1000,
    'device_id': deviceId,
  });
  await client.putFileText(
    requestPath(id),
    body,
    message: 'daily_limits: ${kind.wire} request',
  );
  return SentRequest(id: id, kind: kind, date: date, createdAt: created);
}

/// Reads the PC's answer to [id], or null while there is none yet.
Future<RequestResult?> readResult(RemoteStore client, String id) async {
  final text = await client.getFileText(resultPath(id));
  if (text == null) return null;
  return RequestResult.fromJson(jsonDecode(text) as Map<String, dynamic>);
}
