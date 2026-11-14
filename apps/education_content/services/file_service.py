
import logging

from django.db import transaction

logger = logging.getLogger(__name__)


def schedule_file_deletion(*, storage, file_name: str) -> None:
    """
    Delete a media file after transaction commit,
    only if no education content object references it.
    """
    if not file_name:
        return

    def delete_file():
        try:
            # Import here to avoid circular imports.
            from apps.education_content.models import (
                HybridTeacher,
                UniversityStep,
            )

            is_referenced = (
                HybridTeacher.objects.filter(
                    image=file_name,
                ).exists()
                or UniversityStep.objects.filter(
                    image=file_name,
                ).exists()
            )

            if is_referenced:
                return

            storage.delete(file_name)

        except Exception:
            logger.exception(
                "Failed to delete education content media file: %s",
                file_name,
            )

    transaction.on_commit(delete_file)



def delete_file_if_unreferenced(*, storage, file_name: str) -> None:
    """
    Delete a newly uploaded file after rollback,
    only if no education content object references it.
    """
    if not file_name:
        return

    try:
        from apps.education_content.models import (
            HybridTeacher,
            UniversityStep,
        )

        is_referenced = (
            HybridTeacher.objects.filter(
                image=file_name,
            ).exists()
            or UniversityStep.objects.filter(
                image=file_name,
            ).exists()
        )

        if not is_referenced:
            storage.delete(file_name)

    except Exception:
        logger.exception(
            "Failed to cleanup education content media file: %s",
            file_name,
        )
