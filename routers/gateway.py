import httpx
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api_key_validator import validate_api_key
from database import get_db
from models import UsageLog

router = APIRouter(prefix="/api", tags=["gateway"])

_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    return _http_client


@router.api_route(
    "/{service_key}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def gateway_proxy(
    service_key: str,
    path: str,
    request: Request,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    validation = await validate_api_key(db, x_api_key, service_key)

    target_url = f"{validation.service.base_url.rstrip('/')}/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    client = _get_http_client()

    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "x-api-key", "content-length")
    }

    upstream_resp = await client.request(
        method=request.method,
        url=target_url,
        content=body,
        headers=headers,
    )

    tokens_used = int(upstream_resp.headers.get("X-Tokens-Used", 1))

    log = UsageLog(
        api_key_id=validation.api_key.id,
        service_id=validation.service.id,
        tokens_used=tokens_used,
        status="success" if upstream_resp.is_success else "error",
    )
    db.add(log)
    await db.commit()

    return StreamingResponse(
        content=iter([upstream_resp.content]),
        status_code=upstream_resp.status_code,
        media_type=upstream_resp.headers.get("content-type"),
    )
