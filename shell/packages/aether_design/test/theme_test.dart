import 'dart:io';

import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('dark theme carries the tokens', () {
    final theme = AetherTheme.dark(platform: TargetPlatform.linux);
    final colors = theme.extension<AetherColors>()!;
    expect(colors, AetherColors.dark);
    expect(theme.scaffoldBackgroundColor, AetherColors.dark.ground);
    expect(theme.colorScheme.primary, AetherColors.dark.mist);
  });

  test('one bundled family on every platform', () {
    const bundled = 'packages/aether_design/Hanken Grotesk';
    expect(AetherTheme.fontFamilyFor(TargetPlatform.macOS), bundled);
    expect(AetherTheme.fontFamilyFor(TargetPlatform.android), bundled);
    final linux = AetherTheme.light(platform: TargetPlatform.linux);
    expect(linux.textTheme.bodyLarge!.fontFamily, bundled);
  });

  test('every weight the tokens use has a bundled file', () {
    final pubspec = File('pubspec.yaml').readAsStringSync();
    final weights = {
      AetherText.clockFar,
      AetherText.clockNear,
      AetherText.largeTitle,
      AetherText.glance,
      AetherText.title,
      AetherText.headline,
      AetherText.body,
      AetherText.footnote,
      AetherText.caption,
    }.map((style) => style.fontWeight!.value);
    for (final weight in weights) {
      expect(pubspec, contains('weight: $weight'), reason: 'no font file for weight $weight');
    }
    for (final asset in RegExp(r'asset: (\S+)').allMatches(pubspec).map((m) => m[1]!)) {
      expect(File(asset).existsSync(), isTrue, reason: '$asset is declared but missing');
    }
    expect(File('fonts/OFL.txt').existsSync(), isTrue);
  });

  test('clock styles follow the design system', () {
    expect(AetherText.clockFar.fontSize, 260);
    expect(AetherText.clockNear.fontSize, 120);
    expect(AetherText.clockNear.fontWeight, FontWeight.w200);
  });
}
