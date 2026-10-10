import 'dart:io';

import 'package:aether_design/aether_design.dart';
import 'package:aether_shell/src/ambient_screen.dart';
import 'package:aether_shell/src/controls.dart';
import 'package:aether_shell/src/hub_connection.dart';
import 'package:aether_shell/src/protocol.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_hub.dart';

final example = Envelope.decode(File('../../contracts/examples/state.snapshot.json').readAsStringSync()).payload;

/// The example snapshot with some of now playing's fields replaced.
Map<String, Object?> withNowPlaying(Map<String, Object?> changes) => {
      ...example,
      'nowPlaying': {...example['nowPlaying']! as Map, ...changes},
    };

/// Shows the ambient screen against a scripted hub that already sent [snapshot].
Future<FakeHub> pumpScreen(WidgetTester tester, {Map<String, Object?>? snapshot}) async {
  tester.view.physicalSize = const Size(1280, 800);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  final hub = FakeHub();
  await tester.pumpWidget(ProviderScope(
    overrides: [
      hubProvider.overrideWithValue(hub),
      clockProvider.overrideWith((ref) => Stream.value(DateTime(2026, 10, 10, 16, 25))),
    ],
    child: MaterialApp(
      theme: AetherTheme.dark(platform: TargetPlatform.linux),
      home: const MediaQuery(
        data: MediaQueryData(size: Size(1280, 800), disableAnimations: true),
        child: AmbientScreen(),
      ),
    ),
  ));
  hub.say('state.snapshot', snapshot ?? example);
  await tester.pump();
  await tester.pump();
  return hub;
}

void main() {
  testWidgets('ambient screen shows the hub snapshot', (tester) async {
    await pumpScreen(tester);

    expect(find.text('16:25'), findsOneWidget);
    expect(find.text('Sâmbătă, 10 octombrie'), findsOneWidget);
    expect(find.text('Antrenament la sală'), findsOneWidget);
    expect(find.text('Lumini'), findsOneWidget);
    expect(find.text('Totul e în regulă'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('tapping a tile sends its action and waits for the hub', (tester) async {
    final hub = await pumpScreen(tester);

    await tester.tap(find.text('Lumini'));
    await tester.pump();
    expect(hub.sent.single['type'], 'control');
    expect(hub.lastPayload, {'entityId': 'light.group_on', 'action': 'toggle'});
    // Nothing changes until the hub says so.
    expect(find.text('Se trimite…'), findsOneWidget);
    expect(find.text('3 aprinse'), findsNothing);

    await tester.tap(find.text('Lumini'));
    expect(hub.sent, hasLength(1));

    hub.say('action.result', {'ok': true, 'message': 'Comanda a fost trimisă.'}, reply: true);
    await tester.pump();
    expect(find.text('Se trimite…'), findsNothing);
    expect(find.text('3 aprinse'), findsOneWidget);
    expect(find.text('Totul e în regulă'), findsOneWidget);
  });

  testWidgets('the new state comes from the hub', (tester) async {
    final hub = await pumpScreen(tester);
    final home = example['home']! as Map;
    final tiles = [...home['tiles']! as List];
    tiles[0] = {...tiles[0] as Map, 'state': 'Stinse', 'active': false};

    hub.say('state.update', {
      'section': 'home',
      'value': {...home, 'tiles': tiles},
    });
    await tester.pump();
    await tester.pump();
    expect(find.text('Stinse'), findsOneWidget);
  });

  testWidgets('a tile without tap is not a button', (tester) async {
    final hub = await pumpScreen(tester);

    await tester.tap(find.text('Ușa'), warnIfMissed: false);
    await tester.tap(find.text('PC birou'), warnIfMissed: false);
    await tester.pump();
    expect(hub.sent, isEmpty);
    expect(find.ancestor(of: find.text('Ușa'), matching: find.byType(InkWell)), findsNothing);
    expect(find.ancestor(of: find.text('Lumini'), matching: find.byType(InkWell)), findsOneWidget);
  });

  testWidgets('a refused control is said in the home card, then cleared', (tester) async {
    final hub = await pumpScreen(tester);

    await tester.tap(find.text('Lumini'));
    hub.say('error', {'code': 'unavailable', 'message': 'Home Assistant is not reachable.'}, reply: true);
    await tester.pump();
    expect(find.text('Home Assistant nu răspunde.'), findsOneWidget);
    expect(find.text('Totul e în regulă'), findsNothing);
    expect(find.text('3 aprinse'), findsOneWidget);
    final notice = tester.widget<Text>(find.text('Home Assistant nu răspunde.'));
    expect(notice.style!.color, AetherColors.dark.alert);

    await tester.pump(Controls.noticeDuration);
    expect(find.text('Totul e în regulă'), findsOneWidget);
  });

  testWidgets('now playing buttons send their actions', (tester) async {
    final hub = await pumpScreen(tester);

    for (final (tooltip, action) in [('Redă', 'toggle'), ('Piesa următoare', 'next'), ('Piesa anterioară', 'previous')]) {
      await tester.tap(find.byTooltip(tooltip));
      expect(hub.lastPayload, {'entityId': 'media_player.living_room', 'action': action});
      hub.say('action.result', {'ok': true, 'message': 'Comanda a fost trimisă.'}, reply: true);
      await tester.pump();
    }
    expect(hub.sent, hasLength(3));
  });

  testWidgets('now playing shows only the buttons the player supports', (tester) async {
    await pumpScreen(tester, snapshot: withNowPlaying({'controls': ['toggle'], 'playing': true}));

    expect(find.byTooltip('Pauză'), findsOneWidget);
    expect(find.byTooltip('Piesa următoare'), findsNothing);
    expect(find.byTooltip('Piesa anterioară'), findsNothing);
  });

  testWidgets('now playing from a hub that says nothing about controls has no buttons', (tester) async {
    final playing = {...example['nowPlaying']! as Map}
      ..remove('entityId')
      ..remove('controls');
    await pumpScreen(tester, snapshot: {...example, 'nowPlaying': playing});

    expect(find.text('Seară'), findsOneWidget);
    expect(find.byType(IconButton), findsNothing);
  });
}
