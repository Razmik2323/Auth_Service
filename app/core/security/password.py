from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)


def hash_password(password: str) -> str:
    """Return an Argon2id hash for the given password."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True when the password matches the stored hash."""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """Return True when the hash should be recomputed with current parameters."""
    return _hasher.check_needs_rehash(password_hash)
