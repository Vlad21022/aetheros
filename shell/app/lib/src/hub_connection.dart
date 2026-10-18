import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'protocol.dart';

/// The hub's address. Override with --dart-define=AETHER_HUB=ws://hub.local:8765/v1
const String hubUrl = String.fromEnvironment('AETHER_HUB', defaultValue: 'ws://127.0.0.1:8765/v1');

/// What the app needs from the hub: its messages, and a way to send one.
abstract interface class HubLink {
  /// Every message from the hub. A lost connection arrives as an error event.
  Stream<Envelope> get messages;

  /// Sends a message. False when there is no connection right now.
  bool send(String type, Map<String, Object?> payload, {String? id});
}

/// One WebSocket to the hub. Says hello, and reconnects every few seconds if the hub is away.
class HubConnection implements HubLink {
  HubConnection(this.url);

  final String url;
  final _messages = StreamController<Envelope>.broadcast();
  WebSocketChannel? _channel;
  bool _connected = false;
  bool _closed = false;

  @override
  Stream<Envelope> get messages => _messages.stream;

  @override
  bool send(String type, Map<String, Object?> payload, {String? id}) {
    final channel = _channel;
    if (channel == null || !_connected) return false;
    channel.sink.add(Envelope.encode(type, payload, id: id));
    return true;
  }

  Future<void> run() async {
    while (!_closed) {
      try {
        final channel = _channel = WebSocketChannel.connect(Uri.parse(url));
        await channel.ready;
        _connected = true;
        send('hello', {
          'screenId': 'dev-screen',
          'name': 'Dev screen',
          'protocol': protocolVersion,
          'locale': 'ro-RO',
          'capabilities': {'touch': true, 'microphone': false, 'speaker': false, 'presence': false},
          'size': {'width': 1280, 'height': 800},
        });
        await for (final frame in channel.stream) {
          _messages.add(Envelope.decode(frame as String));
        }
        throw StateError('The hub closed the connection.');
      } catch (error, stack) {
        if (!_closed) _messages.addError(error, stack);
      } finally {
        _connected = false;
      }
      if (!_closed) await Future<void>.delayed(const Duration(seconds: 3));
    }
  }

  void close() {
    _closed = true;
    _channel?.sink.close();
    _messages.close();
  }
}

final hubProvider = Provider<HubLink>((ref) {
  final connection = HubConnection(hubUrl);
  ref.onDispose(connection.close);
  connection.run();
  return connection;
});

/// The latest snapshot from the hub, kept current with state.update.
final snapshotProvider = StreamProvider<Snapshot>((ref) {
  final controller = StreamController<Snapshot>();
  Snapshot? current;
  final subscription = ref.watch(hubProvider).messages.listen(
    (msg) {
      if (msg.type == 'state.snapshot') {
        controller.add(current = Snapshot.fromJson(msg.payload));
      } else if (msg.type == 'state.update' && current != null) {
        controller.add(current = current!.apply(msg.payload));
      }
    },
    onError: controller.addError,
  );
  ref.onDispose(() {
    subscription.cancel();
    controller.close();
  });
  return controller.stream;
});

/// Ticks every second for the clock.
final clockProvider = StreamProvider<DateTime>((ref) async* {
  yield DateTime.now();
  yield* Stream.periodic(const Duration(seconds: 1), (_) => DateTime.now());
});
