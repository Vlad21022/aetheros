# Hub (hub/)

The service screens connect to. It will run the router, the agent and the plugins;
in phase 0 it speaks protocol v1 and serves demo data.

```sh
uv sync
uv run aether-hub        # listens on ws://0.0.0.0:8765/v1
uv run pytest -q
```

- `src/aether_hub/protocol.py` — typed messages, mirror of `contracts/aether-protocol.schema.json`
- `src/aether_hub/server.py` — WebSocket endpoint, handshake and error rules
- `src/aether_hub/state.py` — where the ambient data comes from (`DemoState` until Home Assistant)
- `tests/test_contract.py` — schema, examples and models agree
- `tests/test_server.py` — a real WebSocket conversation, every reply checked against the schema
