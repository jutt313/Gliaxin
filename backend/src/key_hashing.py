import base64
import hashlib
import hmac
import secrets

PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16

try:
    import bcrypt as _bcrypt
except ModuleNotFoundError:
    _bcrypt = None


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def hash_key(raw_key: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        raw_key.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{PBKDF2_PREFIX}${PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_key(raw_key: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$2"):
        if _bcrypt is None:
            return False
        try:
            return _bcrypt.checkpw(raw_key.encode("utf-8"), stored_hash.encode("utf-8"))
        except ValueError:
            return False

    try:
        prefix, iterations_text, encoded_salt, encoded_digest = stored_hash.split("$", 3)
    except ValueError:
        return False

    if prefix != PBKDF2_PREFIX:
        return False

    try:
        iterations = int(iterations_text)
        salt = _b64decode(encoded_salt)
        expected_digest = _b64decode(encoded_digest)
    except (TypeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        raw_key.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)
