import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'tokens.g.dart';

/// Builds [ThemeData] from the generated tokens.
abstract final class AetherTheme {
  static ThemeData dark({TargetPlatform? platform}) =>
      _build(AetherColors.dark, Brightness.dark, platform);

  static ThemeData light({TargetPlatform? platform}) =>
      _build(AetherColors.light, Brightness.light, platform);

  /// One family on every platform: Hanken Grotesk (SIL Open Font License).
  /// TODO: bundle the font files in this package; until then Flutter falls back
  /// to the platform font.
  static String? fontFamilyFor(TargetPlatform platform) => AetherFonts.sansFallback.first;

  static ThemeData _build(
    AetherColors colors,
    Brightness brightness,
    TargetPlatform? platform,
  ) {
    final target = platform ?? defaultTargetPlatform;
    final family = fontFamilyFor(target);

    TextStyle style(TextStyle base, Color color) => base.copyWith(
          fontFamily: family,
          fontFamilyFallback: AetherFonts.sansFallback,
          color: color,
          fontFeatures: const [FontFeature.tabularFigures()],
        );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      platform: target,
      scaffoldBackgroundColor: colors.ground,
      splashFactory: NoSplash.splashFactory,
      colorScheme: ColorScheme(
        brightness: brightness,
        primary: colors.mist,
        onPrimary: colors.onMist,
        secondary: colors.ember,
        onSecondary: colors.onMist,
        error: colors.coral,
        onError: colors.onMist,
        surface: colors.surfaceRaised,
        onSurface: colors.label,
      ),
      textTheme: TextTheme(
        displayLarge: style(AetherText.clockNear, colors.label),
        headlineLarge: style(AetherText.largeTitle, colors.label),
        titleLarge: style(AetherText.title, colors.label),
        titleMedium: style(AetherText.headline, colors.label),
        bodyLarge: style(AetherText.body, colors.label),
        bodyMedium: style(AetherText.footnote, colors.labelSecondary),
        labelSmall: style(AetherText.caption, colors.labelSecondary),
      ),
      extensions: [colors],
    );
  }
}

extension AetherThemeContext on BuildContext {
  /// The AetherOS colour tokens for the current theme.
  AetherColors get aether => Theme.of(this).extension<AetherColors>()!;
}
