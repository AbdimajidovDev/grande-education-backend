
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.deletion import ProtectedError

from django.utils import timezone
from apps.rbac.services.role_service import RoleService
from apps.notifications.services import event_notifications

from apps.universities.models import (
    University,
    UniversityAdmissionPeriod,
    UniversityAuditLog,
    UniversityMajor,
    UniversityMedia,
    UniversityRevision,
    UniversityTranslation,
    UniversityTranslationRevision,
)
from apps.universities.services.audit_log_service import AuditLogService
from apps.universities.services.exceptions import ResourceNotFoundError
from apps.universities.services.media_lifecycle_service import (
    MediaLifecycleService,
)


User = get_user_model()


class UniversityRevisionService:
    """Universitet umumiy ma'lumotlari revisionlarini boshqaradi."""

    @staticmethod
    def _ensure_permission(
        actor: User,
        permission: str,
        fallback_permissions: tuple[str, ...] = (),
    ) -> None:
        if (
                actor is None
                or not actor.is_authenticated
                or not actor.is_active
        ):
            raise PermissionDenied(
                "Bu amalni bajarish uchun faol foydalanuvchi "
                "bo'lishingiz kerak."
            )

        if actor.is_superuser:
            return

        actor_permissions = RoleService._get_actor_role_permissions(actor)
        required = (permission, *fallback_permissions)

        if not any(f"universities.{perm}" in actor_permissions for perm in required):
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
            )

    @staticmethod
    def _get_revision_for_update(
        revision_id,
        *,
        allow_archived_university: bool = False,
        not_found_exc=ValidationError,
    ) -> UniversityRevision:
        """University va revisionni yagona lock tartibida oladi."""

        university_id = (
            UniversityRevision.objects
            .filter(pk=revision_id)
            .values_list("university_id", flat=True)
            .first()
        )

        if university_id is None:
            raise not_found_exc("Universitet revisioni topilmadi.")

        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise not_found_exc("Universitet topilmadi.")

        if (
            not allow_archived_university
            and university.status == University.Status.ARCHIVED
        ):
            raise ValidationError(
                "Arxivlangan universitet revisionlarini boshqarish mumkin emas."
            )

        revision = (
            UniversityRevision.objects
            .select_for_update()
            .filter(
                pk=revision_id,
                university_id=university.pk,
            )
            .first()
        )

        if revision is None:
            raise not_found_exc("Universitet revisioni topilmadi.")

        revision.university = university

        return revision


    @staticmethod
    @transaction.atomic
    def create_revision(
        *,
        actor: User,
        university_id,
        city: str,
        country: str,
        city_native: str = "",
        chinese_name: str = "",
        established_year: int | None = None,
        students_count: int | None = None,
        international_students_count: int | None = None,
    ) -> UniversityRevision:
        """Universitet uchun yangi DRAFT revision yaratadi."""

        UniversityRevisionService._ensure_permission(
            actor,
            "change_university",
        )

        city = city.strip()
        country = country.strip()
        city_native = city_native.strip() if city_native else ""
        chinese_name = chinese_name.strip() if chinese_name else ""

        if not city:
            raise ValidationError({"city": "Shahar nomi kiritilishi shart."})

        if not country:
            raise ValidationError({"country": "Mamlakat nomi kiritilishi shart."})

        if established_year is not None and established_year <= 0:
            raise ValidationError({
                "established_year": "Tashkil topgan yil musbat son bo'lishi kerak."
            })

        if students_count is not None and students_count < 0:
            raise ValidationError({
                "students_count": "Talabalar soni manfiy bo'lishi mumkin emas."
            })

        if international_students_count is not None and international_students_count < 0:
            raise ValidationError({
                "international_students_count": "Xalqaro talabalar soni manfiy bo'lishi mumkin emas."
            })

        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise ValidationError("Universitet topilmadi.")

        if university.status == University.Status.ARCHIVED:
            raise ValidationError(
                "Arxivlangan universitet uchun yangi revision yaratish mumkin emas."
            )

        last_revision_number = (
            UniversityRevision.objects
            .filter(university=university)
            .order_by("-revision_number")
            .values_list("revision_number", flat=True)
            .first()
        )

        next_revision_number = (
            last_revision_number + 1
            if last_revision_number is not None
            else 1
        )

        try:
            return UniversityRevision.objects.create(
                university=university,
                revision_number=next_revision_number,
                city=city,
                country=country,
                city_native=city_native,
                chinese_name=chinese_name,
                established_year=established_year,
                students_count=students_count,
                international_students_count=international_students_count,
                status=UniversityRevision.Status.DRAFT,
                created_by=actor,
            )
        except IntegrityError as exc:
            raise ValidationError(
                "Revision yaratishda ma'lumotlar to'qnashuvi yuz berdi."
            ) from exc

    @staticmethod
    @transaction.atomic
    def update_revision(
        *,
        actor: User,
        revision_id,
        city: str | None = None,
        country: str | None = None,
        city_native: str | None = None,
        chinese_name: str | None = None,
        established_year: int | None = None,
        students_count: int | None = None,
        international_students_count: int | None = None,
    ) -> UniversityRevision:
        """Faqat DRAFT holatidagi revisionni tahrirlaydi."""

        UniversityRevisionService._ensure_permission(
            actor,
            "change_university",
        )

        revision = UniversityRevisionService._get_revision_for_update(
            revision_id
        )

        if revision.status != UniversityRevision.Status.DRAFT:
            raise ValidationError(
                "Faqat DRAFT holatidagi revisionni tahrirlash mumkin."
            )

        update_fields = []

        if city is not None:
            city = city.strip()
            if not city:
                raise ValidationError({"city": "Shahar nomi kiritilishi shart."})
            revision.city = city
            update_fields.append("city")

        if country is not None:
            country = country.strip()
            if not country:
                raise ValidationError({"country": "Mamlakat nomi kiritilishi shart."})
            revision.country = country
            update_fields.append("country")

        if city_native is not None:
            revision.city_native = city_native.strip()
            update_fields.append("city_native")

        if chinese_name is not None:
            revision.chinese_name = chinese_name.strip()
            update_fields.append("chinese_name")

        if established_year is not None:
            if established_year <= 0:
                raise ValidationError({
                    "established_year": "Tashkil topgan yil musbat son bo'lishi kerak."
                })
            revision.established_year = established_year
            update_fields.append("established_year")

        if students_count is not None:
            if students_count < 0:
                raise ValidationError({
                    "students_count": "Talabalar soni manfiy bo'lishi mumkin emas."
                })
            revision.students_count = students_count
            update_fields.append("students_count")

        if international_students_count is not None:
            if international_students_count < 0:
                raise ValidationError({
                    "international_students_count": "Xalqaro talabalar soni manfiy bo'lishi mumkin emas."
                })
            revision.international_students_count = international_students_count
            update_fields.append("international_students_count")

        if update_fields:
            update_fields.append("updated_at")
            revision.save(update_fields=update_fields)

        return revision



    @staticmethod
    @transaction.atomic
    def submit_for_review(
        *,
        actor: User,
        revision_id,
    ) -> UniversityRevision:
        """DRAFT revisionni ko‘rib chiqishga yuboradi."""

        UniversityRevisionService._ensure_permission(
            actor,
            "submit_review_university",
        )

        revision = UniversityRevisionService._get_revision_for_update(
            revision_id
        )

        if revision.status != UniversityRevision.Status.DRAFT:
            raise ValidationError(
                "Faqat DRAFT holatidagi revisionni ko‘rib chiqishga yuborish mumkin."
            )

        revision.status = UniversityRevision.Status.REVIEW
        revision.rejection_reason = ""
        revision.approved_by = None
        revision.approved_at = None

        revision.save(
            update_fields=[
                "status",
                "rejection_reason",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        event_notifications.notify_revision_submitted(
            kind=event_notifications.REVISION_UNIVERSITY,
            revision=revision,
            actor=actor,
        )

        return revision

    @staticmethod
    @transaction.atomic
    def approve_revision(*, actor: User, revision_id) -> UniversityRevision:
        UniversityRevisionService._ensure_permission(
            actor,
            "approve_university",
        )

        revision = UniversityRevisionService._get_revision_for_update(
            revision_id
        )

        if revision.status != UniversityRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi revisionni tasdiqlash mumkin."
            )

        if revision.approved_at is not None:
            raise ValidationError("Ushbu revision allaqachon tasdiqlangan.")

        revision.approved_by = actor
        revision.approved_at = timezone.now()

        revision.save(
            update_fields=[
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        event_notifications.notify_revision_approved(
            kind=event_notifications.REVISION_UNIVERSITY,
            revision=revision,
            actor=actor,
        )

        return revision

    @staticmethod
    @transaction.atomic
    def reject_revision(
            *,
            actor: User,
            revision_id,
            reason: str,
    ) -> UniversityRevision:
        UniversityRevisionService._ensure_permission(
            actor,
            "reject_university",
        )

        reason = reason.strip()

        if not reason:
            raise ValidationError({
                "reason": "Rad etish sababi kiritilishi shart."
            })

        revision = UniversityRevisionService._get_revision_for_update(
            revision_id
        )

        if revision.status != UniversityRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi revisionni rad etish mumkin."
            )

        revision.status = UniversityRevision.Status.DRAFT
        revision.rejection_reason = reason
        revision.approved_by = None
        revision.approved_at = None

        revision.save(
            update_fields=[
                "status",
                "rejection_reason",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        event_notifications.notify_revision_rejected(
            kind=event_notifications.REVISION_UNIVERSITY,
            revision=revision,
            actor=actor,
            reason=reason,
        )

        return revision

    @staticmethod
    @transaction.atomic
    def publish_revision(
            *,
            actor: User,
            revision_id,
    ) -> UniversityRevision:
        """Tasdiqlangan universitet revisionini atomik nashr qiladi."""

        UniversityRevisionService._ensure_permission(
            actor,
            "publish_university",
        )

        university_id = (
            UniversityRevision.objects
            .filter(pk=revision_id)
            .values_list("university_id", flat=True)
            .first()
        )

        if university_id is None:
            raise ValidationError("Universitet revisioni topilmadi.")

        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise ValidationError("Universitet topilmadi.")

        revision = (
            UniversityRevision.objects
            .select_for_update()
            .filter(
                pk=revision_id,
                university_id=university.pk,
            )
            .first()
        )

        if revision is None:
            raise ValidationError("Universitet revisioni topilmadi.")

        if university.status == University.Status.ARCHIVED:
            raise ValidationError(
                "Arxivlangan universitetni nashr qilish mumkin emas."
            )

        if revision.status != UniversityRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi revisionni nashr qilish mumkin."
            )

        if revision.approved_by_id is None or revision.approved_at is None:
            raise ValidationError(
                "Revision nashr qilishdan oldin tasdiqlanishi kerak."
            )

        # Kamida bitta published Uzbek tarjimasi bo'lishi shart.
        has_published_uzbek_translation = (
            UniversityTranslation.objects
            .filter(
                university_id=university.pk,
                language_code="uz",
                published_revision__isnull=False,
                published_revision__status=(
                    UniversityTranslationRevision.Status.PUBLISHED
                ),
                published_revision__translation_id=F("pk"),
            )
            .exists()
        )

        if not has_published_uzbek_translation:
            raise ValidationError(
                "Universitetni nashr qilish uchun "
                "UZ tilidagi published tarjima mavjud bo'lishi shart."
            )

        # Avvalgi published revisionni tekshirish va arxivlash.
        previous_revision = university.published_revision

        if previous_revision:
            if previous_revision.university_id != university.pk:
                raise ValidationError(
                    "Universitetning faol revision bog'lanishi noto'g'ri."
                )

            if previous_revision.pk != revision.pk:
                if previous_revision.status != UniversityRevision.Status.PUBLISHED:
                    raise ValidationError(
                        "Avvalgi faol revision PUBLISHED holatida emas."
                    )

                previous_revision.status = UniversityRevision.Status.ARCHIVED
                previous_revision.save(
                    update_fields=["status", "updated_at"]
                )

        # Yangi revisionni nashr qilish.
        revision.status = UniversityRevision.Status.PUBLISHED
        revision.published_at = timezone.now()
        revision.save(
            update_fields=[
                "status",
                "published_at",
                "updated_at",
            ]
        )

        # Universitetning global holati va faol revisionini yangilash.
        university.published_revision = revision
        university.status = University.Status.PUBLISHED
        university.updated_by = actor

        university.save(
            update_fields=[
                "published_revision",
                "status",
                "updated_by",
                "updated_at",
            ]
        )

        event_notifications.notify_revision_published(
            kind=event_notifications.REVISION_UNIVERSITY,
            revision=revision,
            actor=actor,
        )

        return revision

    @staticmethod
    @transaction.atomic
    def archive_revision(*, actor: User, revision_id) -> UniversityRevision:
        """PUBLISHED yoki DRAFT holatidagi universitet revisionini ARCHIVED qiladi."""

        UniversityRevisionService._ensure_permission(
            actor,
            "change_university",
        )

        revision = UniversityRevisionService._get_revision_for_update(
            revision_id,
            allow_archived_university=True,
            not_found_exc=ResourceNotFoundError,
        )

        if revision.status == UniversityRevision.Status.ARCHIVED:
            raise ValidationError("Ushbu revision allaqachon arxivlangan.")

        if revision.status not in (
            UniversityRevision.Status.PUBLISHED,
            UniversityRevision.Status.DRAFT,
        ):
            raise ValidationError(
                "Faqat PUBLISHED yoki DRAFT holatidagi revisionni arxivlash mumkin."
            )

        university = revision.university
        previous_status = revision.status

        if university.published_revision_id == revision.pk:
            if university.status == University.Status.PUBLISHED:
                raise ValidationError(
                    "Nashr qilingan universitetning faol revisionini "
                    "arxivlashdan oldin universitetni arxivlang."
                )
            university.published_revision = None
            university.updated_by = actor
            university.save(
                update_fields=["published_revision", "updated_by", "updated_at"]
            )

        revision.status = UniversityRevision.Status.ARCHIVED
        revision.save(update_fields=["status", "updated_at"])

        AuditLogService.log_archives(
            actor=actor,
            entries=[
                {
                    "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_REVISION,
                    "object_id": revision.pk,
                    "object_repr": (
                        f"Revision #{revision.revision_number} "
                        f"({revision.city}, {revision.country})"
                    ),
                    "metadata": {
                        "university_id": str(university.pk),
                        "revision_number": revision.revision_number,
                        "previous_status": previous_status,
                        "new_status": revision.status,
                    },
                }
            ],
        )

        return revision

    @staticmethod
    @transaction.atomic
    def delete_revision(*, actor: User, revision_id) -> None:
        """Faqat ARCHIVED holatidagi universitet revisionini o'chiradi."""

        UniversityRevisionService._ensure_permission(
            actor,
            "delete_universityrevision",
        )

        revision = UniversityRevisionService._get_revision_for_update(
            revision_id,
            allow_archived_university=True,
            not_found_exc=ResourceNotFoundError,
        )

        if revision.status != UniversityRevision.Status.ARCHIVED:
            raise ValidationError(
                "Faqat ARCHIVED holatidagi universitet revisionini o'chirish mumkin."
            )

        if revision.university.published_revision_id == revision.pk:
            raise ValidationError(
                "Universitetning joriy nashr qilingan revisionini o'chirish mumkin emas."
            )

        period_rows = list(
            UniversityAdmissionPeriod.objects
            .select_for_update()
            .filter(university_revision=revision)
            .order_by("id")
            .values_list("id", "name")
        )
        major_rows = list(
            UniversityMajor.objects
            .select_for_update()
            .filter(university_revision=revision)
            .order_by("id")
            .values_list("id", "order")
        )
        media_rows = list(
            UniversityMedia.objects
            .select_for_update()
            .filter(university_revision=revision)
            .order_by("id")
            .values_list("id", "file", "media_type")
        )

        media_paths = [file_path for _, file_path, _ in media_rows if file_path]

        audit_entries = []
        for period_id, period_name in period_rows:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_ADMISSION_PERIOD,
                "object_id": period_id,
                "object_repr": period_name,
                "metadata": {
                    "university_id": str(revision.university_id),
                    "revision_id": str(revision.pk),
                    "deleted_via": "UniversityRevision",
                },
            })
        for major_id, major_order in major_rows:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_MAJOR,
                "object_id": major_id,
                "object_repr": f"UniversityMajor #{major_order}",
                "metadata": {
                    "university_id": str(revision.university_id),
                    "revision_id": str(revision.pk),
                    "deleted_via": "UniversityRevision",
                },
            })
        for media_id, file_path, media_type in media_rows:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_MEDIA,
                "object_id": media_id,
                "object_repr": f"{media_type}: {file_path}",
                "metadata": {
                    "university_id": str(revision.university_id),
                    "revision_id": str(revision.pk),
                    "media_type": media_type,
                    "deleted_via": "UniversityRevision",
                },
            })
        audit_entries.append({
            "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_REVISION,
            "object_id": revision.pk,
            "object_repr": (
                f"Revision #{revision.revision_number} "
                f"({revision.city}, {revision.country})"
            ),
            "metadata": {
                "university_id": str(revision.university_id),
                "revision_number": revision.revision_number,
                "status": revision.status,
            },
        })

        UniversityAdmissionPeriod.objects.filter(
            university_revision=revision,
        ).delete()
        UniversityMajor.objects.filter(
            university_revision=revision,
        ).delete()
        UniversityMedia.objects.filter(
            university_revision=revision,
        ).delete()

        try:
            revision.delete()
        except ProtectedError as exc:
            raise ValidationError(
                "Revisionga bog'langan himoyalangan yozuvlar mavjudligi "
                "sababli uni o'chirish mumkin emas."
            ) from exc

        AuditLogService.log_deletes(actor=actor, entries=audit_entries)
        MediaLifecycleService.schedule_cleanup(file_paths=media_paths)
