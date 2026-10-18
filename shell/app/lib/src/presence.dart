import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'hub_connection.dart';

/// How far the person is from the screen (docs/decisions.md, 021).
enum Distance { far, near }

/// Far until someone is at the screen; back to far after [nearHold] without them.
///
/// On the Mac the pointer and the keyboard stand in for a presence sensor; a wall
/// tablet will call [activity] from its sensor instead. Each change is reported to
/// the hub as `presence`.
class Presence extends Notifier<Distance> {
  static const nearHold = Duration(seconds: 20);

  Timer? _hold;

  @override
  Distance build() {
    ref.onDispose(() => _hold?.cancel());
    return Distance.far;
  }

  /// Someone is at the screen right now.
  void activity() {
    _hold?.cancel();
    _hold = Timer(nearHold, () => _set(Distance.far));
    _set(Distance.near);
  }

  void _set(Distance distance) {
    if (state == distance) return;
    state = distance;
    ref.read(hubProvider).send('presence', {'present': distance == Distance.near});
  }
}

final presenceProvider = NotifierProvider<Presence, Distance>(Presence.new);

/// Turns pointer and keyboard activity anywhere below it into [Presence.activity].
class PresenceDetector extends ConsumerWidget {
  const PresenceDetector({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    void activity([Object? _]) => ref.read(presenceProvider.notifier).activity();

    return Focus(
      autofocus: true,
      onKeyEvent: (_, event) {
        activity();
        return KeyEventResult.ignored;
      },
      child: Listener(
        behavior: HitTestBehavior.translucent,
        onPointerHover: activity,
        onPointerMove: activity,
        onPointerDown: activity,
        child: child,
      ),
    );
  }
}
