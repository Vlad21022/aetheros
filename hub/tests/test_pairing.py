"""Who may talk to the hub: tokens, codes and the paired screens file."""

import json
import stat

import pytest

from aether_hub.pairing import CODE_TTL, MAX_PENDING, Pairing, PairingError


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Inbox:
    """Stands in for a screen's connection: records the token it gets."""

    def __init__(self) -> None:
        self.tokens: list[str] = []

    async def __call__(self, token: str) -> None:
        self.tokens.append(token)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def pairing(tmp_path, clock):
    return Pairing(tmp_path / "data" / "screens.json", clock)


def test_a_token_opens_only_its_own_screen(pairing):
    token = pairing.add("kitchen", "Bucătărie")
    assert pairing.verify("kitchen", token)
    assert not pairing.verify("kitchen", token + "x")
    assert not pairing.verify("office", token)
    assert not pairing.verify("kitchen", None)
    assert not pairing.verify("kitchen", "")


def test_only_a_hash_is_kept_and_only_the_owner_can_read_it(pairing, tmp_path):
    token = pairing.add("kitchen", "Bucătărie")
    path = tmp_path / "data" / "screens.json"
    assert token not in path.read_text()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text())["kitchen"]["name"] == "Bucătărie"


def test_pairings_survive_a_restart(pairing, tmp_path):
    token = pairing.add("kitchen", "Bucătărie")
    again = Pairing(tmp_path / "data" / "screens.json")
    assert again.verify("kitchen", token)
    assert [s.screen_id for s in again.screens()] == ["kitchen"]


def test_pairing_again_replaces_the_old_token(pairing):
    old = pairing.add("kitchen", "Bucătărie")
    new = pairing.add("kitchen", "Bucătărie")
    assert not pairing.verify("kitchen", old)
    assert pairing.verify("kitchen", new)


async def test_the_owner_confirms_the_code_the_screen_shows(pairing):
    inbox = Inbox()
    pairing.request("kitchen", "Bucătărie", "482913", inbox)
    screen = await pairing.approve("482913")
    assert (screen.screen_id, screen.name) == ("kitchen", "Bucătărie")
    assert pairing.verify("kitchen", inbox.tokens[0])
    with pytest.raises(PairingError):
        await pairing.approve("482913")


async def test_a_wrong_code_pairs_nothing(pairing):
    inbox = Inbox()
    pairing.request("kitchen", "Bucătărie", "482913", inbox)
    with pytest.raises(PairingError, match="Niciun ecran"):
        await pairing.approve("111111")
    assert inbox.tokens == [] and pairing.screens() == []


async def test_codes_expire(pairing, clock):
    pairing.request("kitchen", "Bucătărie", "482913", Inbox())
    clock.now += CODE_TTL + 1
    with pytest.raises(PairingError):
        await pairing.approve("482913")


async def test_a_new_code_from_the_same_screen_replaces_the_old(pairing):
    pairing.request("kitchen", "Bucătărie", "111111", Inbox())
    pairing.request("kitchen", "Bucătărie", "222222", Inbox())
    with pytest.raises(PairingError):
        await pairing.approve("111111")
    await pairing.approve("222222")


async def test_only_a_few_screens_can_wait_at_once(pairing):
    for i in range(MAX_PENDING + 1):
        pairing.request(f"screen-{i}", "x", f"{i:06d}", Inbox())
    with pytest.raises(PairingError):
        await pairing.approve("000000")
    await pairing.approve(f"{MAX_PENDING:06d}")


async def test_two_screens_with_the_same_code_pair_neither(pairing):
    pairing.request("kitchen", "Bucătărie", "482913", Inbox())
    pairing.request("office", "Birou", "482913", Inbox())
    with pytest.raises(PairingError, match="același cod"):
        await pairing.approve("482913")
    assert pairing.screens() == []


async def test_a_screen_that_left_cannot_be_paired(pairing):
    pairing.request("kitchen", "Bucătărie", "482913", Inbox())
    pairing.withdraw("kitchen")
    with pytest.raises(PairingError):
        await pairing.approve("482913")


async def test_no_pairing_is_kept_if_the_token_never_arrived(pairing):
    async def gone(token: str) -> None:
        raise ConnectionError("closed")

    pairing.request("kitchen", "Bucătărie", "482913", gone)
    with pytest.raises(PairingError, match="deconectat"):
        await pairing.approve("482913")
    assert pairing.screens() == []


def test_forget(pairing):
    token = pairing.add("kitchen", "Bucătărie")
    assert pairing.forget("kitchen").name == "Bucătărie"
    assert not pairing.verify("kitchen", token)
    assert pairing.forget("kitchen") is None
