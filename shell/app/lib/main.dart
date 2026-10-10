import 'package:aether_design/aether_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'src/ambient_screen.dart';

void main() {
  runApp(const ProviderScope(child: AetherShell()));
}

class AetherShell extends StatelessWidget {
  const AetherShell({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AetherOS',
      debugShowCheckedModeBanner: false,
      theme: AetherTheme.light(),
      darkTheme: AetherTheme.dark(),
      themeMode: ThemeMode.dark,
      home: const AmbientScreen(),
    );
  }
}
