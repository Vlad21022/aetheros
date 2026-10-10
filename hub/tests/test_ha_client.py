"""The Home Assistant client against a stand-in server, over a real WebSocket."""

import asyncio
import contextlib
import logging

import pytest
from fake_ha import TOKEN, FakeHa

from aether_hub.ha_client import HaClient, HaError, HaUnavailable, websocket_url


class Recorder:
    def __init__(self) -> None:
        self.events: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

    def client(self, ha: FakeHa, token: str = TOKEN) -> HaClient:
        return HaClient(
            ha.url,
            token,
            on_connected=lambda states: self.events.put_nowait(("connected", states)),
            on_state_changed=lambda data: self.events.put_nowait(("changed", data)),
            on_disconnected=lambda: self.events.put_nowait(("disconnected", None)),
            retry_delays=(0.01,),
        )

    async def next(self, kind: str) -> object:
        async with asyncio.timeout(2):
            while True:
                found, value = await self.events.get()
                if found == kind:
                    return value


@contextlib.asynccontextmanager
async def running(client: HaClient):
    task = asyncio.create_task(client.run())
    try:
        yield task
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://ha.local:8123", "ws://ha.local:8123/api/websocket"),
        ("https://ha.example/", "wss://ha.example/api/websocket"),
        ("ws://10.0.0.5:8123/api/websocket", "ws://10.0.0.5:8123/api/websocket"),
    ],
)
def test_websocket_url(url, expected):
    assert websocket_url(url) == expected


async def test_connects_and_gets_every_state(fake_ha):
    await fake_ha.set_state("light.office", "on", {"friendly_name": "Birou"})
    recorder = Recorder()
    client = recorder.client(fake_ha)
    async with running(client):
        states = await recorder.next("connected")
        assert [s["entity_id"] for s in states] == ["light.office"]
        assert client.connected


async def test_state_changes_arrive(fake_ha):
    recorder = Recorder()
    async with running(recorder.client(fake_ha)):
        await recorder.next("connected")
        await fake_ha.set_state("light.office", "off")
        data = await recorder.next("changed")
        assert data["entity_id"] == "light.office"
        assert data["new_state"]["state"] == "off"


async def test_call_service(fake_ha):
    await fake_ha.set_state("light.office", "off")
    recorder = Recorder()
    client = recorder.client(fake_ha)
    async with running(client):
        await recorder.next("connected")
        await client.call_service("light", "toggle", "light.office")
        assert fake_ha.calls == [("light", "toggle", "light.office")]
        assert (await recorder.next("changed"))["new_state"]["state"] == "on"


async def test_failed_service_raises(fake_ha):
    fake_ha.fail_services = True
    recorder = Recorder()
    client = recorder.client(fake_ha)
    async with running(client):
        await recorder.next("connected")
        with pytest.raises(HaError, match="Service failed"):
            await client.call_service("light", "toggle", "light.office")


async def test_call_service_without_a_connection(fake_ha):
    client = Recorder().client(fake_ha)
    with pytest.raises(HaUnavailable):
        await client.call_service("light", "toggle", "light.office")


async def test_rejected_token_stops_and_is_not_logged(fake_ha, caplog):
    recorder = Recorder()
    client = recorder.client(fake_ha, token="wrong-token")
    with caplog.at_level(logging.DEBUG):
        async with asyncio.timeout(2):
            await client.run()
    assert fake_ha.auth_attempts == 1
    assert not client.connected
    # Everything the hub logged, at DEBUG; websockets.server is the stand-in's side.
    logged = "\n".join(r.getMessage() for r in caplog.records if r.name != "websockets.server")
    assert "AETHER_HA_TOKEN" in logged
    assert "wrong-token" not in logged


async def test_reconnects_after_the_connection_drops(fake_ha):
    recorder = Recorder()
    client = recorder.client(fake_ha)
    async with running(client):
        await recorder.next("connected")
        await fake_ha.set_state("light.office", "on")
        await fake_ha.drop_connections()
        await recorder.next("disconnected")
        states = await recorder.next("connected")
        assert [s["state"] for s in states] == ["on"]
        assert client.connected


async def test_keeps_trying_while_home_assistant_is_down():
    ha = FakeHa()
    await ha.start()
    port = ha.port
    await ha.stop()
    recorder = Recorder()
    async with running(recorder.client(ha)):
        await asyncio.sleep(0.05)
        await ha.start(port)
        try:
            await recorder.next("connected")
        finally:
            await ha.stop()
