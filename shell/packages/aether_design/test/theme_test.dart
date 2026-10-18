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

  test('one family on every platform', () {
    expect(AetherTheme.fontFamilyFor(TargetPlatform.macOS), 'Hanken Grotesk');
    expect(AetherTheme.fontFamilyFor(TargetPlatform.android), 'Hanken Grotesk');
    final linux = AetherTheme.light(platform: TargetPlatform.linux);
    expect(linux.textTheme.bodyLarge!.fontFamily, 'Hanken Grotesk');
  });

  test('clock styles follow the design system', () {
    expect(AetherText.clockFar.fontSize, 260);
    expect(AetherText.clockNear.fontSize, 120);
    expect(AetherText.clockNear.fontWeight, FontWeight.w200);
  });
}
