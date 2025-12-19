import os
import secrets
from fastapi import Header, HTTPException

def require_admin(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    expected = os.getenv("ADMIN_KEY", "")
    if not expected:
        # Yanlışlıkla açık admin bırakmamak için
        raise HTTPException(status_code=500, detail="ADMIN_KEY not configured")

    if not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail="Invalid admin key")
