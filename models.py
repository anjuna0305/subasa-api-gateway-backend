import enum
from datetime import datetime, timezone

from sqlalchemy import Enum, ForeignKey, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    admin = "admin"
    general_user = "general_user"


class ResponseType(str, enum.Enum):
    short = "short"
    long = "long"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.general_user
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped["User"] = relationship(back_populates="api_keys")
    service_usages: Mapped[list["ServiceUsage"]] = relationship(
        back_populates="api_key"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(back_populates="api_key")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    service_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    response_type: Mapped[ResponseType] = mapped_column(
        Enum(ResponseType), nullable=False, default=ResponseType.short
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    service_usages: Mapped[list["ServiceUsage"]] = relationship(
        back_populates="service"
    )
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
    requested_at: Mapped[datetime] = mapped_column(default=_utcnow)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    api_key: Mapped["ApiKey"] = relationship(back_populates="usage_logs")
    service: Mapped["Service"] = relationship(back_populates="usage_logs")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), nullable=False, default=TaskStatus.pending
    )
    request_method: Mapped[str] = mapped_column(String(10), nullable=False)
    request_path: Mapped[str] = mapped_column(String(500), nullable=False)
    request_query: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    request_headers: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    request_body: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    response_status_code: Mapped[int | None] = mapped_column(nullable=True)
    response_body: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    response_content_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tokens_used: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    api_key: Mapped["ApiKey"] = relationship()
    service: Mapped["Service"] = relationship()
