from beanie import init_beanie
from app.core.config import settings
from app.models.user import (
    User, Assessment, Class, Enrollment, Material
)

async def init_db():
    connection_string = settings.DATABASE_URL.rstrip("/")
    # Append the database name to the connection string
    connection_string = f"{connection_string}/{settings.DATABASE_NAME}"

    await init_beanie(
        connection_string=connection_string,
        document_models=[
            User, Assessment, Class, Enrollment, Material
        ]
    )