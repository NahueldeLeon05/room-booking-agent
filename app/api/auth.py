from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_SECRET


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(user_id: int) -> str:
    """Create a signed access token for an authenticated user."""
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=JWT_EXPIRATION_HOURS
    )
    payload = {"sub": str(user_id), "exp": expires_at}

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Validate an access token and return its user ID."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    subject = payload.get("sub")

    if subject is None:
        raise JWTError("Token does not contain a subject")

    try:
        return int(subject)
    except (TypeError, ValueError) as error:
        raise JWTError("Token subject is not a valid user ID") from error


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its stored hash."""
    return password_context.verify(plain, hashed)
