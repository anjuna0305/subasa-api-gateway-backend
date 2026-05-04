from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import AdminUser, AnyUser, CurrentUser
from database import get_db
from models import ApiKey, Service, ServiceUsage, UsageLog
from schemas import (
    CurrentUsageOut,
    ServiceUsageCreate,
    ServiceUsageOut,
    UsageLogCreate,
    UsageLogOut,
)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post("/service-usage", response_model=ServiceUsageOut, status_code=201)
async def create_service_usage(
    payload: ServiceUsageCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    api_key = await db.get(ApiKey, payload.api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    service = await db.get(Service, payload.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service_usage = ServiceUsage(
        api_key_id=payload.api_key_id,
        service_id=payload.service_id,
        usage_limit=payload.usage_limit,
        expires_at=payload.expires_at,
    )
    db.add(service_usage)
    await db.commit()
    await db.refresh(service_usage)
    return service_usage


@router.post("/logs", response_model=UsageLogOut, status_code=201)
async def create_usage_log(
    payload: UsageLogCreate,
    current_user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    api_key = await db.get(ApiKey, payload.api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    service = await db.get(Service, payload.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    log = UsageLog(
        api_key_id=payload.api_key_id,
        service_id=payload.service_id,
        tokens_used=payload.tokens_used,
        status=payload.status,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/current/{api_key_id}/{service_id}", response_model=CurrentUsageOut)
async def get_current_usage(
    api_key_id: int,
    service_id: int,
    current_user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            SELECT
                api_key_id,
                service_id,
                SUM(tokens_used) AS total_tokens_used,
                COUNT(*) AS request_count
            FROM usage_logs
            WHERE api_key_id = :api_key_id AND service_id = :service_id
            GROUP BY api_key_id, service_id
        """),
        {"api_key_id": api_key_id, "service_id": service_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No usage data found")
    return CurrentUsageOut(**row)
