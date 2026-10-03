import hashlib
import hmac
import time

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from .config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Wrong-PIN protection: after 5 wrong tries, everyone must wait 5 minutes.
MAX_FAILURES = 5
WINDOW_SECONDS = 300
_failures: list[float] = []


def _token() -> str:
    # Derived from the PIN, so changing APP_PIN on Render logs every device out.
    return hmac.new(
        settings.app_pin.encode(), b"stockflow-session-v1", hashlib.sha256
    ).hexdigest()


def require_auth(authorization: str = Header(default="")):
    """Attached to every data route in main.py. Does nothing if APP_PIN is not set."""
    if not settings.app_pin:
        return
    supplied = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied.encode(), _token().encode()):
        raise HTTPException(status_code=401, detail="Not logged in")


class LoginBody(BaseModel):
    pin: str


@router.post("/login")
def login(body: LoginBody):
    if not settings.app_pin:
        return {"token": "open"}

    now = time.time()
    _failures[:] = [t for t in _failures if now - t < WINDOW_SECONDS]
    if len(_failures) >= MAX_FAILURES:
        raise HTTPException(
            status_code=429,
            detail="Too many wrong PINs. Please wait 5 minutes and try again.",
        )

    if not hmac.compare_digest(body.pin.encode(), settings.app_pin.encode()):
        _failures.append(now)
        raise HTTPException(status_code=401, detail="Wrong PIN")

    return {"token": _token()}
