# Hub (hub/)

The service screens connect to. It speaks protocol v1, keeps the ambient screen's
data live from Home Assistant, and runs tier 0: a tap on a tile goes straight to a
Home Assistant service, with no model. The agent and the other plugins come later.

```sh
uv sync
uv run aether-hub        # listens on ws://0.0.0.0:8765/v1
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```

Without any settings the hub serves a demo home, which also reacts to taps.

## Connecting Home Assistant

1. `cp .env.example .env` and fill in `AETHER_HA_URL` (e.g. `http://homeassistant.local:8123`)
   and `AETHER_HA_TOKEN` (Home Assistant → your profile → Security → Long-lived access
   tokens). Variables already set in the environment win over `.env`.
2. `cp aether.example.toml aether.toml` and list your entities: the tiles of "Acasă",
   and the entities behind weather, now playing and calendar.
3. `uv run aether-hub`. The log says `connected to Home Assistant, N entities`.

`.env` and `aether.toml` are in `.gitignore`. Never commit a token.

No Home Assistant yet? A throwaway one for development:

```sh
docker run -d --name ha-dev -p 8123:8123 -v "$PWD/ha-dev:/config" \
  ghcr.io/home-assistant/home-assistant:stable
```

Open http://localhost:8123, create a user, add `demo:` to `ha-dev/configuration.yaml`
and restart the container: that gives made-up lights, a lock, weather, a media player
and a calendar. Then follow the three steps above with `AETHER_HA_URL=http://localhost:8123`.

## What a tap can do (tier 0)

| Entity | `control` actions | Home Assistant service |
|---|---|---|
| `light.*`, `switch.*` | `toggle`, `turn_on`, `turn_off` | the same name |
| `media_player.*` | `toggle` | `media_play_pause` |
| `lock.*` | `turn_on` | `lock.lock` |

Only entities from `aether.toml` can be controlled; others get `error unknown_entity`.
Everything else, unlocking included, gets `error not_allowed`. The reply to a control is
`action.result`; the new state reaches every screen as `state.update`. While Home
Assistant is away, tiles show "Indisponibil" and controls get `error unavailable`.

## Files

- `src/aether_hub/protocol.py` — typed messages, mirror of `contracts/aether-protocol.schema.json`
- `src/aether_hub/server.py` — WebSocket endpoint, handshake, broadcast, wiring (`build`)
- `src/aether_hub/config.py` — settings from the environment, `.env` and `aether.toml`
- `src/aether_hub/state.py` — `StateSource` and the demo home
- `src/aether_hub/ha_client.py` — Home Assistant's WebSocket API: auth, states, events, services
- `src/aether_hub/ha_mapping.py` — entity states → tiles and widgets, with the Romanian text
- `src/aether_hub/ha_state.py` — `HomeAssistantState`, the live `StateSource`
- `src/aether_hub/tier0.py` — the tier 0 rules
- `tests/fake_ha.py` — a stand-in Home Assistant the tests talk to over a real WebSocket
- `tests/test_contract.py` — schema, examples and models agree
- `tests/test_server.py` — real WebSocket conversations, every reply checked against the schema
