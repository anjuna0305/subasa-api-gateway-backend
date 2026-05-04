from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import ForeignKey, String, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DATABASE_URL = "mysql+aiomysql://subasa:your_password@localhost:3306/subasa"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,  # set True to log SQL queries
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep ORM objects usable after commit
)


# Dependency — yields a session, always closes it
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    stock: Mapped[int] = mapped_column(default=0)
    category: Mapped[str] = mapped_column(String(100), nullable=True)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped["User"] = relationship(back_populates="api_keys")
    service_usages: Mapped[list["ServiceUsage"]] = relationship(back_populates="api_key")
    usage_logs: Mapped[list["UsageLog"]] = relationship(back_populates="api_key")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    service_usages: Mapped[list["ServiceUsage"]] = relationship(back_populates="service")
    usage_logs: Mapped[list["UsageLog"]] = relationship(back_populates="service")


class ServiceUsage(Base):
    __tablename__ = "service_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    usage_limit: Mapped[int] = mapped_column(nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    api_key: Mapped["ApiKey"] = relationship(back_populates="service_usages")
    service: Mapped["Service"] = relationship(back_populates="service_usages")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    tokens_used: Mapped[int] = mapped_column(nullable=False)
    requested_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    api_key: Mapped["ApiKey"] = relationship(back_populates="usage_logs")
    service: Mapped["Service"] = relationship(back_populates="usage_logs")


class UserCreate(BaseModel):
    name: str
    email: EmailStr


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    key_hash: str
    label: str | None = None
    expires_at: datetime | None = None


class ApiKeyOut(BaseModel):
    id: int
    user_id: int
    label: str | None = None
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class ServiceCreate(BaseModel):
    service_name: str
    base_url: str


class ServiceOut(BaseModel):
    id: int
    service_name: str
    base_url: str
    is_active: bool

    model_config = {"from_attributes": True}


class ServiceUsageCreate(BaseModel):
    api_key_id: int
    service_id: int
    usage_limit: int
    expires_at: datetime | None = None


class ServiceUsageOut(BaseModel):
    id: int
    api_key_id: int
    service_id: int
    usage_limit: int
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class UsageLogCreate(BaseModel):
    api_key_id: int
    service_id: int
    tokens_used: int
    status: str


class UsageLogOut(BaseModel):
    id: int
    api_key_id: int
    service_id: int
    tokens_used: int
    requested_at: datetime
    status: str

    model_config = {"from_attributes": True}


class CurrentUsageOut(BaseModel):
    api_key_id: int
    service_id: int
    total_tokens_used: int
    request_count: int

    model_config = {"from_attributes": True}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Subasa API Example", lifespan=lifespan)


@app.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(name=payload.name, email=payload.email)
    db.add(user)
    await db.commit()
    await db.refresh(user)  # reload to get DB-generated id / created_at
    return user


@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users", response_model=list[UserOut])
async def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"limit": limit, "offset": offset},
    )
    rows = result.mappings().all()
    return [UserOut(**row) for row in rows]


@app.get("/products", response_model=list[ProductOut])
async def list_products(
    category: str | None = Query(None),
    min_price: float = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """Filtered query using raw SQL with bound parameters (safe from injection)."""
    query = """
        SELECT * FROM products
        WHERE price >= :min_price
          AND (:category IS NULL OR category = :category)
        ORDER BY name
    """
    result = await db.execute(
        text(query), {"min_price": min_price, "category": category}
    )
    return [ProductOut(**row) for row in result.mappings().all()]


@app.get("/products/low-stock", response_model=list[ProductOut])
async def low_stock_products(
    threshold: int = Query(5),
    db: AsyncSession = Depends(get_db),
):
    """Simple threshold query."""
    result = await db.execute(
        text("SELECT * FROM products WHERE stock <= :threshold ORDER BY stock ASC"),
        {"threshold": threshold},
    )
    return [ProductOut(**row) for row in result.mappings().all()]


@app.get("/stats/products")
async def product_stats(db: AsyncSession = Depends(get_db)):
    """Aggregate query — returns raw dict, no ORM model needed."""
    result = await db.execute(
        text("""
        SELECT
            category,
            COUNT(*)        AS total_products,
            AVG(price)      AS avg_price,
            SUM(stock)      AS total_stock
        FROM products
        GROUP BY category
        ORDER BY total_products DESC
    """)
    )
    rows = result.mappings().all()
    return [dict(row) for row in rows]


# uvicorn main:app --reload --host 0.0.0.0 --port 8000
