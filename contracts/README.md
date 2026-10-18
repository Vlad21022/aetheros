# Hub ↔ screen protocol (v1)

The contract between the hub (`hub/`) and every screen (`shell/`). The schema in
`aether-protocol.schema.json` is the source of truth; both sides are tested against
the files in `examples/`.

## Transport

- WebSocket, `ws://<hub>:8765/v1`, local network only.
- One JSON message per text frame, UTF-8.
- Every message has the same envelope:

```json
{ "v": 1, "type": "agent.status", "id": "h4", "ts": "2026-10-10T13:25:00Z",
  "replyTo": "s2", "payload": { "state": "thinking", "tier": 1 } }
```

`id` is unique per sender. `replyTo` names the message this one answers.

## Messages

| Direction | type | When |
|---|---|---|
| screen → hub | `hello` | First frame after connecting: who the screen is and what it can do |
| hub → screen | `welcome` | Reply to `hello` |
| hub → screen | `state.snapshot` | Everything the ambient screen shows; after `welcome` and on reconnect |
| hub → screen | `state.update` | One section changed (`home`, `weather`, `nextEvent`, `nowPlaying`, `glance`) |
| screen → hub | `control` | A tap on a home tile or a now playing button. Tier 0: no model involved. Answered with `action.result`, or `error` (`unknown_entity`, `not_allowed`, `unavailable`) |
| screen → hub | `utterance` | Something the user said or typed |
| hub → screen | `agent.status` | Drives the orb: idle, listening, thinking, speaking, acting |
| hub → screen | `agent.reply` | Aether's reply, streamed; the last frame has `final: true` |
| hub → screen | `confirm.request` | A consequential action waits for the user |
| screen → hub | `confirm.response` | The option the user picked |
| hub → screen | `action.result` | What happened |
| screen → hub | `presence` | Someone arrived at or left the screen |
| hub → screen | `screen.command` | Dim, wake, brightness, theme |
| both | `error` | The message in `replyTo` could not be handled |

## A typical exchange

```
screen  hello            ─────▶
        ◀───── welcome
        ◀───── state.snapshot
screen  utterance "Stinge tot, mă duc la culcare."  ─────▶
        ◀───── agent.status thinking (tier 1)
        ◀───── confirm.request "Opresc și PC-ul din birou?"
screen  confirm.response sleep ─────▶
        ◀───── action.result "PC-ul din birou e în sleep."
        ◀───── agent.reply "Gata. Noapte bună." (final)
        ◀───── agent.status idle
```

## What can be tapped

The hub says so; a screen holds no rules of its own.

- A tile with `tap` sends `control` with that action and the tile's `entityId`. A tile
  without `tap` is not a button.
- `nowPlaying.controls` lists the buttons that work (`toggle`, `next`, `previous`); they
  send `control` to `nowPlaying.entityId`.
- The reply is `action.result` or `error`, with `replyTo`. The new state arrives as
  `state.update`; a screen does not change a tile on its own.

## Rules

- The hub decides. A screen never runs an action itself; it only sends `control`,
  `utterance` and `confirm.response`.
- Anything consequential goes through `confirm.request`. The hub executes only after
  a matching `confirm.response` arrives before `expiresAt`.
- Unknown `type` → reply `error` with `bad_message`; never drop the connection.
- Changing the protocol: add optional fields freely. Removing or renaming a field,
  or changing its meaning, means `v: 2` and a new path `/v2`. Update the schema, the
  examples and both sides in the same commit.
