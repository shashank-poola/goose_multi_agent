"""
FastAPI dependencies.

Auth: NextAuth generates a JWT signed with NEXTAUTH_SECRET (HS256).
      Frontend sends it as Bearer token. Backend verifies + upserts user.

NextAuth config required (auth.config.ts):
    jwt: { encode: async ({ secret, token }) => jwt.sign(token, secret, { algorithm: "HS256" }) }
"""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.exceptions import AuthError
from backend.db.engine import get_db
from backend.db.models import User

_bearer = HTTPBearer(auto_error=True)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.nextauth_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError as exc:
        raise AuthError(str(exc))


async def _upsert_user(payload: dict, db: AsyncSession) -> User:
    email: str = payload.get("email", "")
    provider: str = payload.get("provider", "unknown")
    provider_id: str = payload.get("sub", "")

    if not email:
        raise AuthError("JWT missing email")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            name=payload.get("name"),
            avatar_url=payload.get("picture"),
            provider=provider,
            provider_id=provider_id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Keep name/avatar in sync with latest OAuth data
        user.name = payload.get("name", user.name)
        user.avatar_url = payload.get("picture", user.avatar_url)
        await db.commit()

    return user


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = _decode_token(creds.credentials)
        return await _upsert_user(payload, db)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


# Convenience alias for route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
