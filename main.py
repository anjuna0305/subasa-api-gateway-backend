from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import engine
from models import Base
from routers.api_keys import router as api_keys_router
from routers.gateway import _get_http_client, router as gateway_router
from routers.services import router as services_router
from routers.usage import router as usage_router
from routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    client = _get_http_client()
    await client.aclose()
    await engine.dispose()


app = FastAPI(title="Subasa API Example", lifespan=lifespan)

app.include_router(users_router)
app.include_router(api_keys_router)
app.include_router(services_router)
app.include_router(usage_router)
app.include_router(gateway_router)
