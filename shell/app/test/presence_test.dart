import 'package:aether_shell/src/hub_connection.dart';
import 'package:aether_shell/src/presence.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_hub.dart';

void main() {
  late FakeHub hub;
  late ProviderContainer container;

  // In the test body, so the hold timer runs on the test's fake clock.
  void start() {
    hub = FakeHub();
    container = ProviderContainer(overrides: [hubProvider.overrideWithValue(hub)]);
    addTearDown(container.dispose);
    container.listen(presenceProvider, (_, __) {});
  }

  Distance distance() => container.read(presenceProvider);
  List<Object?> presenceSent() => [
        for (final msg in hub.sent)
          if (msg['type'] == 'presence') (msg['payload']! as Map)['present'],
      ];

  testWidgets('far until someone is there', (tester) async {
    start();
    expect(distance(), Distance.far);
    expect(hub.sent, isEmpty);
  });

  testWidgets('activity brings near, and the hub hears it once', (tester) async {
    start();
    container.read(presenceProvider.notifier).activity();
    expect(distance(), Distance.near);
    container.read(presenceProvider.notifier).activity();
    expect(presenceSent(), [true]);
    await tester.pump(Presence.nearHold);
  });

  testWidgets('20 s without activity goes back to far', (tester) async {
    start();
    final presence = container.read(presenceProvider.notifier);
    presence.activity();
    await tester.pump(const Duration(seconds: 15));
    presence.activity();
    await tester.pump(const Duration(seconds: 15));
    expect(distance(), Distance.near, reason: 'the second activity restarted the hold');
    await tester.pump(const Duration(seconds: 5));
    expect(distance(), Distance.far);
    expect(presenceSent(), [true, false]);
  });

  testWidgets('the pointer and the keyboard count as presence', (tester) async {
    hub = FakeHub();
    await tester.pumpWidget(ProviderScope(
      overrides: [hubProvider.overrideWithValue(hub)],
      child: const MaterialApp(home: PresenceDetector(child: SizedBox.expand())),
    ));
    final element = tester.element(find.byType(PresenceDetector));
    Distance now() => ProviderScope.containerOf(element).read(presenceProvider);
    expect(now(), Distance.far);

    final mouse = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await mouse.addPointer(location: const Offset(10, 10));
    await mouse.moveTo(const Offset(200, 200));
    await tester.pump();
    expect(now(), Distance.near);

    await tester.pump(Presence.nearHold);
    expect(now(), Distance.far);

    await tester.sendKeyEvent(LogicalKeyboardKey.space);
    await tester.pump();
    expect(now(), Distance.near);
    await mouse.removePointer();
    await tester.pump(Presence.nearHold);
  });
}
