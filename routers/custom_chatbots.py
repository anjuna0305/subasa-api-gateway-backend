from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic_core.core_schema import CustomErrorSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.operators import or_

from auth import AdminUser, AnyUser, CurrentUser
from database import get_db
from models import ApiKey, CustomChatbot, User
from schemas import ApiKeyCreate, ApiKeyOut, CustomChatbotCreate, CustomChatbotOut

router = APIRouter(prefix="/custom-chatbots", tags=["custom-chatbots"])


@router.post("", response_model=CustomChatbotOut, status_code=201)
async def create_custom_chatbot(
    payload: CustomChatbotCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(
        select(CustomChatbot).where(
            or_(
                CustomChatbot.chatbot_name == payload.chatbot_name,
                CustomChatbot.url_path == payload.url_path,
            )
        )
    )

    if existing:
        field = (
            "chatbot_name"
            if existing.chatbot_name == payload.chatbot_name
            else "url_path"
        )
        message = (
            "Chatbot name already exists"
            if existing.chatbot_name == payload.chatbot_name
            else "URL path already exists"
        )

        raise HTTPException(
            status_code=409, detail=[{"field": field, "message": message}]
        )

    custom_chatbot = CustomChatbot(
        chatbot_name=payload.chatbot_name,
        description=payload.description,
        hero_image="random bulshit image path for not",
        url_path=payload.url_path,
        retrieval_key="random uuid",
        file_path="random_file_path",
    )

    db.add(custom_chatbot)
    await db.commit()
    await db.refresh(custom_chatbot)
    return custom_chatbot


# todo change this
@router.get("/{api_key_id}", response_model=ApiKeyOut)
async def get_api_key(
    api_key_id: int,
    db: AsyncSession = Depends(get_db),
):
    api_key = await db.get(ApiKey, api_key_id)
    if not api_key:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "api_key", "message": "API key not found."}],
        )
    return api_key


@router.get("/by-url-path/{url_path}", response_model=CustomChatbotOut)
async def get_chabot_by_url_path(
    url_path: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomChatbot).where(CustomChatbot.url_path == url_path)
    )
    custom_chatbot = result.scalar_one_or_none()
    if not custom_chatbot:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "custom_chatbot", "message": "Chat bot not found."}],
        )
    return custom_chatbot


@router.get("", response_model=list[CustomChatbotOut])
async def list_custom_chatbot(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomChatbot).order_by(CustomChatbot.created_at.desc())
    )
    return result.scalars().all()
