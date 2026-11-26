import logging

from celery import shared_task

from apps.universities.services.media_lifecycle_service import (
    MediaLifecycleService,
)

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.universities.tasks.retry_failed_university_media_cleanups",
    ignore_result=True,
)
def retry_failed_university_media_cleanups(limit: int = 100) -> int:
    """Muvaffaqiyatsiz media storage tozalash vazifalarini qayta ishlaydi."""

    processed = MediaLifecycleService.retry_failed_cleanups(limit=limit)
    stats = MediaLifecycleService.get_cleanup_backlog_stats()
    if stats["failed"] > 0 or stats["pending"] > 0:
        logger.warning(
            "Periodic media cleanup retry status: processed=%s failed_remaining=%s pending_remaining=%s",
            processed,
            stats["failed"],
            stats["pending"],
        )
    return processed
