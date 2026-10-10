"""Tier 0: a tap on a tile, mapped straight to a Home Assistant service. No model.

The rules are a fixed table. Only entities the hub was configured with can be
controlled, and only with reversible actions; anything consequential waits for
the confirmation flow. See docs/decisions.md, 019.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

from . import protocol as p
from .ha_client import HaError, HaUnavailable

log = logging.getLogger("aether_hub.tier0")

# (domain, control action) → service in that domain.
RULES: dict[tuple[str, str], str] = {
    ("light", "toggle"): "toggle",
    ("light", "turn_on"): "turn_on",
    ("light", "turn_off"): "turn_off",
    ("switch", "toggle"): "toggle",
    ("switch", "turn_on"): "turn_on",
    ("switch", "turn_off"): "turn_off",
    ("media_player", "toggle"): "media_play_pause",
    # Locking is always safe. Unlocking a door is consequential: not from a tap.
    ("lock", "turn_on"): "lock",
}

SENT = "Comanda a fost trimisă."
REFUSED = "Nu a mers. Home Assistant a refuzat comanda."


class Actuator(Protocol):
    """Whatever carries out a service call: the Home Assistant client, or the demo home."""

    async def call_service(self, domain: str, service: str, entity_id: str) -> None: ...


class Tier0Error(Exception):
    """The control was not carried out. Becomes an `error` reply with this code."""

    def __init__(self, code: p.ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code: p.ErrorCode = code


class Tier0Router:
    def __init__(self, entities: Iterable[str], actuator: Actuator) -> None:
        self._entities = frozenset(entities)
        self._actuator = actuator

    async def control(self, control: p.ControlPayload) -> p.ActionResultPayload:
        entity_id, action = control.entityId, control.action
        if entity_id not in self._entities:
            raise Tier0Error("unknown_entity", f"{entity_id} is not an entity of this hub.")

        domain = entity_id.partition(".")[0]
        service = RULES.get((domain, action))
        if service is None:
            if domain == "lock":
                raise Tier0Error("not_allowed", "Unlocking needs a confirmation; a tile can only lock.")
            raise Tier0Error("not_allowed", f"{action} is not allowed on {domain} entities.")

        try:
            await self._actuator.call_service(domain, service, entity_id)
        except HaUnavailable:
            raise Tier0Error("unavailable", "Home Assistant is not reachable.") from None
        except HaError as exc:
            log.warning("%s.%s on %s failed: %s", domain, service, entity_id, exc)
            return p.ActionResultPayload(ok=False, message=REFUSED)
        log.info("tier 0: %s.%s on %s", domain, service, entity_id)
        return p.ActionResultPayload(ok=True, message=SENT)
