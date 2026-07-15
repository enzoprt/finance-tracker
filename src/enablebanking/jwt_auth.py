"""RS256 JWT signing for Enable Banking application authentication.

Every API request must carry a fresh JWT signed with the application's RSA
private key: https://enablebanking.com/docs/api/quick-start/
"""

import time

import jwt

from src.config import EnableBankingConfig

_TOKEN_LIFETIME_SECONDS = 3600
_RENEW_MARGIN_SECONDS = 60

_cached_token: str = ""
_cached_expires_at: float = 0.0


def _sign_jwt(config: EnableBankingConfig) -> str:
    private_key = config.private_key_path.read_text()
    now = int(time.time())
    payload = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": now,
        "exp": now + _TOKEN_LIFETIME_SECONDS,
    }
    headers = {"kid": config.application_id, "alg": "RS256", "typ": "JWT"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


def get_application_jwt(config: EnableBankingConfig) -> str:
    """Returns a cached JWT, re-signing a new one once it's close to expiry."""
    global _cached_token, _cached_expires_at

    now = time.time()
    if _cached_token and now < _cached_expires_at - _RENEW_MARGIN_SECONDS:
        return _cached_token

    _cached_token = _sign_jwt(config)
    _cached_expires_at = now + _TOKEN_LIFETIME_SECONDS
    return _cached_token
