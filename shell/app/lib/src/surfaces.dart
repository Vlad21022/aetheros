import 'dart:ui' show ImageFilter;

import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart';

/// The screen's background: graphite with a soft sky, built from the tokens only.
/// A sky that follows the hour comes later.
class Sky extends StatelessWidget {
  const Sky({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = context.aether;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color.lerp(colors.ground, colors.mist, 0.08)!,
            Color.lerp(colors.ground, colors.mist, 0.02)!,
            colors.ground,
          ],
          stops: const [0, 0.55, 1],
        ),
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: RadialGradient(
            center: const Alignment(-0.6, -1.2),
            radius: 1.2,
            colors: [colors.mist.withValues(alpha: 0.14), colors.mist.withValues(alpha: 0)],
          ),
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(0.56, 1.24),
              radius: 0.9,
              colors: [colors.ember.withValues(alpha: 0.16), colors.ember.withValues(alpha: 0)],
            ),
          ),
          child: child,
        ),
      ),
    );
  }
}

/// A widget surface: translucent material with a background blur.
class Panel extends StatelessWidget {
  const Panel({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = context.aether;
    final radius = BorderRadius.circular(AetherRadius.radiusLg);
    return ClipRRect(
      borderRadius: radius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 40, sigmaY: 40),
        child: DecoratedBox(
          decoration: BoxDecoration(color: colors.material, borderRadius: radius),
          child: Padding(padding: const EdgeInsets.all(AetherSpace.space6), child: child),
        ),
      ),
    );
  }
}

/// A card's header: a caption on the left, an optional one on the right.
class CardHeader extends StatelessWidget {
  const CardHeader(this.title, {super.key, this.trailing});

  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.labelSmall;
    return Row(
      children: [
        Text(title, style: style),
        const SizedBox(width: AetherSpace.space4),
        if (trailing != null) Expanded(child: Align(alignment: Alignment.centerRight, child: trailing)),
      ],
    );
  }
}

/// Aether's presence: a glowing orb that breathes unless motion is reduced.
class AgentOrb extends StatefulWidget {
  const AgentOrb({super.key, required this.size});

  final double size;

  @override
  State<AgentOrb> createState() => _AgentOrbState();
}

class _AgentOrbState extends State<AgentOrb> with SingleTickerProviderStateMixin {
  late final AnimationController _breath = AnimationController(vsync: this, duration: AetherMotion.orbBreath);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final reduceMotion = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    if (reduceMotion) {
      _breath.stop();
    } else if (!_breath.isAnimating) {
      _breath.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _breath.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = context.aether.ember;
    final highlight = Color.lerp(color, context.aether.label, 0.45)!;
    return AnimatedBuilder(
      animation: _breath,
      builder: (context, _) {
        final t = Curves.easeInOut.transform(_breath.value);
        return Container(
          width: widget.size,
          height: widget.size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              center: const Alignment(-0.25, -0.3),
              colors: [highlight, color, color.withValues(alpha: 0)],
              stops: const [0, 0.46, 0.74],
            ),
            boxShadow: [BoxShadow(color: color.withValues(alpha: 0.30 + 0.20 * t), blurRadius: 24 + 12 * t)],
          ),
        );
      },
    );
  }
}

/// The hub is connecting or away.
class HubMessage extends StatelessWidget {
  const HubMessage(this.message, {super.key, this.style});

  final String message;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) =>
      Text(message, style: style ?? Theme.of(context).textTheme.bodyLarge, maxLines: 1, overflow: TextOverflow.ellipsis);
}

const connectingText = 'Se conectează la hub…';
const hubAwayText = 'Hub-ul nu răspunde. Reîncerc…';
