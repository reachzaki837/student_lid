from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path
from pymongo.errors import PyMongoError
from app.routers import auth, dashboard, assessment
from app.db.mongo import init_db
from app.core.config import settings

# Lifespan event to start MongoDB
@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.db_ready = False

    # Fail fast in production-like environments when secret configuration is unsafe.
    settings.validate_runtime_secrets()

    try:
        database_url = os.getenv("DATABASE_URL", "")
        running_on_vercel = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))

        # On Vercel, localhost DB URL is invalid. Do not crash the whole app on startup.
        if running_on_vercel and (not database_url or "localhost" in database_url):
            print("Skipping MongoDB init on Vercel: DATABASE_URL is not configured.")
        else:
            await init_db()
            application.state.db_ready = True
            print("Connected to MongoDB!")
    except (PyMongoError, RuntimeError, ValueError, OSError) as exc:
        print(f"MongoDB initialization failed: {exc}")
    yield

app = FastAPI(title="Student Learning Tool", lifespan=lifespan)

static_dir = Path(__file__).resolve().parent / "app" / "static"
if static_dir.exists() and static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(assessment.router)

@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")
