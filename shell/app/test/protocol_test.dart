import 'dart:convert';
import 'dart:io';

import 'package:aether_shell/src/protocol.dart';
import 'package:flutter_test/flutter_test.dart';

/// Shared examples from contracts/examples (tests run from shell/app).
String example(String type) => File('../../contracts/examples/$type.json').readAsStringSync();

void main() {
  test('parses the state.snapshot example', () {
    final msg = Envelope.decode(example('state.snapshot'));
    expect(msg.type, 'state.snapshot');
    final snapshot = Snapshot.fromJson(msg.payload);
    expect(snapshot.home.tiles, hasLength(4));
    expect(snapshot.home.tiles.first.kind, 'light');
    expect(snapshot.weather!.temperatureC, 14);
    expect(snapshot.nowPlaying!.playing, isFalse);
  });

  test('state.update with null clears a section', () {
    final snapshot = Snapshot.fromJson(Envelope.decode(example('state.snapshot')).payload);
    final update = Envelope.decode(example('state.update'));
    expect(snapshot.apply(update.payload).nowPlaying, isNull);
  });

  test('encodes a hello the hub accepts', () {
    final frame = jsonDecode(Envelope.encode('hello', {'screenId': 'x'})) as Map<String, Object?>;
    expect(frame['v'], 1);
    expect(frame['type'], 'hello');
    expect(frame['ts'], isA<String>());
  });

  test('rejects another protocol version', () {
    expect(() => Envelope.decode('{"v":2,"type":"x","id":"1","payload":{}}'), throwsFormatException);
  });
}
