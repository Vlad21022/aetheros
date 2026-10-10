import 'dart:ui' show ImageFilter;

import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'format.dart';
import 'hub_connection.dart';
import 'protocol.dart';

/// The screen at rest. Matches the "Ambient · în repaus" artboard in the
/// AetherOS Ambient design canvas.
class AmbientScreen extends ConsumerWidget {
  const AmbientScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = context.aether;
    final snapshot = ref.watch(snapshotProvider);

    return Scaffold(
      body: DecoratedBox(
        decoration: BoxDecoration(
          color: colors.ground,
          gradient: RadialGradient(
            center: const Alignment(-0.75, -0.85),
            radius: 1.3,
            colors: [colors.tint.withValues(alpha: 0.20), colors.tint.withValues(alpha: 0)],
          ),
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(0.85, 1.1),
              radius: 1.1,
              colors: [colors.agent.withValues(alpha: 0.13), colors.agent.withValues(alpha: 0)],
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.all(AetherSpace.space12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(child: _ClockColumn(weather: snapshot.valueOrNull?.weather)),
                const SizedBox(width: AetherSpace.space12),
                SizedBox(
                  width: 640,
                  child: snapshot.when(
                    data: (data) => _Widgets(snapshot: data),
                    loading: () => const _HubMessage('Se conectează la hub…'),
                    error: (_, __) => const _HubMessage('Hub-ul nu răspunde. Reîncerc…'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ClockColumn extends ConsumerWidget {
  const _ClockColumn({required this.weather});

  final Weather? weather;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final now = ref.watch(clockProvider).valueOrNull ?? DateTime.now();
    final time = hourMinute(now);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(romanianDate(now), style: text.titleLarge),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(time, style: text.displayLarge),
            ),
            if (weather != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Row(
                  children: [
                    Icon(Icons.cloud_outlined, size: 24, color: colors.labelSecondary),
                    const SizedBox(width: AetherSpace.space2),
                    Flexible(
                      child: Text(
                        '${weather!.temperatureC.round()}° · ${weather!.condition}'
                        '${weather!.summary == null ? '' : ' · ${weather!.summary}'}',
                        style: text.bodyLarge!.copyWith(color: colors.labelSecondary),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
        Row(
          children: [
            _AgentOrb(color: colors.agent),
            const SizedBox(width: AetherSpace.space4),
            Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Spune „Aether”', style: text.titleMedium),
                  Text('sau atinge ecranul · procesat local', style: text.bodyMedium),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _Widgets extends StatelessWidget {
  const _Widgets({required this.snapshot});

  final Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final event = snapshot.nextEvent;
    final playing = snapshot.nowPlaying;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (event != null) _EventCard(event: event),
        const SizedBox(height: AetherSpace.space4),
        Expanded(
          child: _Material(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Acasă', style: text.titleLarge),
                    Flexible(
                      child: Text(
                        snapshot.home.summary,
                        style: text.bodyMedium,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AetherSpace.space4),
                Expanded(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (final (i, tile) in snapshot.home.tiles.take(4).indexed) ...[
                        if (i > 0) const SizedBox(width: 12),
                        Expanded(child: _TileView(tile: tile)),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        if (playing != null) ...[
          const SizedBox(height: AetherSpace.space4),
          _Material(
            child: Row(
              children: [
                DecoratedBox(
                  decoration: BoxDecoration(
                    color: colors.fillControl,
                    borderRadius: BorderRadius.circular(AetherRadius.radiusSm),
                  ),
                  child: SizedBox.square(
                    dimension: 72,
                    child: Icon(Icons.music_note_outlined, size: 28, color: colors.labelSecondary),
                  ),
                ),
                const SizedBox(width: AetherSpace.space4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(playing.title, style: text.titleMedium),
                      Text(
                        '${playing.subtitle ?? ''} · ${playing.source}${playing.playing ? '' : ' · în pauză'}',
                        style: text.bodyMedium,
                      ),
                      if (playing.progress != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 10),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(AetherRadius.radiusFull),
                            child: LinearProgressIndicator(
                              value: playing.progress,
                              minHeight: 4,
                              color: colors.label,
                              backgroundColor: colors.label.withValues(alpha: 0.14),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(width: AetherSpace.space4),
                IconButton(
                  onPressed: () {},
                  iconSize: 28,
                  color: colors.label,
                  tooltip: 'Piesa anterioară',
                  icon: const Icon(Icons.fast_rewind_rounded),
                ),
                IconButton.filled(
                  onPressed: () {},
                  iconSize: 28,
                  style: IconButton.styleFrom(
                    backgroundColor: colors.label,
                    foregroundColor: colors.ground,
                    minimumSize: const Size(56, 56),
                  ),
                  tooltip: playing.playing ? 'Pauză' : 'Redă',
                  icon: Icon(playing.playing ? Icons.pause_rounded : Icons.play_arrow_rounded),
                ),
                IconButton(
                  onPressed: () {},
                  iconSize: 28,
                  color: colors.label,
                  tooltip: 'Piesa următoare',
                  icon: const Icon(Icons.fast_forward_rounded),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _EventCard extends ConsumerWidget {
  const _EventCard({required this.event});

  final CalendarEvent event;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final now = ref.watch(clockProvider).valueOrNull ?? DateTime.now();
    final countdown = startsIn(now, event.start);

    return _Material(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Calendar', style: text.labelSmall),
              if (countdown != null) Text(countdown, style: text.labelSmall),
            ],
          ),
          const SizedBox(height: AetherSpace.space2),
          Text(event.title, style: text.headlineLarge),
          const SizedBox(height: AetherSpace.space2),
          Text(
            '${hourMinute(event.start)}${event.end == null ? '' : ' – ${hourMinute(event.end!)}'}'
            '${event.note == null ? '' : ' · ${event.note}'}',
            style: text.bodyLarge!.copyWith(color: colors.labelSecondary),
          ),
        ],
      ),
    );
  }
}

class _TileView extends StatelessWidget {
  const _TileView({required this.tile});

  final Tile tile;

  @override
  Widget build(BuildContext context) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final (icon, fill) = switch (tile.kind) {
      'light' => (Icons.lightbulb_outline_rounded, tile.active ? colors.lightOn : colors.fillControl),
      'lock' => (Icons.lock_outline_rounded, tile.active ? colors.onState : colors.alert),
      'climate' => (Icons.thermostat_rounded, colors.fillControl),
      'computer' => (Icons.desktop_windows_outlined, tile.active ? colors.onState : colors.fillControl),
      _ => (Icons.circle_outlined, tile.active ? colors.onState : colors.fillControl),
    };
    // TODO(design): add an on-fill token; dark ink reads on the yellow and green circles.
    final iconColor = fill == colors.fillControl ? colors.label : const Color(0xFF1C1C1E);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.label.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AetherSpace.space4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            CircleAvatar(radius: 22, backgroundColor: fill, child: Icon(icon, size: 22, color: iconColor)),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(tile.title, style: text.titleMedium, maxLines: 1, overflow: TextOverflow.ellipsis),
                Text(tile.state, style: text.bodyMedium, maxLines: 1, overflow: TextOverflow.ellipsis),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// A widget surface: translucent material with a background blur.
class _Material extends StatelessWidget {
  const _Material({required this.child});

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
          decoration: BoxDecoration(
            color: colors.material,
            borderRadius: radius,
            border: Border.all(color: colors.label.withValues(alpha: 0.07)),
          ),
          child: Padding(padding: const EdgeInsets.all(AetherSpace.space6), child: child),
        ),
      ),
    );
  }
}

class _AgentOrb extends StatefulWidget {
  const _AgentOrb({required this.color});

  final Color color;

  @override
  State<_AgentOrb> createState() => _AgentOrbState();
}

class _AgentOrbState extends State<_AgentOrb> with SingleTickerProviderStateMixin {
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
    return AnimatedBuilder(
      animation: _breath,
      builder: (context, _) {
        final t = Curves.easeInOut.transform(_breath.value);
        return Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              center: const Alignment(-0.25, -0.3),
              colors: [Color.lerp(widget.color, Colors.white, 0.45)!, widget.color, widget.color.withValues(alpha: 0)],
              stops: const [0, 0.46, 0.74],
            ),
            boxShadow: [BoxShadow(color: widget.color.withValues(alpha: 0.30 + 0.25 * t), blurRadius: 20 + 12 * t)],
          ),
        );
      },
    );
  }
}

class _HubMessage extends StatelessWidget {
  const _HubMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(child: Text(message, style: Theme.of(context).textTheme.bodyLarge));
  }
}
