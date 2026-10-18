import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'far_view.dart';
import 'near_view.dart';
import 'presence.dart';
import 'surfaces.dart';

/// The ambient screen: far when nobody is near, near when someone is at the screen.
/// Matches the "Departe" and "Aproape" artboards in the AetherOS Ambient design canvas.
class AmbientScreen extends ConsumerWidget {
  const AmbientScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final distance = ref.watch(presenceProvider);
    final reduceMotion = MediaQuery.maybeDisableAnimationsOf(context) ?? false;

    return Scaffold(
      body: PresenceDetector(
        child: Sky(
          child: AnimatedSwitcher(
            duration: reduceMotion ? Duration.zero : AetherMotion.distance,
            child: KeyedSubtree(
              key: ValueKey(distance),
              child: switch (distance) {
                Distance.far => const FarView(),
                Distance.near => const NearView(),
              },
            ),
          ),
        ),
      ),
    );
  }
}
