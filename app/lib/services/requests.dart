/// Requests the phone writes for the PC, and the PC's answers.
///
/// The PC enforces every limit; the phone only asks. The PC deletes each
/// request once it has written the result and prunes old results, so the phone
/// never deletes anything -- it just keeps reading the result of every
/// unanswered request until one arrives or the cache prunes the request.
library;

import 'dart:convert';

import 'package:crdt_sync/crdt_sync.dart';
import 'package:daily_limits/services/sync_app.dart';
import 'package:uuid/uuid.dart';

/// How long the phone shows a request as waiting before saying the PC has not
/// answered yet. Display-only: an answer arriving later still replaces it.
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
    this.sentAt,
  });

  /// Reads one entry of the cache's `requests` list.
  factory fromJson(Map<String, dynamic> json) {
    final result = json['result'];
    final createdAt = DateTime.fromMillisecondsSinceEpoch(
      ((json['created_at'] as num) * 1000).round(),
    );
    // Old cache files have no 'sent_at' key: treat them as sent at creation.
    final sentAt = json.containsKey('sent_at')
        ? json['sent_at'] == null
              ? null
              : DateTime.fromMillisecondsSinceEpoch(
                  ((json['sent_at'] as num) * 1000).round(),
                )
        : createdAt;
    return SentRequest(
      id: json['id'] as String,
      kind: RequestKind.fromWire(json['kind'] as String?),
      date: json['date'] as String?,
      createdAt: createdAt,
      result: result is Map<String, dynamic>
          ? RequestResult.fromJson(result)
          : null,
      timedOut: json['timed_out'] == true,
      sentAt: sentAt,
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

  /// Whether [kAnswerTimeout] passed with no answer. The phone still collects
  /// a late answer; this only changes the line and re-enables the button.
  final bool timedOut;

  /// When the request was uploaded to Firebase; null = still queued locally.
  final DateTime? sentAt;

  /// Queued locally, not yet in Firebase.
  bool get isQueued => sentAt == null;

  /// Still waiting for the PC, within [kAnswerTimeout].
  bool get isPending => result == null && !timedOut;

  /// Whether the PC's answer has been read.
  bool get isAnswered => result != null;

  /// A copy with the answer or the timeout recorded.
  SentRequest settle({RequestResult? result, bool timedOut = false}) =>
      SentRequest(
        id: id,
        kind: kind,
        date: date,
        createdAt: createdAt,
        result: result,
        timedOut: timedOut,
        sentAt: sentAt,
      );

  /// A copy marked as uploaded to Firebase at [at].
  SentRequest markSent(DateTime at) => SentRequest(
    id: id,
    kind: kind,
    date: date,
    createdAt: createdAt,
    result: result,
    timedOut: timedOut,
    sentAt: at,
  );

  /// The cache form.
  Map<String, dynamic> toJson() => {
    'id': id,
    'kind': kind.wire,
    'date': date,
    'created_at': createdAt.millisecondsSinceEpoch / 1000,
    'result': result?.toJson(),
    'timed_out': timedOut,
    'sent_at': sentAt == null ? null : sentAt!.millisecondsSinceEpoch / 1000,
  };
}

/// Creates a new queued request (not yet uploaded to Firebase).
SentRequest newRequest({required RequestKind kind, String? date}) {
  final now = DateTime.now();
  return SentRequest(
    id: const Uuid().v4(),
    kind: kind,
    date: date,
    createdAt: now,
  );
}

/// Uploads [request] to Firebase under its id and returns it marked as sent.
Future<SentRequest> uploadRequest(
  RemoteStore client,
  SentRequest request, {
  required String deviceId,
}) async {
  final body = jsonEncode({
    'id': request.id,
    'kind': request.kind.wire,
    'date': request.date,
    'created_at': request.createdAt.millisecondsSinceEpoch ~/ 1000,
    'device_id': deviceId,
  });
  await client.putFileText(
    requestPath(request.id),
    body,
    message: 'daily_limits: ${request.kind.wire} request',
  );
  return request.markSent(DateTime.now());
}

/// Reads the PC's answer to [id], or null while there is none yet.
Future<RequestResult?> readResult(RemoteStore client, String id) async {
  final text = await client.getFileText(resultPath(id));
  if (text == null) return null;
  return RequestResult.fromJson(jsonDecode(text) as Map<String, dynamic>);
}
