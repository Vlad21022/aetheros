"""One hub certificate for the whole test run, and a client that trusts only it."""

import ssl
import tempfile
from pathlib import Path

from aether_hub.tls import ensure_certificate

CERTIFICATE = ensure_certificate(Path(tempfile.mkdtemp(prefix="aether-tls-")))
SERVER_SSL = CERTIFICATE.server_context()
CLIENT_SSL = ssl.create_default_context(cafile=CERTIFICATE.cert_path)
