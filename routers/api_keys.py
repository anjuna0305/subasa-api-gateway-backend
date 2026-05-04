from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from auth import AdminUser, AnyUser, CurrentUser
from database import get_db
from models import ApiKey, User
from schemas import ApiKeyCreate, ApiKeyOut

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("/users/{user_id}/api-keys", response_model=ApiKeyOut, status_code=201)
async def create_api_key(
    user_id: int,
    payload: ApiKeyCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    api_key = ApiKey(
        user_id=user_id,
        key_hash=payload.key_hash,
        label=payload.label,
        expires_at=payload.expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.get("/{api_key_id}", response_model=ApiKeyOut)
async def get_api_key(
    api_key_id: int,
    current_user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    api_key = await db.get(ApiKey, api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return api_key


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()
