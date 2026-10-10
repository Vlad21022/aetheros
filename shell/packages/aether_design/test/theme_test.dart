import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('dark theme carries the tokens', () {
    final theme = AetherTheme.dark(platform: TargetPlatform.linux);
    final colors = theme.extension<AetherColors>()!;
    expect(colors, AetherColors.dark);
    expect(theme.scaffoldBackgroundColor, AetherColors.dark.ground);
    expect(theme.colorScheme.primary, AetherColors.dark.tint);
  });

  test('Apple platforms use the system font, others use Inter', () {
    expect(AetherTheme.fontFamilyFor(TargetPlatform.macOS), isNull);
    expect(AetherTheme.fontFamilyFor(TargetPlatform.android), 'Inter');
    final linux = AetherTheme.light(platform: TargetPlatform.linux);
    expect(linux.textTheme.bodyLarge!.fontFamily, 'Inter');
  });

  test('clock style follows the design system', () {
    expect(AetherText.clock.fontSize, 176);
    expect(AetherText.clock.fontWeight, FontWeight.w200);
  });
}
