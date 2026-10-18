"""The hub's own TLS certificate: screens connect over wss and pin its fingerprint.

Generated once, on first start, in the hub's data directory; reused afterwards so the
fingerprint screens pinned stays valid. See docs/decisions.md, 025.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import os
import socket
import ssl
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

CERT_FILE = "hub.crt"
KEY_FILE = "hub.key"
VALID_FOR = dt.timedelta(days=3650)


@dataclass(frozen=True)
class HubCertificate:
    cert_path: Path
    key_path: Path
    fingerprint: str
    """SHA-256 of the certificate (DER), lowercase hex: what a screen pins."""

    def server_context(self) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(self.cert_path, self.key_path)
        return context


def fingerprint(der: bytes) -> str:
    return hashlib.sha256(der).hexdigest()


def display(fp: str) -> str:
    """ab12cd34… → AB12 CD34 …, for reading aloud and comparing by eye."""
    return " ".join(fp[i : i + 4] for i in range(0, len(fp), 4)).upper()


def ensure_certificate(directory: Path) -> HubCertificate:
    """The hub's certificate, created on first use. Files are readable by the owner only."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    cert_path, key_path = directory / CERT_FILE, directory / KEY_FILE
    if not (cert_path.is_file() and key_path.is_file()):
        _create(cert_path, key_path)
    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    return HubCertificate(cert_path, key_path, fingerprint(cert.public_bytes(serialization.Encoding.DER)))


def _create(cert_path: Path, key_path: Path) -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AetherOS Hub")])
    now = dt.datetime.now(dt.UTC)
    names: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.DNSName(socket.gethostname()),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + VALID_FOR)
        .add_extension(x509.SubjectAlternativeName(names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    _write_private(
        key_path,
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
    )
    _write_private(cert_path, cert.public_bytes(serialization.Encoding.PEM))


def _write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(data)
