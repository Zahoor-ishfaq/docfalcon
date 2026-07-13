from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=3000,  # fail fast instead of hanging 30s
        )
    return _client


def get_db():
    return get_client()["docfalcon"]


async def ping_db() -> tuple[bool, str | None]:
    try:
        await get_client().admin.command("ping")
        return True, None
    except Exception as e:
        return False, str(e)
    
async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None