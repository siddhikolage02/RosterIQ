
import bcrypt


def hash_password(password: str) -> str:
    """Create a secure bcrypt password hash."""

    if not isinstance(password, str):
        raise ValueError("Password must be a string.")

    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes.")

    password_bytes = password.encode("utf-8")

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(rounds=12),
    )

    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its stored bcrypt hash."""

    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False

    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False
