# AetherOS

A calm, local-first home assistant. A hub in your home runs the agent, the models and
the plugins; screens around the house show what matters and let you talk to it.
Nothing leaves the house to be thought about.

## How it fits together

```
 screens (Flutter)          hub (Python)                     plugins (MCP)
 kitchen tablet  ─┐                                       ┌─ Home Assistant
 office frame    ─┼─ WebSocket ─▶  router ─▶ agent ─────┼─ desktop PC (Windows)
 Mac (dev)       ─┘   protocol v1   tier 0 / 1 / 2        └─ calendar, … (later)
                                      │
                                      └─ tier 2: large model on the PC's GPU
```

| Folder | What | Status |
|---|---|---|
| `contracts/` | The hub ↔ screen protocol: JSON Schema, examples, rules | v1 defined |
| `hub/` | Python service screens connect to | Live state from Home Assistant, tier 0 controls, demo home |
| `shell/app/` | The Flutter screen app | Ambient screen against the hub |
| `shell/packages/aether_design/` | Design tokens and theme for Flutter | Generated from `design/` |
| `design/` | `tokens.json` exported from the AetherOS design system | v3, own identity (graphite, mist, Hanken Grotesk) |
| `tools/` | `gen_tokens.py`: tokens → Dart | |
| `os/` | Buildroot appliance image for the hub | Milestone 1 (boots in QEMU) |
| `docs/decisions.md` | Why things are the way they are | |

## Run it (macOS)

Needs Python 3.12+ with [uv](https://docs.astral.sh/uv/) and Flutter 3.27+.

```sh
# 1. the hub
cd hub && uv sync && uv run aether-hub          # ws://127.0.0.1:8765/v1, demo home

# 2. the screen, in another terminal (first time: see shell/README.md)
cd shell/app && flutter run -d macos
```

To use your own home instead of the demo one, see `hub/README.md`.

Tests: `cd hub && uv run pytest`, `cd shell/app && flutter test`.

## Roadmap

0. **Foundation**: monorepo, CI, protocol v1, design tokens
1. **Hub + tier 0**: Home Assistant connection, direct commands without a model
2. **Ambient screen on the Mac** with real home data ← *here*
3. **Agent (tier 1)**: local model, tool calling over MCP, confirmations, action log
4. **Voice**: wake word, Whisper, Piper
5. **Desktop PC**: MCP plugin with allowlisted actions, Wake-on-LAN, tier 2 model
6. **Tablet screens**: the same Flutter app in kiosk mode on Android
7. **Hub image** (`os/`): A/B partitions, boot to hub, signed updates
8. **External actions**: calendar, Teams, shopping, always confirmed

## Design

- Design system: AetherOS (colours, type, spacing, radii, brand book) on claude.ai
- Screens: the AetherOS Ambient design canvas on claude.ai

Change a colour or size in the design system, export `tokens.json` into `design/`,
then run `python3 tools/gen_tokens.py`.
