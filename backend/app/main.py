import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, devices, management, users
from app.core.config import DEFAULT_SECRET_KEY, settings
from app.db.base import Base
from app.db.migrate_sqlite import ensure_sqlite_device_columns
from app.db.seed import demo_accounts_with_default_password, seed_database
from app.db.session import SessionLocal, engine
import app.models  # noqa: F401


# Log through uvicorn so warnings appear in its console output with the usual format
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
        logger.warning("SECRET_KEY is the built-in default; set a random value in backend/.env for production.")
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        ensure_sqlite_device_columns()
    db = SessionLocal()
    try:
        if settings.SEED_ON_STARTUP:
            seed_database(db)
        weak = demo_accounts_with_default_password(db)
        if weak:
            logger.warning("Demo accounts still use their default passwords: %s. Change or disable them.", ", ".join(weak))
    finally:
        db.close()
    yield


app = FastAPI(title="DeviceVault API", description="Mobile Device Inventory Management System", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(management.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
