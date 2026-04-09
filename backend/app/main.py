from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db
from app.routers.stock_router import router as stock_router
from app.routers.agent_router import router as agent_router
from app.routers.snapshot_router import router as snapshot_router

app = FastAPI(title="Stock Foker API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock_router)
app.include_router(agent_router)
app.include_router(snapshot_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Stock Foker API is running"}
