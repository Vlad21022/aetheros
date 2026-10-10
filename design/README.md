# Design tokens (design/)

`tokens.json` is exported from the AetherOS design system on claude.ai. It is the only
source for colours, type, spacing and radii in the app.

After replacing it:

```sh
python3 tools/gen_tokens.py
```

This rewrites `shell/packages/aether_design/lib/src/tokens.g.dart`. CI fails if the
generated file does not match `tokens.json`.
