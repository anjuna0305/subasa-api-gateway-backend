from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from auth import AdminUser, AnyUser, CurrentUser
from database import get_db
from models import Service
from schemas import ServiceCreate, ServiceOut

router = APIRouter(prefix="/services", tags=["services"])


@router.post("", response_model=ServiceOut, status_code=201)
async def create_service(
    payload: ServiceCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    service = Service(
        service_key=payload.service_key,
        service_name=payload.service_name,
        base_url=payload.base_url,
        response_type=payload.response_type,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.get("/{service_id}", response_model=ServiceOut)
async def get_service(
    service_id: int,
    current_user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "service", "message": "Service not found."}],
        )
    return service


@router.get("", response_model=list[ServiceOut])
async def list_services(
    current_user: AnyUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Service).order_by(Service.service_name.asc())
    )
    return result.scalars().all()
