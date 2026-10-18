"""The hub's certificate: made once, kept private, and the only way in."""

import ssl
import stat

import pytest
from cryptography import x509
from tls_helpers import CLIENT_SSL, SERVER_SSL
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import InvalidHandshake

from aether_hub.tls import display, ensure_certificate, fingerprint


def test_made_once_and_reused(tmp_path):
    first = ensure_certificate(tmp_path / "data")
    again = ensure_certificate(tmp_path / "data")
    assert first.fingerprint == again.fingerprint
    assert len(first.fingerprint) == 64
    assert first.cert_path.read_bytes() == again.cert_path.read_bytes()


def test_files_are_for_the_owner_only(tmp_path):
    certificate = ensure_certificate(tmp_path / "data")
    assert stat.S_IMODE((tmp_path / "data").stat().st_mode) == 0o700
    for path in (certificate.cert_path, certificate.key_path):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_the_fingerprint_is_the_sha256_of_the_certificate(tmp_path):
    certificate = ensure_certificate(tmp_path)
    cert = x509.load_pem_x509_certificate(certificate.cert_path.read_bytes())
    der = ssl.PEM_cert_to_DER_cert(certificate.cert_path.read_text())
    assert fingerprint(der) == certificate.fingerprint
    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "localhost" in names.get_values_for_type(x509.DNSName)


def test_display_groups_the_fingerprint():
    assert display("ab12cd34ef56") == "AB12 CD34 EF56"


async def _echo(ws):
    async for message in ws:
        await ws.send(message)


async def test_only_tls_gets_in():
    async with serve(_echo, "127.0.0.1", 0, ssl=SERVER_SSL) as server:
        port = server.sockets[0].getsockname()[1]
        async with connect(f"wss://127.0.0.1:{port}/v1", ssl=CLIENT_SSL) as ws:
            await ws.send("hi")
            assert await ws.recv() == "hi"
        with pytest.raises(InvalidHandshake):
            async with connect(f"ws://127.0.0.1:{port}/v1", open_timeout=2):
                pass


async def test_a_client_that_trusts_another_hub_is_refused(tmp_path):
    other = ensure_certificate(tmp_path / "other")
    elsewhere = ssl.create_default_context(cafile=other.cert_path)
    async with serve(_echo, "127.0.0.1", 0, ssl=SERVER_SSL) as server:
        port = server.sockets[0].getsockname()[1]
        with pytest.raises(ssl.SSLCertVerificationError):
            async with connect(f"wss://127.0.0.1:{port}/v1", ssl=elsewhere):
                pass
