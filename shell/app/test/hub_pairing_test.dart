// The real HubConnection against a scripted hub over real wss, with the test-only
// certificates in test/fixtures.

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:aether_shell/src/hub_connection.dart';
import 'package:aether_shell/src/pinning.dart';
import 'package:aether_shell/src/screen_store.dart';
import 'package:flutter_test/flutter_test.dart';

const hubFingerprint = '8c56aeae7b03e22f7cf13bc2c0a6782edc6561efbf5054ab820c9f69c3090947';
const otherFingerprint = '0b4efeb69acab80e77c6d0bda096e6163f9b5c1e95b2a91c002a47edb9df6e0e';

/// A hub that knows a few tokens and pairs on request.
class ScriptedHub {
  late HttpServer _server;
  final tokens = <String, String>{};
  final received = <Map<String, Object?>>[];
  final _sockets = <WebSocket>[];
  final _arrived = StreamController<Map<String, Object?>>.broadcast();

  String get url => 'wss://127.0.0.1:${_server.port}/v1';

  Future<void> start() async {
    final context = SecurityContext()
      ..useCertificateChain('test/fixtures/hub/hub.crt')
      ..usePrivateKey('test/fixtures/hub/hub.key');
    _server = await HttpServer.bindSecure('127.0.0.1', 0, context);
    _server.listen((request) async {
      final ws = await WebSocketTransformer.upgrade(request);
      _sockets.add(ws);
      ws.listen((frame) => _onFrame(ws, jsonDecode(frame as String) as Map<String, Object?>));
    });
  }

  Future<Map<String, Object?>> next(String type) =>
      _arrived.stream.firstWhere((msg) => msg['type'] == type).timeout(const Duration(seconds: 5));

  void _onFrame(WebSocket ws, Map<String, Object?> msg) {
    received.add(msg);
    final payload = msg['payload']! as Map;
    if (msg['type'] == 'hello') {
      if (tokens[payload['screenId']] == payload['token']) {
        _say(ws, 'welcome', {'hubName': 'Test', 'protocol': 1}, msg);
        _say(ws, 'state.snapshot', {'home': {'summary': 'Totul e în regulă', 'tiles': []}}, null);
      } else {
        _say(ws, 'error', {'code': 'unauthorized', 'message': 'not paired'}, msg);
      }
    }
    _arrived.add(msg);
  }

  /// The owner confirmed the code of the last pair.request.
  void approve() {
    final request = received.lastWhere((m) => m['type'] == 'pair.request');
    final screenId = (request['payload']! as Map)['screenId']! as String;
    tokens[screenId] = 'token-for-$screenId';
    _say(_sockets.last, 'pair.result', {'token': tokens[screenId], 'hubName': 'Test'}, request);
  }

  /// aether-hub forget: the token stops working and the connection closes.
  Future<void> forget(String screenId) async {
    tokens.remove(screenId);
    await _sockets.last.close(4001, 'unpaired');
  }

  void _say(WebSocket ws, String type, Map<String, Object?> payload, Map<String, Object?>? replyTo) {
    ws.add(jsonEncode({
      'v': 1,
      'type': type,
      'id': 'h${received.length}',
      'ts': '2026-10-10T13:25:00Z',
      if (replyTo != null) 'replyTo': replyTo['id'],
      'payload': payload,
    }));
  }

  Future<void> stop() async {
    for (final ws in _sockets) {
      await ws.close();
    }
    await _server.close(force: true);
  }
}

void main() {
  late ScriptedHub hub;
  late MemoryScreenStore store;
  late HubConnection connection;

  setUp(() async {
    hub = ScriptedHub();
    await hub.start();
    store = MemoryScreenStore(const ScreenIdentity(screenId: 'kitchen'));
  });

  tearDown(() async {
    connection.close();
    await hub.stop();
  });

  HubConnection connect({Duration codeLifetime = const Duration(minutes: 5)}) {
    connection = HubConnection(
      hub.url,
      store,
      name: 'Bucătărie',
      retry: const Duration(milliseconds: 50),
      codeLifetime: codeLifetime,
    );
    connection.run();
    return connection;
  }

  test('a new screen shows a code, gets a token, pins the hub, and says hello', () async {
    final codes = <String?>[];
    final c = connect();
    c.pairingCode.listen(codes.add);
    final snapshot = c.messages.firstWhere((m) => m.type == 'state.snapshot');

    final request = await hub.next('pair.request');
    final payload = request['payload']! as Map;
    expect(payload['screenId'], 'kitchen');
    expect(payload['name'], 'Bucătărie');
    expect(payload['code'], matches(RegExp(r'^[0-9]{6}$')));
    expect(codes, [payload['code']]);

    hub.approve();
    final hello = await hub.next('hello');
    expect((hello['payload']! as Map)['token'], 'token-for-kitchen');
    await snapshot.timeout(const Duration(seconds: 5));

    expect(store.identity.token, 'token-for-kitchen');
    expect(store.identity.hubFingerprint, hubFingerprint);
    expect(codes, [payload['code'], null]);
  });

  test('a paired screen goes straight to hello', () async {
    hub.tokens['kitchen'] = 'known';
    store.identity = const ScreenIdentity(screenId: 'kitchen', token: 'known', hubFingerprint: hubFingerprint);
    final c = connect();
    await c.messages.firstWhere((m) => m.type == 'welcome').timeout(const Duration(seconds: 5));
    expect(hub.received.map((m) => m['type']), ['hello']);
  });

  test('a screen pinned to another hub refuses this one', () async {
    store.identity = const ScreenIdentity(screenId: 'kitchen', token: 'known', hubFingerprint: otherFingerprint);
    final c = connect();
    await expectLater(c.messages.first, throwsA(isA<Object>()));
    expect(hub.received, isEmpty);
  });

  test('forgotten by the hub: back to pairing', () async {
    hub.tokens['kitchen'] = 'known';
    store.identity = const ScreenIdentity(screenId: 'kitchen', token: 'known', hubFingerprint: hubFingerprint);
    final c = connect();
    final code = c.pairingCode.firstWhere((code) => code != null);
    await c.messages.firstWhere((m) => m.type == 'welcome').timeout(const Duration(seconds: 5));

    await hub.forget('kitchen');
    await hub.next('pair.request');
    expect(await code.timeout(const Duration(seconds: 5)), isNotNull);
    expect(store.identity.paired, isFalse);
    expect(store.identity.screenId, 'kitchen');
  });

  test('the code is renewed while nobody confirms it', () async {
    connect(codeLifetime: const Duration(milliseconds: 200));
    final first = await hub.next('pair.request');
    final second = await hub.next('pair.request');
    expect((first['payload']! as Map)['code'], isNot((second['payload']! as Map)['code']));
  });

  group('pinning', () {
    test('trusts only the pinned fingerprint, anything while pairing', () {
      expect(trustHub(pinned: 'a', presented: 'a'), isTrue);
      expect(trustHub(pinned: 'a', presented: 'b'), isFalse);
      expect(trustHub(pinned: null, presented: 'b'), isTrue);
    });
  });

  group('store', () {
    test('a fresh identity has a random id and no token', () {
      final a = ScreenIdentity.fresh();
      expect(a.screenId, hasLength(12));
      expect(a.paired, isFalse);
      expect(ScreenIdentity.fresh().screenId, isNot(a.screenId));
    });

    test('the file store keeps the identity between starts', () async {
      final dir = await Directory.systemTemp.createTemp('aether-store-');
      addTearDown(() => dir.delete(recursive: true));
      final first = await FileScreenStore(directory: () async => dir).load();
      expect(first.paired, isFalse);
      await FileScreenStore(directory: () async => dir).save(first.withToken('t', 'fp'));
      final again = await FileScreenStore(directory: () async => dir).load();
      expect((again.screenId, again.token, again.hubFingerprint), (first.screenId, 't', 'fp'));
      expect(again.unpaired().toJson(), {'screenId': first.screenId});
    });

    test('the token stays out of toString', () {
      const identity = ScreenIdentity(screenId: 'kitchen', token: 'secret', hubFingerprint: 'fp');
      expect(identity.toString(), isNot(contains('secret')));
    });
  });
}
