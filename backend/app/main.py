import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# 统一日志格式：为所有 logger（含 uvicorn）加上时间戳
# ------------------------------------------------------------------
_LOG_FMT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=_LOG_FMT,
    datefmt=_LOG_DATEFMT,
    force=True,
)

# uvicorn 自建 handler 不走 root logger，在 startup 事件中覆盖（import 时 handler 尚未创建）
_formatter = logging.Formatter(_LOG_FMT, datefmt=_LOG_DATEFMT)


def _unify_uvicorn_log_format() -> None:
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        for h in uv_logger.handlers:
            h.setFormatter(_formatter)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db.database import init_db
from app.routers.stock_router import router as stock_router
from app.routers.agent_router import router as agent_router
from app.routers.snapshot_router import router as snapshot_router
from app.routers.data_source_router import router as data_source_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: 替代已弃用的 on_event('startup')。"""
    init_db()
    _unify_uvicorn_log_format()
    yield


app = FastAPI(title="Stock Foker API", version="0.1.0", lifespan=lifespan)

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 禁止浏览器缓存 API 响应 ----
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

app.add_middleware(NoCacheMiddleware)

app.include_router(stock_router)
app.include_router(agent_router)
app.include_router(snapshot_router)
app.include_router(data_source_router)


@app.get("/")
def root():
    return {"message": "Stock Foker API is running"}
