import 'dart:io';

import 'package:aether_shell/src/hub_connection.dart';
import 'package:aether_shell/src/protocol.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_hub.dart';

void main() {
  late FakeHub hub;
  late ProviderContainer container;
  final snapshot = Envelope.decode(File('../../contracts/examples/state.snapshot.json').readAsStringSync());

  setUp(() {
    hub = FakeHub();
    container = ProviderContainer(overrides: [hubProvider.overrideWithValue(hub)]);
    addTearDown(container.dispose);
    container.listen(snapshotProvider, (_, __) {});
  });

  AsyncValue<Snapshot> state() => container.read(snapshotProvider);

  test('the snapshot is kept current with state.update', () async {
    expect(state().isLoading, isTrue);
    hub.say('state.snapshot', snapshot.payload);
    await pumpEventQueue();
    expect(state().value!.nowPlaying, isNotNull);

    hub.say('state.update', {'section': 'nowPlaying', 'value': null});
    await pumpEventQueue();
    expect(state().value!.nowPlaying, isNull);
    expect(state().value!.home.tiles, hasLength(4));
  });

  test('an update before any snapshot is ignored', () async {
    hub.say('state.update', {'section': 'nowPlaying', 'value': null});
    await pumpEventQueue();
    expect(state().isLoading, isTrue);
  });

  test('a lost connection is an error until the next snapshot', () async {
    hub.say('state.snapshot', snapshot.payload);
    await pumpEventQueue();
    hub.drop();
    await pumpEventQueue();
    expect(state().hasError, isTrue);

    hub.say('state.snapshot', snapshot.payload);
    await pumpEventQueue();
    expect(state().hasError, isFalse);
    expect(state().value!.home.summary, 'Totul e în regulă');
  });

  test('replies to controls do not disturb the snapshot', () async {
    hub.say('state.snapshot', snapshot.payload);
    await pumpEventQueue();
    hub.say('action.result', {'ok': true, 'message': 'Gata.'});
    hub.say('error', {'code': 'unavailable', 'message': 'x'});
    await pumpEventQueue();
    expect(state().hasValue && !state().hasError, isTrue);
  });
}
