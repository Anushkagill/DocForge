"""Google OAuth 2.0 and OpenID Connect (OIDC) adapter with PKCE and claims validation."""

import base64
import hashlib
import math
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from docforge.domain.interfaces import OAuthProviderInterface, OAuthValidationError

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ALLOWED_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
CLOCK_SKEW_SECONDS = 60
MAX_REALISTIC_EPOCH = 253402300799  # 9999-12-31T23:59:59Z


def _is_finite_timestamp(val: Any) -> bool:
    """Validate that a timestamp is a finite, realistic numeric epoch.

    Handles OverflowError for arbitrarily large Python integers.
    Rejects NaN, +inf, -inf, booleans, strings, and out-of-range epochs.
    """
    if val is None or isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    try:
        if not math.isfinite(val):
            return False
    except (OverflowError, TypeError):
        return False
    return 0 <= val <= MAX_REALISTIC_EPOCH


class GoogleOIDCAdapter(OAuthProviderInterface):
    """Adapter for Google OAuth 2.0 Authorization Code Flow with PKCE and OIDC ID token validation."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        jwks_url: str = GOOGLE_CERTS_URL,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._jwks_url = jwks_url
        self._jwks_client: PyJWKClient | None = None

    @property
    def jwks_client(self) -> PyJWKClient:
        """Lazy-loaded PyJWKClient for caching Google public keys."""
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(self._jwks_url, cache_jwk_set=True, lifespan=3600)
        return self._jwks_client

    def generate_authorization_url(self) -> tuple[str, str, str, str]:
        """Generate auth URL and cryptographic security tokens: (auth_url, state, nonce, code_verifier)."""
        state = secrets.token_hex(32)
        nonce = secrets.token_hex(32)

        raw_verifier = secrets.token_bytes(32)
        code_verifier = base64.urlsafe_b64encode(raw_verifier).decode("utf-8").rstrip("=")

        challenge_digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_digest).decode("utf-8").rstrip("=")

        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "online",
            "prompt": "select_account",
        }
        auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return auth_url, state, nonce, code_verifier

    def verify_id_token_claims(
        self,
        claims: dict[str, Any],
        expected_nonce: str,
        current_time: float | None = None,
    ) -> tuple[str, str]:
        """Validate all claims inside a decoded Google ID token.

        Enforces:
        - Non-empty string sub.
        - Allowed issuer.
        - aud matching client_id (handling scalar string and array of strings).
        - azp matching client_id when multiple audiences are present.
        - nonce matching expected_nonce.
        - email non-empty string.
        - email_verified is True (strictly boolean True).
        - iat and exp are finite numbers, within valid bounds, not expired, not future-dated beyond skew.

        Returns (email, sub).
        Raises OAuthValidationError on any validation failure.
        """
        now = time.time() if current_time is None else current_time

        # 1. Issuer check
        iss = claims.get("iss")
        if not isinstance(iss, str) or iss not in ALLOWED_ISSUERS:
            raise OAuthValidationError(f"Invalid token issuer: {iss!r}")

        # 2. Audience & Authorized Party check
        aud = claims.get("aud")
        if isinstance(aud, str):
            if aud != self._client_id:
                raise OAuthValidationError(f"Token audience mismatch: {aud!r}")
        elif isinstance(aud, list):
            if not aud or not all(isinstance(a, str) and a.strip() for a in aud):
                raise OAuthValidationError("Token audience list contains invalid elements.")
            if self._client_id not in aud:
                raise OAuthValidationError(f"Client ID not in token audiences: {aud!r}")
            azp = claims.get("azp")
            if azp != self._client_id:
                raise OAuthValidationError(f"Authorized party mismatch: {azp!r}")
        else:
            raise OAuthValidationError("Token audience claim is missing or malformed.")

        # 3. Subject check
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            raise OAuthValidationError("Token subject claim is missing or empty.")

        # 4. Nonce check
        if not isinstance(expected_nonce, str) or not expected_nonce.strip():
            raise OAuthValidationError("Expected nonce must be a non-empty string.")
        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not nonce.strip() or nonce != expected_nonce:
            raise OAuthValidationError("Token nonce mismatch.")

        # 5. Email & verification check
        email = claims.get("email")
        if not isinstance(email, str) or not email.strip() or "@" not in email:
            raise OAuthValidationError("Token email claim is missing or malformed.")
        email_verified = claims.get("email_verified")
        if email_verified is not True:
            raise OAuthValidationError("Google email address is not verified.")

        # 6. Timestamp finiteness checks
        iat = claims.get("iat")
        if not _is_finite_timestamp(iat):
            raise OAuthValidationError(f"Invalid or non-finite iat timestamp: {iat!r}")

        exp = claims.get("exp")
        if not _is_finite_timestamp(exp):
            raise OAuthValidationError(f"Invalid or non-finite exp timestamp: {exp!r}")

        # 7. Expiry & clock skew checks
        if exp < (now - CLOCK_SKEW_SECONDS):
            raise OAuthValidationError("Google ID token has expired.")
        if iat > (now + CLOCK_SKEW_SECONDS):
            raise OAuthValidationError("Google ID token iat is in the future.")

        return email.lower().strip(), sub.strip()

    async def verify_callback(
        self,
        code: str,
        code_verifier: str,
        expected_nonce: str,
    ) -> tuple[str, str]:
        """Exchange authorization code and verify ID token against Google's public JWKS."""
        if not code or not code_verifier or not expected_nonce:
            raise OAuthValidationError("Missing code, code_verifier, or expected_nonce.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": self._redirect_uri,
                },
            )
            if token_resp.status_code != 200:
                raise OAuthValidationError(
                    f"Token exchange failed with status {token_resp.status_code}: {token_resp.text}"
                )

            token_data = token_resp.json()
            id_token_raw = token_data.get("id_token")
            if not id_token_raw or not isinstance(id_token_raw, str):
                raise OAuthValidationError("Missing id_token in token exchange response.")

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(id_token_raw)
            decoded_claims = jwt.decode(
                id_token_raw,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False, "verify_iss": False, "verify_exp": False},
            )
        except Exception as e:
            raise OAuthValidationError(f"ID token signature verification failed: {e}") from e

        return self.verify_id_token_claims(decoded_claims, expected_nonce)
