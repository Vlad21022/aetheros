import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart' ;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'controls.dart';
import 'format.dart';
import 'hub_connection.dart';
import 'protocol.dart';
import 'surfaces.dart';

/// Someone at the screen: the clock, the weather and the widgets on a 12-column
/// grid. The "Aproape" artboard. Places without data (energy, the Now bar) are
/// left out and their neighbour takes the whole row.
class NearView extends ConsumerWidget {
  const NearView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshot = ref.watch(snapshotProvider);
    final data = snapshot.valueOrNull;
    final event = data?.nextEvent;
    final playing = data?.nowPlaying;

    return Padding(
      padding: const EdgeInsets.all(AetherSpace.space12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _GridRow(
            height: 152,
            wide: const _ClockHeader(),
            narrow: data?.weather == null ? null : _WeatherHeader(weather: data!.weather!),
          ),
          if (data == null)
            Expanded(
              child: Center(
                child: HubMessage(snapshot.hasError ? hubAwayText : connectingText),
              ),
            )
          else ...[
            if (event != null) ...[
              const SizedBox(height: AetherSpace.space4),
              Expanded(child: _GridRow(wide: _EventCard(event: event))),
            ],
            const SizedBox(height: AetherSpace.space4),
            Expanded(
              child: _GridRow(
                wide: _HomeCard(home: data.home),
                narrow: playing == null ? null : _MusicCard(playing: playing),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Columns 1–8 and 9–12 of the 12-column grid, or all 12 when [narrow] is absent.
class _GridRow extends StatelessWidget {
  const _GridRow({required this.wide, this.narrow, this.height});

  static const columns = 12;
  static const gutter = AetherSpace.space4;

  final Widget wide;
  final Widget? narrow;
  final double? height;

  @override
  Widget build(BuildContext context) {
    final row = LayoutBuilder(
      builder: (context, constraints) {
        final column = (constraints.maxWidth - gutter * (columns - 1)) / columns;
        double span(int n) => column * n + gutter * (n - 1);
        return Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(width: narrow == null ? constraints.maxWidth : span(8), child: wide),
            if (narrow != null) ...[
              const SizedBox(width: gutter),
              SizedBox(width: span(4), child: narrow),
            ],
          ],
        );
      },
    );
    return height == null ? row : SizedBox(height: height, child: row);
  }
}

class _ClockHeader extends ConsumerWidget {
  const _ClockHeader();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final now = ref.watch(clockProvider).valueOrNull ?? DateTime.now();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(romanianDate(now), style: text.titleLarge!.copyWith(color: colors.labelSecondary)),
        const SizedBox(height: AetherSpace.space2),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(hourMinute(now), style: text.displayMedium),
        ),
      ],
    );
  }
}

class _WeatherHeader extends StatelessWidget {
  const _WeatherHeader({required this.weather});

  final Weather weather;

  @override
  Widget build(BuildContext context) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Icon(Icons.cloud_outlined, size: 40, color: colors.labelSecondary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.end,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${weather.temperatureC.round()}° · ${weather.condition}',
                  style: text.titleLarge,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (weather.summary != null)
                  Text(
                    weather.summary!,
                    style: text.bodyLarge!.copyWith(color: colors.labelSecondary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
        ],
      ),
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

    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CardHeader('Calendar', trailing: countdown == null ? null : Text(countdown, style: text.labelSmall)),
          const SizedBox(height: 12),
          Text(event.title, style: text.headlineLarge, maxLines: 1, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 6),
          Text(
            '${hourMinute(event.start)}${event.end == null ? '' : ' – ${hourMinute(event.end!)}'}'
            '${event.note == null ? '' : ' · ${event.note}'}',
            style: text.bodyLarge!.copyWith(color: colors.labelSecondary),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

class _HomeCard extends StatelessWidget {
  const _HomeCard({required this.home});

  final Home home;

  @override
  Widget build(BuildContext context) {
    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CardHeader('Acasă', trailing: _HomeSummary(summary: home.summary)),
          const SizedBox(height: 12),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final (i, tile) in home.tiles.take(4).indexed) ...[
                  if (i > 0) const SizedBox(width: AetherSpace.space4),
                  Expanded(child: _TileView(tile: tile)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The right side of the "Acasă" header: the home's summary, or why the last control failed.
class _HomeSummary extends ConsumerWidget {
  const _HomeSummary({required this.summary});

  final String summary;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final style = Theme.of(context).textTheme.labelSmall!;
    final notice = ref.watch(controlsProvider.select((controls) => controls.notice));
    return Semantics(
      liveRegion: notice != null,
      child: Text(
        notice ?? summary,
        style: notice == null ? style : style.copyWith(color: context.aether.coral),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}

class _TileView extends ConsumerWidget {
  const _TileView({required this.tile});

  final Tile tile;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final tap = tile.tap;
    final waiting = ref.watch(controlsProvider.select((controls) => controls.pending.contains(tile.entityId)));
    final (icon, fill) = switch (tile.kind) {
      'light' => (Icons.lightbulb_outline_rounded, tile.active ? colors.candle : colors.fillControl),
      'lock' => (Icons.lock_outline_rounded, tile.active ? colors.sage : colors.coral),
      'climate' => (Icons.thermostat_rounded, colors.fillControl),
      'computer' => (Icons.desktop_windows_outlined, tile.active ? colors.sage : colors.fillControl),
      _ => (Icons.circle_outlined, tile.active ? colors.sage : colors.fillControl),
    };
    // On a coloured disc the icon is ground in Dark and white in Light (the candle token's rule).
    final onFill = Theme.of(context).brightness == Brightness.dark ? colors.ground : colors.surfaceRaised;
    final iconColor = fill == colors.fillControl ? colors.label : onFill;

    final radius = BorderRadius.circular(AetherRadius.radiusSm);
    final card = DecoratedBox(
      decoration: BoxDecoration(color: colors.label.withValues(alpha: 0.06), borderRadius: radius),
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
                Text(
                  waiting ? 'Se trimite…' : tile.state,
                  style: text.bodyMedium,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ],
        ),
      ),
    );
    if (tap == null) return card;

    // The hub said this tile is a button, and which action it sends.
    return Semantics(
      button: true,
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          borderRadius: radius,
          onTap: waiting ? null : () => ref.read(controlsProvider.notifier).send(tile.entityId, tap),
          child: card,
        ),
      ),
    );
  }
}

class _MusicCard extends ConsumerWidget {
  const _MusicCard({required this.playing});

  final NowPlaying playing;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final entityId = playing.entityId;
    final waiting =
        entityId != null && ref.watch(controlsProvider.select((controls) => controls.pending.contains(entityId)));

    /// Null when the player cannot do [action] or a control is on its way.
    VoidCallback? send(String action) =>
        !playing.can(action) || waiting ? null : () => ref.read(controlsProvider.notifier).send(entityId!, action);

    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CardHeader(
                'Muzică',
                trailing: Text(playing.source, style: text.labelSmall, maxLines: 1, overflow: TextOverflow.ellipsis),
              ),
              const SizedBox(height: 12),
              Text(playing.title, style: text.titleLarge, maxLines: 1, overflow: TextOverflow.ellipsis),
              Text(
                [if (playing.subtitle != null) playing.subtitle!, if (!playing.playing) 'în pauză'].join(' · '),
                style: text.bodyMedium,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
          if (playing.progress != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(AetherRadius.radiusFull),
              child: LinearProgressIndicator(
                value: playing.progress,
                minHeight: 4,
                color: colors.label,
                backgroundColor: colors.label.withValues(alpha: 0.14),
              ),
            ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (playing.can('previous'))
                IconButton(
                  onPressed: send('previous'),
                  color: colors.label,
                  tooltip: 'Piesa anterioară',
                  icon: const Icon(Icons.fast_rewind_rounded),
                )
              else
                const SizedBox(width: 48),
              if (playing.can('toggle'))
                IconButton.filled(
                  onPressed: send('toggle'),
                  style: IconButton.styleFrom(
                    backgroundColor: colors.mist,
                    foregroundColor: colors.onMist,
                    disabledBackgroundColor: colors.mist,
                    disabledForegroundColor: colors.onMist,
                    minimumSize: const Size(56, 56),
                  ),
                  tooltip: playing.playing ? 'Pauză' : 'Redă',
                  icon: Icon(playing.playing ? Icons.pause_rounded : Icons.play_arrow_rounded),
                ),
              if (playing.can('next'))
                IconButton(
                  onPressed: send('next'),
                  color: colors.label,
                  tooltip: 'Piesa următoare',
                  icon: const Icon(Icons.fast_forward_rounded),
                )
              else
                const SizedBox(width: 48),
            ],
          ),
        ],
      ),
    );
  }
}
