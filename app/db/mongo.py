from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.user import User, Assessment, Class, Enrollment

async def init_db():
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    
    await init_beanie(
        database=client[settings.DATABASE_NAME],
        document_models=[
            User,
            Assessment,
            Class,
            Enrollment
        ]
    )