import 'dart:io';

import 'package:aether_design/aether_design.dart';
import 'package:aether_shell/src/ambient_screen.dart';
import 'package:aether_shell/src/hub_connection.dart';
import 'package:aether_shell/src/protocol.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('ambient screen shows the hub snapshot', (tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final frame = File('../../contracts/examples/state.snapshot.json').readAsStringSync();
    final snapshot = Snapshot.fromJson(Envelope.decode(frame).payload);

    await tester.pumpWidget(ProviderScope(
      overrides: [
        snapshotProvider.overrideWith((ref) => Stream.value(snapshot)),
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
    await tester.pump();

    expect(find.text('16:25'), findsOneWidget);
    expect(find.text('Sâmbătă, 10 octombrie'), findsOneWidget);
    expect(find.text('Antrenament la sală'), findsOneWidget);
    expect(find.text('Lumini'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
