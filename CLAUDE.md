# AetherOS — instructions for Claude

AetherOS is a local-first home assistant: a **hub** (Python) runs the agent, the
models and the plugins; **screens** (Flutter) show the home and talk to the hub over
a WebSocket protocol. Read `README.md` for the map, `docs/vision.md` for the product
context (why, scope, hardware, open questions) and `docs/decisions.md` before
changing anything architectural. The owner wants a genuinely engineered product:
design first, typed contracts, tests and CI from day one. No vibe-coding.

## Hard rules

- **Everything stays local.** No cloud model, no cloud speech, no telemetry. External
  services are touched only by an action that needs them, never to think.
- **The protocol is the contract.** `contracts/aether-protocol.schema.json` is the source
  of truth. Any change updates, in the same commit: the schema, `contracts/examples/`,
  `hub/src/aether_hub/protocol.py`, `shell/app/lib/src/protocol.dart`, and the tests.
  Adding optional fields is fine; removing or renaming one means protocol v2.
- **The hub decides, screens display.** A screen never executes an action. It sends
  `control`, `utterance`, `presence` and `confirm.response`.
- **Consequential actions are confirmed.** Shutting down a PC, sending anything to another
  person, spending money: always a `confirm.request` first. Reversible actions (lights,
  timers) run and report. Plugins expose allowlisted actions only, never a free shell.
- **No hand-written design values in the app.** Colours, type, spacing and radii come from
  `aether_design` (`context.aether`, `AetherText`, `AetherSpace`, `AetherRadius`). To change
  one, edit `design/tokens.json` and run `python3 tools/gen_tokens.py`. Never edit
  `tokens.g.dart` by hand.
- **Copy is Romanian, code and docs are English.** UI text: short, plain sentences, sentence
  case, no exclamation marks, no emoji. Buttons name the verb ("Pune PC-ul în sleep", never "OK").

## Intelligence tiers

- Tier 0: fixed rules mapped straight to Home Assistant. No model. Must work when models are down.
- Tier 1: small local model on the hub (3–4B, good tool calling). Most requests end here.
- Tier 2: large local model on the desktop PC's RTX 5070, woken by Wake-on-LAN. Only when
  tier 1 can't handle the request. If the PC doesn't answer, say so; never degrade silently.
- The router decides escalation. Its rules are code with tests.

## Commands

```sh
# hub (Python 3.12+, uv)
cd hub && uv sync
uv run aether-hub                 # ws://127.0.0.1:8765/v1
uv run pytest -q                  # contract + server tests
uv run ruff check . && uv run ruff format --check .

# screen (Flutter 3.27+)
cd shell/app && flutter pub get
flutter run -d macos              # needs the hub running
flutter run -d macos --dart-define=AETHER_HUB=ws://<hub-ip>:8765/v1
flutter analyze && flutter test
cd ../packages/aether_design && flutter test

# design tokens
python3 tools/gen_tokens.py       # after changing design/tokens.json
python3 tools/gen_tokens.py --check

# OS image (Linux host or Docker only; phase 7)
cd os && make build && make smoke
```

## First-time setup of the screen app

The platform folders are not committed yet. Once, in `shell/app`:

1. `flutter create --platforms=macos,linux,android --project-name aether_shell .`
2. Delete `test/widget_test.dart` if `flutter create` added it.
3. macOS blocks network access by default: add
   `<key>com.apple.security.network.client</key><true/>` to both
   `macos/Runner/DebugProfile.entitlements` and `macos/Runner/Release.entitlements`.
4. Commit the generated platform folders.

## Where things are

- `contracts/` protocol v1 (schema, examples, README with the message flow)
- `hub/src/aether_hub/` `protocol.py` (typed messages), `server.py` (WebSocket), `state.py` (demo data until Home Assistant)
- `shell/app/lib/` `main.dart`, `src/protocol.dart`, `src/hub_connection.dart` (Riverpod providers), `src/ambient_screen.dart`
- `shell/packages/aether_design/` theme, motion, generated tokens
- `os/` Buildroot BR2_EXTERNAL tree; see `os/README.md`
- Design references (owner's claude.ai account): design system
  https://claude.ai/artifact/RAREk2tw1REX2ky8PKgBU5 and screens
  https://claude.ai/artifact/3GB5RvUYEjP6Yhunoz5KeZ

## Current phase

Phase 0 is done (this scaffold). Next is phase 1: a Home Assistant source behind
`StateSource` in `hub/src/aether_hub/state.py`, and tier 0 handling of `control`
messages. Keep the demo source for tests and for running without Home Assistant.

## Working style

- State management in Flutter is Riverpod. Keep widgets small; logic in providers.
- Every new message type, router rule and plugin action gets a test.
- Record any architectural decision in `docs/decisions.md` (decision, reason, when to revisit).
