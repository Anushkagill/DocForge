"""Argon2id password hashing adapter using argon2-cffi."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from docforge.domain.interfaces import PasswordHasherInterface

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128


class Argon2PasswordHasher(PasswordHasherInterface):
    """Secure password hasher using Argon2id.

    Parameters conform to OWASP recommendations:
    - time_cost: 3 iterations
    - memory_cost: 65536 KiB (64 MiB)
    - parallelism: 4 threads
    - hash_len: 32 bytes
    - salt_len: 16 bytes
    """

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    def hash(self, password: str) -> str:
        """Hash a plaintext password with Argon2id.

        Enforces length limits (10 to 128 characters) to resist algorithmic DoS.
        """
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
        if len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters.")
        return self._hasher.hash(password)

    def verify(self, password: str, hash_str: str) -> bool:
        """Verify password against encoded hash, returning False on mismatch or malformed hash."""
        if not password or not hash_str:
            return False
        try:
            return self._hasher.verify(hash_str, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def check_needs_rehash(self, hash_str: str) -> bool:
        """Return True if hash parameters do not match current configured cost."""
        try:
            return self._hasher.check_needs_rehash(hash_str)
        except (InvalidHashError, VerificationError):
            return True
