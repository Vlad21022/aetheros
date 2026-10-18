"""Which screens may talk to the hub, and how a new one is let in.

A paired screen holds a token; the hub keeps only its SHA-256, in screens.json in
the data directory (owner-only). An unpaired screen asks with the six-digit code it
shows; the owner confirms that code on the hub (`aether-hub pair <code>`), and only
then does the screen get a token. See docs/decisions.md, 025.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SCREENS_FILE = "screens.json"
MAX_PENDING = 5
CODE_TTL = 300.0
"""Seconds a pairing code stays valid."""


@dataclass(frozen=True)
class PairedScreen:
    screen_id: str
    name: str
    paired_at: str


@dataclass
class _Pending:
    screen_id: str
    name: str
    code: str
    expires: float
    deliver: Callable[[str], Awaitable[None]]


class PairingError(Exception):
    """Why a code was not accepted. The message is for the owner, in Romanian."""


class Pairing:
    def __init__(self, path: Path, clock: Callable[[], float] = time.monotonic) -> None:
        self._path = path
        self._clock = clock
        self._screens: dict[str, dict[str, str]] = {}
        self._pending: list[_Pending] = []
        if path.is_file():
            self._screens = json.loads(path.read_text(encoding="utf-8"))

    # --- paired screens ---------------------------------------------------------

    def verify(self, screen_id: str, token: str | None) -> bool:
        record = self._screens.get(screen_id)
        if record is None or not token:
            return False
        return hmac.compare_digest(record["tokenHash"], _hash(token))

    def add(self, screen_id: str, name: str) -> str:
        """Pairs a screen and returns its new token. Any earlier token stops working."""
        token = secrets.token_urlsafe(32)
        self._screens[screen_id] = {
            "name": name,
            "pairedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "tokenHash": _hash(token),
        }
        self._save()
        return token

    def forget(self, screen_id: str) -> PairedScreen | None:
        record = self._screens.pop(screen_id, None)
        if record is None:
            return None
        self._save()
        return PairedScreen(screen_id, record["name"], record["pairedAt"])

    def screens(self) -> list[PairedScreen]:
        return [PairedScreen(sid, r["name"], r["pairedAt"]) for sid, r in sorted(self._screens.items())]

    # --- pairing ----------------------------------------------------------------

    def request(self, screen_id: str, name: str, code: str, deliver: Callable[[str], Awaitable[None]]) -> None:
        """An unpaired screen shows `code`; `deliver` sends it the token once the owner confirms."""
        self._expire()
        self._pending = [p for p in self._pending if p.screen_id != screen_id]
        self._pending.append(_Pending(screen_id, name, code, self._clock() + CODE_TTL, deliver))
        # A stranger on the network must not be able to crowd out the owner's screen for long.
        del self._pending[:-MAX_PENDING]

    def withdraw(self, screen_id: str) -> None:
        """The screen went away before its code was confirmed."""
        self._pending = [p for p in self._pending if p.screen_id != screen_id]

    async def approve(self, code: str) -> PairedScreen:
        self._expire()
        matches = [p for p in self._pending if hmac.compare_digest(p.code, code)]
        if not matches:
            raise PairingError(f"Niciun ecran nu așteaptă codul {code}. Verifică ecranul; codul expiră în 5 minute.")
        if len(matches) > 1:
            raise PairingError("Două ecrane arată același cod. Așteaptă un cod nou pe ecran și încearcă din nou.")
        pending = matches[0]
        self._pending.remove(pending)
        token = self.add(pending.screen_id, pending.name)
        try:
            await pending.deliver(token)
        except Exception:
            # The screen never got its token: do not keep a pairing nobody can use.
            self.forget(pending.screen_id)
            raise PairingError("Ecranul s-a deconectat înainte să primească asocierea. Încearcă din nou.") from None
        return PairedScreen(pending.screen_id, pending.name, self._screens[pending.screen_id]["pairedAt"])

    def _expire(self) -> None:
        now = self._clock()
        self._pending = [p for p in self._pending if p.expires > now]

    def _save(self) -> None:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(self._screens, file, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
