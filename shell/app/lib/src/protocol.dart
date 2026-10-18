// Dart side of contracts/aether-protocol.schema.json (protocol v1).
//
// Only the messages the screen needs so far. test/protocol_test.dart parses the
// shared examples in contracts/examples, so a schema change that breaks this file
// fails the tests.

import 'dart:convert';

const int protocolVersion = 1;

class Envelope {
  Envelope({required this.type, required this.id, required this.payload, this.replyTo});

  final String type;
  final String id;
  final String? replyTo;
  final Map<String, Object?> payload;

  factory Envelope.decode(String frame) {
    final json = jsonDecode(frame) as Map<String, Object?>;
    if (json['v'] != protocolVersion) {
      throw FormatException('unsupported protocol version ${json['v']}');
    }
    return Envelope(
      type: json['type']! as String,
      id: json['id']! as String,
      replyTo: json['replyTo'] as String?,
      payload: (json['payload']! as Map).cast<String, Object?>(),
    );
  }

  /// Builds a frame. Pass [id] to match the reply's replyTo later.
  static String encode(String type, Map<String, Object?> payload, {String? id, String? replyTo}) {
    return jsonEncode({
      'v': protocolVersion,
      'type': type,
      'id': id ?? newId(),
      'ts': DateTime.now().toUtc().toIso8601String(),
      if (replyTo != null) 'replyTo': replyTo,
      'payload': payload,
    });
  }

  static int _counter = 0;
  static String newId() => 's${DateTime.now().millisecondsSinceEpoch}-${_counter++}';
}

class Tile {
  Tile.fromJson(Map<String, Object?> json)
      : entityId = json['entityId']! as String,
        kind = json['kind']! as String,
        title = json['title']! as String,
        state = json['state']! as String,
        active = json['active']! as bool,
        tap = json['tap'] as String?;

  final String entityId;
  final String kind;
  final String title;
  final String state;
  final bool active;

  /// The control action a tap sends. Null: the tile is not a button.
  final String? tap;
}

class Home {
  Home.fromJson(Map<String, Object?> json)
      : summary = json['summary']! as String,
        tiles = [
          for (final tile in json['tiles']! as List) Tile.fromJson((tile as Map).cast<String, Object?>()),
        ];

  final String summary;
  final List<Tile> tiles;
}

class Weather {
  Weather.fromJson(Map<String, Object?> json)
      : temperatureC = (json['temperatureC']! as num).toDouble(),
        condition = json['condition']! as String,
        summary = json['summary'] as String?;

  final double temperatureC;
  final String condition;
  final String? summary;
}

class CalendarEvent {
  CalendarEvent.fromJson(Map<String, Object?> json)
      : title = json['title']! as String,
        start = DateTime.parse(json['start']! as String).toLocal(),
        end = json['end'] == null ? null : DateTime.parse(json['end']! as String).toLocal(),
        note = json['note'] as String?;

  final String title;
  final DateTime start;
  final DateTime? end;
  final String? note;
}

class NowPlaying {
  NowPlaying.fromJson(Map<String, Object?> json)
      : source = json['source']! as String,
        title = json['title']! as String,
        subtitle = json['subtitle'] as String?,
        playing = json['playing']! as bool,
        progress = (json['progress'] as num?)?.toDouble(),
        entityId = json['entityId'] as String?,
        controls = [...?(json['controls'] as List?)?.cast<String>()];

  final String source;
  final String title;
  final String? subtitle;
  final bool playing;
  final double? progress;

  /// Where playback controls go. Null: there is nothing to control.
  final String? entityId;

  /// The control actions that work for this player: toggle, next, previous.
  final List<String> controls;

  bool can(String action) => entityId != null && controls.contains(action);
}

/// The payload of action.result.
class ActionResult {
  ActionResult.fromJson(Map<String, Object?> json)
      : ok = json['ok']! as bool,
        message = json['message']! as String;

  final bool ok;
  final String message;
}

/// The payload of error.
class HubError {
  HubError.fromJson(Map<String, Object?> json)
      : code = json['code']! as String,
        message = json['message']! as String;

  final String code;
  final String message;
}

class Snapshot {
  Snapshot({required this.home, this.weather, this.nextEvent, this.nowPlaying});

  factory Snapshot.fromJson(Map<String, Object?> json) => Snapshot(
        home: Home.fromJson((json['home']! as Map).cast<String, Object?>()),
        weather: _opt(json['weather'], Weather.fromJson),
        nextEvent: _opt(json['nextEvent'], CalendarEvent.fromJson),
        nowPlaying: _opt(json['nowPlaying'], NowPlaying.fromJson),
      );

  final Home home;
  final Weather? weather;
  final CalendarEvent? nextEvent;
  final NowPlaying? nowPlaying;

  /// Applies a state.update payload.
  Snapshot apply(Map<String, Object?> update) {
    final value = update['value'];
    return switch (update['section']) {
      'home' => Snapshot(home: Home.fromJson((value! as Map).cast()), weather: weather, nextEvent: nextEvent, nowPlaying: nowPlaying),
      'weather' => Snapshot(home: home, weather: _opt(value, Weather.fromJson), nextEvent: nextEvent, nowPlaying: nowPlaying),
      'nextEvent' => Snapshot(home: home, weather: weather, nextEvent: _opt(value, CalendarEvent.fromJson), nowPlaying: nowPlaying),
      'nowPlaying' => Snapshot(home: home, weather: weather, nextEvent: nextEvent, nowPlaying: _opt(value, NowPlaying.fromJson)),
      _ => this,
    };
  }

  static T? _opt<T>(Object? value, T Function(Map<String, Object?>) parse) =>
      value == null ? null : parse((value as Map).cast<String, Object?>());
}
