"""Typed mirror of contracts/aether-protocol.schema.json (protocol v1).

The JSON Schema is the source of truth. tests/test_contract.py checks that every
example in contracts/examples parses here and serializes back unchanged, so the two
cannot drift apart silently.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

PROTOCOL_VERSION = 1


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- shared shapes ---------------------------------------------------------

TileKind = Literal["light", "lock", "climate", "computer", "media", "sensor", "switch", "cover"]
TapAction = Literal["toggle", "turn_on", "turn_off"]
PlaybackControl = Literal["toggle", "next", "previous"]


class Tile(_Model):
    entityId: str = Field(min_length=1, max_length=255)
    kind: TileKind
    title: str = Field(max_length=60)
    state: str = Field(max_length=60)
    active: bool
    alert: bool | None = None
    tap: TapAction | None = None


class Home(_Model):
    summary: str = Field(max_length=120)
    tiles: list[Tile] = Field(max_length=24)


class Weather(_Model):
    temperatureC: float
    condition: str = Field(max_length=60)
    summary: str | None = Field(default=None, max_length=120)


class Event(_Model):
    title: str = Field(max_length=120)
    start: datetime
    end: datetime | None = None
    note: str | None = Field(default=None, max_length=160)


class NowPlaying(_Model):
    source: str = Field(max_length=80)
    title: str = Field(max_length=120)
    subtitle: str | None = Field(default=None, max_length=120)
    playing: bool
    progress: float | None = Field(default=None, ge=0, le=1)
    entityId: str | None = Field(default=None, min_length=1, max_length=255)
    controls: list[PlaybackControl] | None = Field(default=None, max_length=3)


# --- payloads --------------------------------------------------------------


class Capabilities(_Model):
    touch: bool
    microphone: bool
    speaker: bool
    presence: bool


class Size(_Model):
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class HelloPayload(_Model):
    screenId: str = Field(min_length=1, max_length=64)
    name: str = Field(max_length=80)
    room: str | None = Field(default=None, max_length=80)
    protocol: Literal[1]
    locale: str | None = Field(default=None, max_length=16)
    token: str | None = Field(default=None, min_length=1, max_length=128)
    capabilities: Capabilities
    size: Size

    def __repr__(self) -> str:
        # Never print the token, wherever a hello ends up.
        return f"HelloPayload(screenId={self.screenId!r}, name={self.name!r})"

    __str__ = __repr__


class PairRequestPayload(_Model):
    screenId: str = Field(min_length=1, max_length=64)
    name: str = Field(max_length=80)
    code: str = Field(pattern=r"^[0-9]{6}$")


class PairResultPayload(_Model):
    token: str = Field(min_length=1, max_length=128)
    hubName: str = Field(max_length=80)

    def __repr__(self) -> str:
        return f"PairResultPayload(hubName={self.hubName!r})"

    __str__ = __repr__


class UtterancePayload(_Model):
    text: str = Field(min_length=1, max_length=2000)
    source: Literal["voice", "typed"]
    locale: str | None = Field(default=None, max_length=16)


class ControlPayload(_Model):
    entityId: str = Field(min_length=1, max_length=255)
    action: Literal["toggle", "turn_on", "turn_off", "set", "next", "previous"]
    value: float | str | bool | None = None


class PresencePayload(_Model):
    present: bool


class ConfirmResponsePayload(_Model):
    requestId: str = Field(min_length=1, max_length=64)
    optionId: str = Field(min_length=1, max_length=64)


class WelcomePayload(_Model):
    hubName: str = Field(max_length=80)
    protocol: Literal[1]


class SnapshotPayload(_Model):
    home: Home
    weather: Weather | None = None
    nextEvent: Event | None = None
    nowPlaying: NowPlaying | None = None
    glance: str | None = Field(default=None, min_length=1, max_length=120)
    """The line under the far clock, composed by the hub (glance.py)."""


Glance = Annotated[str, Field(min_length=1, max_length=120)]


class UpdatePayload(_Model):
    section: Literal["home", "weather", "nextEvent", "nowPlaying", "glance"]
    value: Home | Weather | Event | NowPlaying | Glance | None

    @model_validator(mode="before")
    @classmethod
    def _value_matches_section(cls, data: object) -> object:
        if isinstance(data, dict) and isinstance(data.get("value"), dict):
            expected = {"home": Home, "weather": Weather, "nextEvent": Event, "nowPlaying": NowPlaying}
            model = expected.get(data.get("section"))  # type: ignore[arg-type]
            if model is not None:
                data = {**data, "value": model.model_validate(data["value"])}
        return data

    @model_validator(mode="after")
    def _home_is_never_null(self) -> UpdatePayload:
        if self.section == "home" and self.value is None:
            raise ValueError("home cannot be cleared")
        if (self.section == "glance") != isinstance(self.value, str) and self.value is not None:
            raise ValueError("only glance carries a string")
        return self


class AgentStatusPayload(_Model):
    state: Literal["idle", "listening", "thinking", "speaking", "acting"]
    tier: Literal[0, 1, 2] | None = None


class AgentReplyPayload(_Model):
    text: str = Field(max_length=8000)
    final: bool


class Step(_Model):
    label: str = Field(min_length=1, max_length=120)
    status: Literal["done", "pending", "failed", "skipped"]
    note: str | None = Field(default=None, max_length=120)
    kind: TileKind | None = None


class Option(_Model):
    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=60)
    role: Literal["primary", "secondary", "cancel"]


class ConfirmRequestPayload(_Model):
    requestId: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=200)
    detail: str | None = Field(default=None, max_length=600)
    steps: list[Step] = Field(max_length=12)
    options: list[Option] = Field(min_length=1, max_length=3)
    expiresAt: datetime | None = None


class ActionResultPayload(_Model):
    requestId: str | None = Field(default=None, min_length=1, max_length=64)
    ok: bool
    message: str = Field(max_length=300)


class ScreenCommandPayload(_Model):
    command: Literal["dim", "wake", "set_brightness", "set_theme"]
    value: float | str | None = None


ErrorCode = Literal[
    "bad_message", "unsupported_protocol", "unauthorized", "unknown_entity", "not_allowed", "unavailable", "internal"
]


class ErrorPayload(_Model):
    code: ErrorCode
    message: str = Field(max_length=300)


# --- messages --------------------------------------------------------------


class _Envelope(_Model):
    v: Literal[1]
    id: str = Field(min_length=1, max_length=64)
    ts: datetime
    replyTo: str | None = Field(default=None, min_length=1, max_length=64)


class Hello(_Envelope):
    type: Literal["hello"]
    payload: HelloPayload


class Utterance(_Envelope):
    type: Literal["utterance"]
    payload: UtterancePayload


class Control(_Envelope):
    type: Literal["control"]
    payload: ControlPayload


class Presence(_Envelope):
    type: Literal["presence"]
    payload: PresencePayload


class ConfirmResponse(_Envelope):
    type: Literal["confirm.response"]
    payload: ConfirmResponsePayload


class PairRequest(_Envelope):
    type: Literal["pair.request"]
    payload: PairRequestPayload


class PairResult(_Envelope):
    type: Literal["pair.result"]
    payload: PairResultPayload


class Welcome(_Envelope):
    type: Literal["welcome"]
    payload: WelcomePayload


class StateSnapshot(_Envelope):
    type: Literal["state.snapshot"]
    payload: SnapshotPayload


class StateUpdate(_Envelope):
    type: Literal["state.update"]
    payload: UpdatePayload


class AgentStatus(_Envelope):
    type: Literal["agent.status"]
    payload: AgentStatusPayload


class AgentReply(_Envelope):
    type: Literal["agent.reply"]
    payload: AgentReplyPayload


class ConfirmRequest(_Envelope):
    type: Literal["confirm.request"]
    payload: ConfirmRequestPayload


class ActionResult(_Envelope):
    type: Literal["action.result"]
    payload: ActionResultPayload


class ScreenCommand(_Envelope):
    type: Literal["screen.command"]
    payload: ScreenCommandPayload


class Error(_Envelope):
    type: Literal["error"]
    payload: ErrorPayload


Message = Annotated[
    Union[
        Hello,
        Utterance,
        Control,
        Presence,
        ConfirmResponse,
        PairRequest,
        Welcome,
        PairResult,
        StateSnapshot,
        StateUpdate,
        AgentStatus,
        AgentReply,
        ConfirmRequest,
        ActionResult,
        ScreenCommand,
        Error,
    ],
    Field(discriminator="type"),
]

_adapter: TypeAdapter[Message] = TypeAdapter(Message)


def parse(raw: str | bytes) -> Message:
    """Parse one WebSocket frame. Raises pydantic.ValidationError on a bad frame."""
    return _adapter.validate_json(raw)


def dump(message: Message) -> str:
    """Serialize for the wire. Fields left unset are omitted; explicit nulls are kept."""
    return _adapter.dump_json(message, exclude_unset=True).decode()


def new(cls: type[_Envelope], payload: BaseModel, reply_to: str | None = None) -> Message:
    """Build an outgoing message with a fresh id and timestamp."""
    fields: dict[str, object] = {
        "v": PROTOCOL_VERSION,
        "type": cls.model_fields["type"].annotation.__args__[0],  # type: ignore[union-attr]
        "id": uuid.uuid4().hex[:16],
        "ts": datetime.now(UTC).replace(microsecond=0),
        "payload": payload,
    }
    if reply_to is not None:
        fields["replyTo"] = reply_to
    return cls(**fields)  # type: ignore[return-value]
