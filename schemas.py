from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from models import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.general_user

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be empty")
        if len(v) > 100:
            raise ValueError("name must be at most 100 characters")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("password must be at most 128 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one digit")
        return v


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
