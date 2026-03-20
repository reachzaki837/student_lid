from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from app.routers import auth, dashboard, assessment
from app.db.mongo import init_db

# Lifespan event to start MongoDB
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("Connected to MongoDB!")
    yield

app = FastAPI(title="Student Learning Tool", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(assessment.router)

@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")