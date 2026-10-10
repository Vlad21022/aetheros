import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'protocol.dart';

/// The hub's address. Override with --dart-define=AETHER_HUB=ws://hub.local:8765/v1
const String hubUrl = String.fromEnvironment('AETHER_HUB', defaultValue: 'ws://127.0.0.1:8765/v1');

/// The latest snapshot from the hub. Reconnects every few seconds if the hub is away.
final snapshotProvider = StreamProvider<Snapshot>((ref) {
  final controller = StreamController<Snapshot>();
  var closed = false;
  WebSocketChannel? channel;

  Future<void> connect() async {
    Snapshot? current;
    while (!closed) {
      try {
        channel = WebSocketChannel.connect(Uri.parse(hubUrl));
        await channel!.ready;
        channel!.sink.add(Envelope.encode('hello', {
          'screenId': 'dev-screen',
          'name': 'Dev screen',
          'protocol': protocolVersion,
          'locale': 'ro-RO',
          'capabilities': {'touch': true, 'microphone': false, 'speaker': false, 'presence': false},
          'size': {'width': 1280, 'height': 800},
        }));
        await for (final frame in channel!.stream) {
          final msg = Envelope.decode(frame as String);
          if (msg.type == 'state.snapshot') {
            current = Snapshot.fromJson(msg.payload);
            controller.add(current);
          } else if (msg.type == 'state.update' && current != null) {
            current = current.apply(msg.payload);
            controller.add(current);
          }
        }
      } catch (error, stack) {
        if (!closed) controller.addError(error, stack);
      }
      if (!closed) await Future<void>.delayed(const Duration(seconds: 3));
    }
  }

  connect();
  ref.onDispose(() {
    closed = true;
    channel?.sink.close();
    controller.close();
  });
  return controller.stream;
});

/// Ticks every second for the clock.
final clockProvider = StreamProvider<DateTime>((ref) async* {
  yield DateTime.now();
  yield* Stream.periodic(const Duration(seconds: 1), (_) => DateTime.now());
});
