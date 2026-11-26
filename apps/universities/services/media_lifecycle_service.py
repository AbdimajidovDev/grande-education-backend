import hashlib
import logging

from django.core.files.storage import default_storage
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.universities.models import (
    MediaCleanupTask,
    MediaStorageLock,
    UniversityMedia,
)

logger = logging.getLogger(__name__)


class MediaLifecycleService:
    """Media fayllariga bo'lgan reference'lar va storage tozalash siklini boshqaradi."""

    @staticmethod
    def _advisory_lock_key(file_path: str) -> int:
        digest = hashlib.sha256(file_path.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)

    @staticmethod
    def acquire_storage_key_lock(file_path: str) -> None:
        """Berilgan storage path bo'yicha transaction-darajali eksklyuziv lock oladi."""

        if not file_path:
            return

        if connection.vendor == "postgresql":
            lock_key = MediaLifecycleService._advisory_lock_key(file_path)
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_key])

        try:
            with transaction.atomic():
                MediaStorageLock.objects.get_or_create(file_path=file_path)
        except IntegrityError:
            pass

        MediaStorageLock.objects.select_for_update().filter(
            file_path=file_path,
        ).first()

    @staticmethod
    def is_storage_key_referenced(file_path: str) -> bool:
        """Loyiha bo'yicha barcha fayl maydonlarida shu storage key ishlatilayotganini tekshiradi."""

        if not file_path:
            return False

        from apps.education_content.models import (
            HybridTeacher,
            UniversityStep,
        )
        from apps.partners.models.partner import Partner
        from apps.programs.models.program import Program
        from apps.teachers.models.teacher import Teacher

        return (
            UniversityMedia.objects.filter(file=file_path).exists()
            or Partner.objects.filter(logo=file_path).exists()
            or Program.objects.filter(image=file_path).exists()
            or Teacher.objects.filter(photo=file_path).exists()
            or HybridTeacher.objects.filter(image=file_path).exists()
            or UniversityStep.objects.filter(image=file_path).exists()
        )

    @staticmethod
    def register_reference(*, file_path: str) -> None:
        """Storage key lock ostida kutilayotgan cleanup vazifalarini bekor qiladi."""

        if not file_path:
            return

        MediaLifecycleService.acquire_storage_key_lock(file_path)

        MediaCleanupTask.objects.select_for_update().filter(
            file_path=file_path,
            status__in=[
                MediaCleanupTask.Status.PENDING,
                MediaCleanupTask.Status.FAILED,
            ],
        ).update(
            status=MediaCleanupTask.Status.CANCELLED,
            updated_at=timezone.now(),
        )

    @staticmethod
    def schedule_cleanup(*, file_paths: list[str]) -> list:
        """Storage key lock ostida reference qolmagan fayllarni commit'dan keyin o'chirishga qo'yadi."""

        unique_paths = sorted(set(path for path in file_paths if path))
        if not unique_paths:
            return []

        task_ids = []
        for file_path in unique_paths:
            MediaLifecycleService.acquire_storage_key_lock(file_path)

            if MediaLifecycleService.is_storage_key_referenced(file_path):
                continue

            task = MediaCleanupTask.objects.create(
                file_path=file_path,
                status=MediaCleanupTask.Status.PENDING,
            )
            task_ids.append(task.pk)

        if task_ids:
            transaction.on_commit(
                lambda ids=list(task_ids): MediaLifecycleService.execute_cleanup_tasks(ids)
            )

        return task_ids

    @staticmethod
    def execute_cleanup_tasks(task_ids: list) -> None:
        """Rejalashtirilgan cleanup vazifalarini xavfsiz bajaradi."""

        for task_id in task_ids:
            MediaLifecycleService._execute_single_task(task_id)

    @staticmethod
    def _execute_single_task(task_id) -> None:
        with transaction.atomic():
            file_path = (
                MediaCleanupTask.objects
                .filter(pk=task_id)
                .values_list("file_path", flat=True)
                .first()
            )
            if not file_path:
                return

            # Lock tartibi: avval MediaStorageLock(file_path), so'ng MediaCleanupTask(pk).
            MediaLifecycleService.acquire_storage_key_lock(file_path)

            task = (
                MediaCleanupTask.objects
                .select_for_update()
                .filter(
                    pk=task_id,
                    status__in=[
                        MediaCleanupTask.Status.PENDING,
                        MediaCleanupTask.Status.FAILED,
                    ],
                )
                .first()
            )
            if task is None:
                return

            if MediaLifecycleService.is_storage_key_referenced(task.file_path):
                task.status = MediaCleanupTask.Status.CANCELLED
                task.save(update_fields=["status", "updated_at"])
                return

            try:
                default_storage.delete(task.file_path)
            except Exception as exc:
                logger.exception(
                    "Failed to delete university media file from storage: %s (task_id=%s)",
                    task.file_path,
                    task.pk,
                )
                task.status = MediaCleanupTask.Status.FAILED
                task.attempts += 1
                task.last_error = exc.__class__.__name__
                task.save(
                    update_fields=[
                        "status",
                        "attempts",
                        "last_error",
                        "updated_at",
                    ]
                )
                return

            task.status = MediaCleanupTask.Status.COMPLETED
            task.attempts += 1
            task.last_error = ""
            task.completed_at = timezone.now()
            task.save(
                update_fields=[
                    "status",
                    "attempts",
                    "last_error",
                    "completed_at",
                    "updated_at",
                ]
            )

    @staticmethod
    def get_cleanup_backlog_stats() -> dict[str, int]:
        """MediaCleanupTask holatlari bo'yicha kuzatuv statistikasi."""

        return {
            "pending": MediaCleanupTask.objects.filter(
                status=MediaCleanupTask.Status.PENDING
            ).count(),
            "failed": MediaCleanupTask.objects.filter(
                status=MediaCleanupTask.Status.FAILED
            ).count(),
            "completed": MediaCleanupTask.objects.filter(
                status=MediaCleanupTask.Status.COMPLETED
            ).count(),
            "cancelled": MediaCleanupTask.objects.filter(
                status=MediaCleanupTask.Status.CANCELLED
            ).count(),
        }

    @staticmethod
    def retry_failed_cleanups(*, limit: int = 100) -> int:
        """Muvaffaqiyatsiz yoki kutilayotgan cleanup vazifalarini qayta ishlaydi."""

        task_ids = list(
            MediaCleanupTask.objects
            .filter(
                status__in=[
                    MediaCleanupTask.Status.FAILED,
                    MediaCleanupTask.Status.PENDING,
                ]
            )
            .order_by("created_at")
            .values_list("id", flat=True)[:limit]
        )
        if not task_ids:
            return 0

        MediaLifecycleService.execute_cleanup_tasks(task_ids)

        outcomes = dict.fromkeys(
            (
                MediaCleanupTask.Status.COMPLETED,
                MediaCleanupTask.Status.CANCELLED,
                MediaCleanupTask.Status.FAILED,
                MediaCleanupTask.Status.PENDING,
            ),
            0,
        )
        for row_status in MediaCleanupTask.objects.filter(
            id__in=task_ids
        ).values_list("status", flat=True):
            outcomes[row_status] = outcomes.get(row_status, 0) + 1

        remaining_failed = MediaCleanupTask.objects.filter(
            status=MediaCleanupTask.Status.FAILED
        ).count()

        if outcomes[MediaCleanupTask.Status.FAILED] > 0 or remaining_failed > 0:
            logger.warning(
                "Media cleanup retry finished with remaining failures: "
                "selected=%s completed=%s cancelled=%s still_failed=%s remaining_failed_total=%s",
                len(task_ids),
                outcomes[MediaCleanupTask.Status.COMPLETED],
                outcomes[MediaCleanupTask.Status.CANCELLED],
                outcomes[MediaCleanupTask.Status.FAILED],
                remaining_failed,
            )
        else:
            logger.info(
                "Media cleanup retry finished cleanly: selected=%s completed=%s cancelled=%s",
                len(task_ids),
                outcomes[MediaCleanupTask.Status.COMPLETED],
                outcomes[MediaCleanupTask.Status.CANCELLED],
            )

        return len(task_ids)
