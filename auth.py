from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import JWT_SECRET
from models import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


@dataclass
class CurrentUser:
    id: int
    email: str
    role: UserRole


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> CurrentUser:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id: int | None = payload.get("sub")
        email: str | None = payload.get("email")
        role_str: str | None = payload.get("role")
        if user_id is None or email is None or role_str is None:
            raise exc
        role = UserRole(role_str)
    except (jwt.InvalidTokenError, ValueError):
        raise exc
    return CurrentUser(id=user_id, email=email, role=role)


def require_role(*allowed_roles: UserRole):
    async def _guard(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _guard


AdminUser = Annotated[CurrentUser, Depends(require_role(UserRole.admin))]
AnyUser = Annotated[CurrentUser, Depends(get_current_user)]
