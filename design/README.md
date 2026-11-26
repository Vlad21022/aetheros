# Design (design/)

- `tokens.json`: colours, type, spacing, radii (generated into Dart, see below)
- `system.md`: the rules: layout, components, motion, Aether's states, copy
- `screens/`: the designed screens and the two animated prototypes

## Tokens

`tokens.json` is exported from the AetherOS design system on claude.ai. It is the only
source for colours, type, spacing and radii in the app.

After replacing it:

```sh
python3 tools/gen_tokens.py
```

This rewrites `shell/packages/aether_design/lib/src/tokens.g.dart`. CI fails if the
generated file does not match `tokens.json`.
