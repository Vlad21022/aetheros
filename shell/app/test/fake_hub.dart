import 'dart:async';
import 'dart:convert';

import 'package:aether_shell/src/hub_connection.dart';
import 'package:aether_shell/src/protocol.dart';

/// A hub the tests script by hand.
class FakeHub implements HubLink {
  final _messages = StreamController<Envelope>.broadcast(sync: true);
  final _pairingCode = StreamController<String?>.broadcast(sync: true);

  /// Every message the screen sent, decoded.
  final sent = <Map<String, Object?>>[];
  bool connected = true;

  @override
  Stream<Envelope> get messages => _messages.stream;

  @override
  Stream<String?> get pairingCode => _pairingCode.stream;

  /// The screen waits to be paired with [code]; null once it is paired.
  void showCode(String? code) => _pairingCode.add(code);

  @override
  bool send(String type, Map<String, Object?> payload, {String? id}) {
    if (!connected) return false;
    sent.add(jsonDecode(Envelope.encode(type, payload, id: id)) as Map<String, Object?>);
    return true;
  }

  Map<String, Object?> get lastPayload => sent.last['payload']! as Map<String, Object?>;

  /// The hub says something, optionally in reply to the last message sent.
  void say(String type, Map<String, Object?> payload, {bool reply = false}) {
    _messages.add(Envelope(
      type: type,
      id: 'h${sent.length}',
      replyTo: reply ? sent.last['id']! as String : null,
      payload: payload,
    ));
  }

  void drop() => _messages.addError(StateError('connection lost'));
}
