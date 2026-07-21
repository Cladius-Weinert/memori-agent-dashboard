"""Auth router: register, login, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas import LoginIn, TokenOut, UserCreate, UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: AsyncSession = Depends(get_db)) -> User:
    existing = await session.scalar(select(User).where(User.email == data.email))
    if existing:
        raise HTTPException(status_code=400, detail="email already registered")
    user = User(email=data.email, full_name=data.full_name, hashed_password=hash_password(data.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    user = await session.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="inactive user")
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(session: AsyncSession = Depends(get_db), token: str = None) -> User:
    # Simplified: token validation done via dependency in routes
    # This is a placeholder - actual auth handled in each route
    raise HTTPException(status_code=401, detail="Not implemented here")


@router.get("/me", response_model=UserRead)
async def me(
    authorization: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> User:
    # NOTE: real impl would decode JWT from Authorization header
    # For now, return a dummy or raise - placeholder
    raise HTTPException(status_code=501, detail="me endpoint requires JWT dependency injection setup")
