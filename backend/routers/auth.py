from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response
from google.auth.transport import requests as grequests
from google.oauth2 import id_token as google_id_token
from jose import JWTError
from pydantic import BaseModel, EmailStr

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
_SECURE = settings.ENVIRONMENT == "production"


class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    company_name: str


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class GoogleBody(BaseModel):
    id_token: str


def _set_refresh(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


@router.post("/register", status_code=201)
async def register(body: RegisterBody, response: Response):
    db = get_db()
    if await db.users.find_one({"email": body.email}):
        raise HTTPException(400, "Email already registered")

    company_id = str(
        (await db.companies.insert_one({
            "name": body.company_name,
            "created_at": datetime.now(timezone.utc),
        })).inserted_id
    )
    user_id = str(
        (await db.users.insert_one({
            "email": body.email,
            "password_hash": hash_password(body.password),
            "company_id": company_id,
            "auth_provider": "local",
            "created_at": datetime.now(timezone.utc),
        })).inserted_id
    )

    _set_refresh(response, create_refresh_token(user_id, company_id))
    return {"access_token": create_access_token(user_id, company_id), "token_type": "bearer"}


@router.post("/login")
async def login(body: LoginBody, response: Response):
    db = get_db()
    user = await db.users.find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    uid, cid = str(user["_id"]), user["company_id"]
    _set_refresh(response, create_refresh_token(uid, cid))
    return {"access_token": create_access_token(uid, cid), "token_type": "bearer"}


@router.post("/refresh")
async def refresh(
    response: Response,
    token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if not token:
        raise HTTPException(401, "Missing refresh token")
    try:
        payload = decode_token(token, "refresh")
    except JWTError:
        raise HTTPException(401, "Invalid or expired refresh token")

    uid, cid = payload["sub"], payload["company_id"]
    _set_refresh(response, create_refresh_token(uid, cid))
    return {"access_token": create_access_token(uid, cid), "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(REFRESH_COOKIE)
    return {"detail": "Logged out"}


@router.post("/google", status_code=201)
async def google_auth(body: GoogleBody, response: Response):
    try:
        info = google_id_token.verify_oauth2_token(
            body.id_token,
            grequests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(401, "Invalid Google token")

    email = info["email"]
    db = get_db()
    user = await db.users.find_one({"email": email})

    if user:
        uid, cid = str(user["_id"]), user["company_id"]
    else:
        # First Google login — create company + user.
        cid = str(
            (await db.companies.insert_one({
                "name": info.get("name", email.split("@")[0]),
                "created_at": datetime.now(timezone.utc),
            })).inserted_id
        )
        uid = str(
            (await db.users.insert_one({
                "email": email,
                "password_hash": None,
                "company_id": cid,
                "auth_provider": "google",
                "created_at": datetime.now(timezone.utc),
            })).inserted_id
        )

    _set_refresh(response, create_refresh_token(uid, cid))
    return {"access_token": create_access_token(uid, cid), "token_type": "bearer"}