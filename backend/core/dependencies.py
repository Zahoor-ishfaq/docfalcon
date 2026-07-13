from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from backend.core.database import get_db
from backend.core.security import decode_token

bearer = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    """Decode Bearer token and return the user doc. Raises 401 on any failure."""
    try:
        payload = decode_token(creds.credentials, "access")
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

    db = get_db()
    user = await db.users.find_one({"_id": __import__("bson").ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(401, "User not found")

    user["_id"] = str(user["_id"])
    return user