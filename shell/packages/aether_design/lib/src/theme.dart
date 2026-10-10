import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'tokens.g.dart';

/// Builds [ThemeData] from the generated tokens.
abstract final class AetherTheme {
  static ThemeData dark({TargetPlatform? platform}) =>
      _build(AetherColors.dark, Brightness.dark, platform);

  static ThemeData light({TargetPlatform? platform}) =>
      _build(AetherColors.light, Brightness.light, platform);

  /// SF Pro is licensed for Apple platforms only, so Apple devices use the
  /// system font (null here) and every other platform uses Inter.
  static String? fontFamilyFor(TargetPlatform platform) => switch (platform) {
        TargetPlatform.iOS || TargetPlatform.macOS => null,
        _ => AetherFonts.sansFallback.first,
      };

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
        primary: colors.tint,
        onPrimary: colors.onTint,
        secondary: colors.agent,
        onSecondary: colors.onTint,
        error: colors.alert,
        onError: colors.onTint,
        surface: colors.surfaceRaised,
        onSurface: colors.label,
      ),
      textTheme: TextTheme(
        displayLarge: style(AetherText.clock, colors.label),
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
