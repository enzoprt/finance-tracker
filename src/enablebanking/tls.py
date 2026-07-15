"""Self-signed TLS certificate for the local HTTPS OAuth callback listener.

Enable Banking's redirect_url is registered as https://localhost:8080/callback,
so the local listener must speak TLS. Browsers show a one-time
untrusted-certificate warning for this self-signed cert; that's expected and
safe to bypass since the listener never leaves this machine.
"""

import ssl
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.config import DATA_DIR

CERT_FILE = DATA_DIR / "localhost_cert.pem"
KEY_FILE = DATA_DIR / "localhost_key.pem"


def _generate_cert() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )

    KEY_FILE.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def get_ssl_context() -> ssl.SSLContext:
    if not (CERT_FILE.is_file() and KEY_FILE.is_file()):
        _generate_cert()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))
    return context
