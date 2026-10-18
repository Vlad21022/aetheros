import 'package:flutter/physics.dart';

/// Motion rules from the design system: springs that settle without bouncing.
abstract final class AetherMotion {
  /// Sheets and cards: about 0.45 s response, damping ratio 0.9.
  static const SpringDescription settle = SpringDescription(
    mass: 1,
    stiffness: 195,
    damping: 25,
  );

  /// The agent orb breathing while listening.
  static const Duration orbBreath = Duration(seconds: 4);

  /// Dim after this long without presence, over [dimDuration].
  static const Duration idleBeforeDim = Duration(seconds: 60);
  static const Duration dimDuration = Duration(seconds: 3);

  /// Wake must feel instant.
  static const Duration wake = Duration(milliseconds: 250);

  /// Far and near layouts cross-fade over this long.
  static const Duration distance = Duration(milliseconds: 500);
}
