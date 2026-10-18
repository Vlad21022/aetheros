import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'format.dart';
import 'hub_connection.dart';
import 'surfaces.dart';

/// Nobody near the screen: the clock, one line, the orb. The "Departe" artboard.
class FarView extends ConsumerWidget {
  const FarView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final now = ref.watch(clockProvider).valueOrNull ?? DateTime.now();
    final snapshot = ref.watch(snapshotProvider);
    final glanceStyle = text.headlineMedium!;
    final line = snapshot.when(
      data: (data) => data.glance == null ? null : Text(data.glance!, style: glanceStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
      loading: () => HubMessage(connectingText, style: glanceStyle.copyWith(color: colors.labelSecondary)),
      error: (_, __) => HubMessage(hubAwayText, style: glanceStyle.copyWith(color: colors.labelSecondary)),
    );

    return Padding(
      padding: const EdgeInsets.all(AetherSpace.space20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(romanianDate(now), style: text.titleLarge!.copyWith(color: colors.labelSecondary)),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(hourMinute(now), style: text.displayLarge),
          ),
          const SizedBox(height: AetherSpace.space6),
          Row(
            children: [
              Expanded(child: line ?? const SizedBox.shrink()),
              const SizedBox(width: AetherSpace.space6),
              const AgentOrb(size: 56),
            ],
          ),
        ],
      ),
    );
  }
}
