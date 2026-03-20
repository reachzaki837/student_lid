# test_db.py
import asyncio
from app.db.session import engine
from app.models.base import Base
from app.models import user, academic, assessment 

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())