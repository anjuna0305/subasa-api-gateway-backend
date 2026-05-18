import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.operators import or_

from config import CUSTOM_CHATBOT_SERVICE_URL, FILE_UPLOAD_DIR, IMAGE_UPLOAD_DIR
from database import get_db
from models import ApiKey, CustomChatbot
from schemas import (
    ApiKeyOut,
    CustomChatbotCreate,
    CustomChatbotMessageRequest,
    CustomChatbotMessageResponse,
    CustomChatbotOut,
)

ALLOWED_IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png"}
ALLOWED_FILE_EXTENSIONS = {".txt", ".pdf"}
MIME_TYPES = {
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}

router = APIRouter(prefix="/custom-chatbots", tags=["custom-chatbots"])


@router.post("/api/{url_path}", response_model=CustomChatbotMessageResponse)
async def chat_with_custom_chatbot(
    url_path: str,
    payload: CustomChatbotMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomChatbot).where(CustomChatbot.url_path == url_path)
    )
    custom_chatbot = result.scalar_one_or_none()
    if not custom_chatbot:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "url_path", "message": "Chatbot not found."}],
        )

    from routers._http import get_http_client

    client = get_http_client()

    # forward_url = f"{CUSTOM_CHATBOT_SERVICE_URL.rstrip('/')}/api/{url_path}"
    forward_url = CUSTOM_CHATBOT_SERVICE_URL
    forward_payload = {
        "message": payload.message,
        "retrieval_key": custom_chatbot.retrieval_key,
        "file_path": custom_chatbot.file_path,
    }

    upstream_resp = await client.post(
        forward_url,
        json=forward_payload,
    )
    upstream_resp.raise_for_status()

    data = upstream_resp.json()
    return CustomChatbotMessageResponse(
        response=data.get("response", data.get("message", ""))
    )


def _validate_image_extension(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=[
                {
                    "field": "file",
                    "message": "Only jpeg and png images are allowed",
                }
            ],
        )
    return ext


def _validate_file_extension(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=[
                {
                    "field": "file",
                    "message": "Only text and pfg files are allowed",
                }
            ],
        )
    return ext


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
@router.get("/{chatbot_id}", response_model=CustomChatbotOut)
async def get_custom_chatbot(
    chatbot_id: int,
    db: AsyncSession = Depends(get_db),
):
    api_key = await db.get(CustomChatbot, chatbot_id)
    if not api_key:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "chatbot_id", "message": "Chatbot id not found."}],
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


@router.post("/publish/{chatbot_id}", response_model=CustomChatbotOut)
async def publish_chatbot(chatbot_id: int, db: AsyncSession = Depends(get_db)):
    chatbot = await db.get(CustomChatbot, chatbot_id)
    if not chatbot:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "chatbot_id", "message": "Chat bot not found."}],
        )

    chatbot.is_publish = True
    await db.commit()
    await db.refresh(chatbot)
    return chatbot


@router.post("/unpublish/{chatbot_id}", response_model=CustomChatbotOut)
async def unpublish_chatbot(chatbot_id: int, db: AsyncSession = Depends(get_db)):
    chatbot = await db.get(CustomChatbot, chatbot_id)
    if not chatbot:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "chatbot_id", "message": "Chat bot not found."}],
        )

    chatbot.is_publish = False
    await db.commit()
    await db.refresh(chatbot)
    return chatbot


@router.post("/{chatbot_id}/upload-image", response_model=CustomChatbotOut)
async def upload_chatbot_image(
    chatbot_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    chatbot = await db.get(CustomChatbot, chatbot_id)
    if not chatbot:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "chatbot_id", "message": "Custom chatbot not found."}],
        )

    ext = _validate_image_extension(file.filename or "")

    image_name = f"{uuid.uuid4().hex}{ext}"

    os.makedirs(IMAGE_UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(IMAGE_UPLOAD_DIR, image_name)

    if chatbot.hero_image:
        old_path = os.path.join(IMAGE_UPLOAD_DIR, chatbot.hero_image)
        if os.path.exists(old_path):
            os.remove(old_path)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    chatbot.hero_image = image_name
    await db.commit()
    await db.refresh(chatbot)
    return chatbot


@router.get("/images/{image_name}")
async def get_chatbot_image(image_name: str):
    ext = os.path.splitext(image_name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=[{"field": "image_name", "message": "Invalid image format."}],
        )

    file_path = os.path.join(IMAGE_UPLOAD_DIR, image_name)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=[{"field": "image_name", "message": "Image not found."}],
        )

    return FileResponse(file_path, media_type=MIME_TYPES.get(ext, "image/jpeg"))


@router.post("/{chatbot_id}/upload-file", response_model=CustomChatbotOut)
async def upload_chatbot_file(
    chatbot_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    chatbot = await db.get(CustomChatbot, chatbot_id)
    if not chatbot:
        raise HTTPException(
            status_code=404,
            detail=[{"field": "chatbot_id", "message": "Custom chatbot not found."}],
        )

    ext = _validate_file_extension(file.filename or "")

    file_name = f"{uuid.uuid4().hex}{ext}"

    os.makedirs(FILE_UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(FILE_UPLOAD_DIR, file_name)

    if chatbot.hero_image:
        old_path = os.path.join(FILE_UPLOAD_DIR, chatbot.file_path)
        if os.path.exists(old_path):
            os.remove(old_path)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    chatbot.file_path = file_name
    await db.commit()
    await db.refresh(chatbot)
    return chatbot
