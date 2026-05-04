from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import AdminUser, AnyUser, CurrentUser
from config import JWT_EXPIRE_MINUTES, JWT_SECRET
from database import get_db
from models import User, UserRole
from schemas import TokenOut, UserCreate, UserLogin, UserOut

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    hashed = pwd_context.hash(payload.password)
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hashed,
        role=UserRole.general_user,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    hashed = pwd_context.hash(payload.password)
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hashed,
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expires = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    token = jwt.encode(
        {"sub": user.id, "email": user.email, "role": user.role.value, "exp": expires},
        JWT_SECRET,
        algorithm="HS256",
    )
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: AnyUser, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    current_user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
