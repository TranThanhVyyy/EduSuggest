import asyncio

from sqlalchemy.exc import SQLAlchemyError

from config.database import SessionLocal
from repository.token_repository import delete_expired
from utils.logger import logger

CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60


def cleanup_expired_tokens() -> int:
    with SessionLocal.begin() as db:
        return delete_expired(db)


async def cleanup_expired_tokens_periodically() -> None:
    while True:
        try:
            deleted_count = await asyncio.to_thread(cleanup_expired_tokens)
        except SQLAlchemyError as exc:
            logger.error(
                "Expired token cleanup failed (%s)",
                type(exc).__name__,
            )
        else:
            if deleted_count:
                logger.info("Removed %d expired token blacklist records", deleted_count)
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
