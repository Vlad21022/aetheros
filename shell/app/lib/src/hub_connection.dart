import 'dart:async';
import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'pinning.dart';
import 'protocol.dart';
import 'screen_store.dart';

/// The hub's address. Override with --dart-define=AETHER_HUB=wss://hub.local:8765/v1
const String hubUrl = String.fromEnvironment('AETHER_HUB', defaultValue: 'wss://127.0.0.1:8765/v1');

/// What this screen calls itself when it asks to be paired.
const String screenName = String.fromEnvironment('AETHER_SCREEN_NAME', defaultValue: 'Ecran');

/// What the app needs from the hub: its messages, a way to send one, and the
/// pairing code while the screen is not paired.
abstract interface class HubLink {
  /// Every message from the hub. A lost connection arrives as an error event.
  Stream<Envelope> get messages;

  /// The code to show while waiting for the owner to pair this screen; null once paired.
  Stream<String?> get pairingCode;

  /// Sends a message. False when there is no connection right now.
  bool send(String type, Map<String, Object?> payload, {String? id});
}

/// One wss connection to the hub, pinned to its certificate. Pairs the screen when it
/// has no token, says hello with the token when it has one, and reconnects every few
/// seconds if the hub is away.
class HubConnection implements HubLink {
  HubConnection(
    this.url,
    this.store, {
    this.name = screenName,
    this.retry = const Duration(seconds: 3),
    this.codeLifetime = const Duration(minutes: 5),
    Random? random,
  }) : _random = random ?? Random.secure();

  final String url;
  final ScreenStore store;
  final String name;
  final Duration retry;

  /// A new code is shown after this long; the hub forgets a code after five minutes.
  final Duration codeLifetime;

  final Random _random;
  final _messages = StreamController<Envelope>.broadcast();
  final _pairingCode = StreamController<String?>.broadcast();
  WebSocketChannel? _channel;
  Timer? _codeTimer;
  String? _helloId;
  bool _connected = false;
  bool _closed = false;

  @override
  Stream<Envelope> get messages => _messages.stream;

  @override
  Stream<String?> get pairingCode => _pairingCode.stream;

  @override
  bool send(String type, Map<String, Object?> payload, {String? id}) {
    final channel = _channel;
    if (channel == null || !_connected) return false;
    channel.sink.add(Envelope.encode(type, payload, id: id));
    return true;
  }

  Future<void> run() async {
    while (!_closed) {
      String? presented;
      try {
        var identity = await store.load();
        final channel = _channel = IOWebSocketChannel.connect(
          Uri.parse(url),
          customClient: pinnedHttpClient(
            pinned: identity.paired ? identity.hubFingerprint : null,
            onPresented: (fingerprint) => presented = fingerprint,
          ),
        );
        await channel.ready;
        _connected = true;
        identity.paired ? _sayHello(identity) : _askToPair(identity);

        await for (final frame in channel.stream) {
          final msg = Envelope.decode(frame as String);
          if (msg.type == 'pair.result') {
            identity = identity.withToken(PairResult.fromJson(msg.payload).token, presented);
            await store.save(identity);
            _stopPairing();
            _sayHello(identity);
          } else if (msg.type == 'error' &&
              msg.replyTo != null &&
              msg.replyTo == _helloId &&
              HubError.fromJson(msg.payload).code == 'unauthorized') {
            // The hub no longer knows this screen (aether-hub forget): pair again.
            identity = identity.unpaired();
            await store.save(identity);
            _askToPair(identity);
          } else {
            _messages.add(msg);
          }
        }
        throw StateError('The hub closed the connection.');
      } catch (error, stack) {
        if (!_closed) _messages.addError(error, stack);
      } finally {
        _connected = false;
        _codeTimer?.cancel();
      }
      if (!_closed) await Future<void>.delayed(retry);
    }
  }

  void _sayHello(ScreenIdentity identity) {
    _helloId = Envelope.newId();
    send(
      'hello',
      {
        'screenId': identity.screenId,
        'name': name,
        'protocol': protocolVersion,
        'locale': 'ro-RO',
        'token': identity.token,
        'capabilities': {'touch': true, 'microphone': false, 'speaker': false, 'presence': false},
        'size': {'width': 1280, 'height': 800},
      },
      id: _helloId,
    );
  }

  void _askToPair(ScreenIdentity identity) {
    final code = List.generate(6, (_) => _random.nextInt(10)).join();
    send('pair.request', {'screenId': identity.screenId, 'name': name, 'code': code});
    _pairingCode.add(code);
    _codeTimer?.cancel();
    _codeTimer = Timer(codeLifetime, () => _askToPair(identity));
  }

  void _stopPairing() {
    _codeTimer?.cancel();
    _pairingCode.add(null);
  }

  void close() {
    _closed = true;
    _codeTimer?.cancel();
    _channel?.sink.close();
    _messages.close();
    _pairingCode.close();
  }
}

final hubProvider = Provider<HubLink>((ref) {
  final connection = HubConnection(hubUrl, FileScreenStore());
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

/// The code to show while the screen waits to be paired; null when paired.
final pairingCodeProvider = StreamProvider<String?>((ref) => ref.watch(hubProvider).pairingCode);

/// Ticks every second for the clock.
final clockProvider = StreamProvider<DateTime>((ref) async* {
  yield DateTime.now();
  yield* Stream.periodic(const Duration(seconds: 1), (_) => DateTime.now());
});
