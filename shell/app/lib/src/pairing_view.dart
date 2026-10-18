import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart';

/// Shown until the owner pairs this screen on the hub with the code it shows.
class PairingView extends StatelessWidget {
  const PairingView({super.key, required this.code});

  final String code;

  @override
  Widget build(BuildContext context) {
    final colors = context.aether;
    final text = Theme.of(context).textTheme;
    final spaced = '${code.substring(0, 3)} ${code.substring(3)}';

    return Padding(
      padding: const EdgeInsets.all(AetherSpace.space20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Asociază ecranul', style: text.headlineLarge),
          const SizedBox(height: AetherSpace.space2),
          Text(
            'Ecranul nu e încă asociat cu hub-ul. Pe hub, rulează:',
            style: text.bodyLarge!.copyWith(color: colors.labelSecondary),
          ),
          Semantics(
            label: 'Cod de asociere ${code.split('').join(' ')}',
            child: ExcludeSemantics(child: Text(spaced, style: text.displayMedium)),
          ),
          SelectableText('aether-hub pair $code', style: text.titleLarge),
          const SizedBox(height: AetherSpace.space6),
          Text(
            'Codul se schimbă la fiecare 5 minute.',
            style: text.bodyMedium,
          ),
        ],
      ),
    );
  }
}
