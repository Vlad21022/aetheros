"""The ambient screen's data, live from Home Assistant.

`HaClient` feeds it through `connected`, `state_changed` and `disconnected`; the hub
reads `snapshot()` and `updates()`. While Home Assistant is away the tiles say so:
the hub never falls back to demo data.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from typing import Any

from . import ha_mapping as mapping
from . import protocol as p
from .config import Entities
from .ha_mapping import EntityState
from .state import Change, changed_sections


class HomeAssistantState:
    def __init__(self, entities: Entities) -> None:
        self._entities = entities
        self._states: dict[str, EntityState] = {}
        self._connected = False
        self._current = mapping.snapshot(entities, {}, connected=False)
        self._changes: asyncio.Queue[Change] = asyncio.Queue()

    async def snapshot(self) -> p.SnapshotPayload:
        return self._current

    async def updates(self) -> AsyncIterator[Change]:
        while True:
            yield await self._changes.get()

    def connected(self, states: list[Mapping[str, Any]]) -> None:
        """Home Assistant answered: every state, fresh."""
        self._states = {state.entity_id: state for state in map(EntityState.from_json, states)}
        self._connected = True
        self._publish_everything()

    def disconnected(self) -> None:
        if not self._connected:
            return
        # Stale readings must not look current.
        self._states = {}
        self._connected = False
        self._publish_everything()

    def state_changed(self, data: Mapping[str, Any]) -> None:
        """The `data` of a state_changed event."""
        entity_id = data.get("entity_id")
        if not isinstance(entity_id, str):
            return
        new_state = data.get("new_state")
        if new_state is None:
            self._states.pop(entity_id, None)
        else:
            self._states[entity_id] = EntityState.from_json(new_state)
        if not self._connected:
            return
        old, self._current = self._current, self._build()
        for update in changed_sections(old, self._current):
            self._changes.put_nowait(update)

    def _build(self) -> p.SnapshotPayload:
        return mapping.snapshot(self._entities, self._states, connected=self._connected)

    def _publish_everything(self) -> None:
        self._current = self._build()
        self._changes.put_nowait(self._current)
