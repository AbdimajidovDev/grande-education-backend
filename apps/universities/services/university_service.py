
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from apps.rbac.services.role_service import RoleService

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


class UniversityService:
    """Universitet yaratish va uning global holatini boshqarish xizmatlari."""

    @staticmethod
    def _ensure_authenticated(actor: User) -> None:
        if (
                actor is None
                or not actor.is_authenticated
                or not actor.is_active
        ):
            raise PermissionDenied(
                "Bu amalni bajarish uchun faol foydalanuvchi "
                "bo'lishingiz kerak."
            )

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
        UniversityService._ensure_authenticated(actor)

        if actor.is_superuser:
            return

        actor_permissions = RoleService._get_actor_role_permissions(actor)

        if f"universities.{permission}" not in actor_permissions:
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
            )


    @staticmethod
    @transaction.atomic
    def create_university(
        *,
        actor: User,
        city: str,
        country: str,
    ) -> University:
        """Universitet va uning birinchi revisionini atomik yaratadi."""

        UniversityService._ensure_permission(
            actor,
            "add_university",
        )

        city = city.strip()
        country = country.strip()

        if not city:
            raise ValidationError({"city": "Shahar nomi kiritilishi shart."})

        if not country:
            raise ValidationError({"country": "Mamlakat nomi kiritilishi shart."})

        university = University.objects.create(
            status=University.Status.DRAFT,
            created_by=actor,
            updated_by=actor,
        )

        UniversityRevision.objects.create(
            university=university,
            revision_number=1,
            city=city,
            country=country,
            status=UniversityRevision.Status.DRAFT,
            created_by=actor,
        )

        return university

    ALLOWED_STATUS_TRANSITIONS = {
        University.Status.DRAFT: {
            University.Status.ARCHIVED,
        },
        University.Status.PUBLISHED: {
            University.Status.ARCHIVED,
        },
        University.Status.ARCHIVED: {
            University.Status.DRAFT,
        },
    }

    STATUS_TRANSITION_PERMISSIONS = {
        (
            University.Status.DRAFT,
            University.Status.ARCHIVED,
        ): "change_university",
        (
            University.Status.PUBLISHED,
            University.Status.ARCHIVED,
        ): "change_university",
        (
            University.Status.ARCHIVED,
            University.Status.DRAFT,
        ): "change_university",
    }


    @staticmethod
    @transaction.atomic
    def change_status(*, actor: User, university_id, new_status: str,) -> University:

        UniversityService._ensure_authenticated(actor)

        allowed_statuses = {
            University.Status.DRAFT,
            University.Status.REVIEW,
            University.Status.PUBLISHED,
            University.Status.ARCHIVED,
        }

        if new_status not in allowed_statuses:
            raise ValidationError({
                "status": "Noto‘g‘ri universitet statusi."
            })

        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise ResourceNotFoundError("Universitet topilmadi.")

        if university.status == new_status:
            raise ValidationError(
                "Universitet allaqachon ushbu statusda."
            )

        allowed_statuses = (
            UniversityService.ALLOWED_STATUS_TRANSITIONS.get(
                university.status,
                set(),
            )
        )

        if new_status not in allowed_statuses:
            raise ValidationError({
                "status": (
                    f"{university.status} holatidan "
                    f"{new_status} holatiga o'tish mumkin emas."
                )
            })

        required_permission = (
            UniversityService.STATUS_TRANSITION_PERMISSIONS.get(
                (university.status, new_status)
            )
        )

        if required_permission is None:
            raise ValidationError(
                "Ushbu status o'zgarishi uchun permission belgilanmagan."
            )

        UniversityService._ensure_permission(
            actor,
            required_permission,
        )

        previous_status = university.status
        university.status = new_status
        university.updated_by = actor

        university.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ]
        )

        if new_status == University.Status.ARCHIVED:
            AuditLogService.log_archives(
                actor=actor,
                entries=[
                    {
                        "object_type": UniversityAuditLog.ObjectType.UNIVERSITY,
                        "object_id": university.pk,
                        "object_repr": f"University {university.pk}",
                        "metadata": {
                            "previous_status": previous_status,
                            "new_status": new_status,
                        },
                    }
                ],
            )

        return university

    @staticmethod
    @transaction.atomic
    def delete_university(*, actor: User, university_id) -> None:
        """Faqat ARCHIVED holatidagi universitetni va uning arxivlangan childlarini o'chiradi."""

        UniversityService._ensure_permission(actor, "delete_university")

        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise ResourceNotFoundError("Universitet topilmadi.")

        if university.status != University.Status.ARCHIVED:
            raise ValidationError(
                "Faqat ARCHIVED holatidagi universitetni o'chirish mumkin."
            )

        revisions = list(
            UniversityRevision.objects
            .select_for_update()
            .filter(university=university)
            .order_by("id")
        )
        revision_ids = [revision.id for revision in revisions]

        translations = list(
            UniversityTranslation.objects
            .select_for_update()
            .filter(university=university)
            .order_by("id")
        )
        translation_ids = [translation.id for translation in translations]

        translation_revisions = []
        if translation_ids:
            translation_revisions = list(
                UniversityTranslationRevision.objects
                .select_for_update()
                .filter(translation_id__in=translation_ids)
                .order_by("id")
            )

        if university.published_revision_id is not None:
            raise ValidationError(
                "Nashr qilingan revision bog'lanishiga ega universitetni "
                "o'chirish mumkin emas."
            )

        if any(
            revision.status != UniversityRevision.Status.ARCHIVED
            for revision in revisions
        ):
            raise ValidationError(
                "Universitet tarkibida ARCHIVED bo'lmagan reviziya mavjud."
            )

        if any(
            translation.published_revision_id is not None
            for translation in translations
        ):
            raise ValidationError(
                "Universitet tarkibida nashr qilingan tarjima bog'lanishi mavjud."
            )

        if any(
            trans_rev.status != UniversityTranslationRevision.Status.ARCHIVED
            for trans_rev in translation_revisions
        ):
            raise ValidationError(
                "Universitet tarkibida ARCHIVED bo'lmagan tarjima reviziyasi mavjud."
            )

        if university.admissions.exists():
            raise ValidationError(
                "Ushbu universitetga bog'langan qabul arizalari mavjudligi "
                "sababli uni o'chirish mumkin emas."
            )

        period_rows = []
        major_rows = []
        media_rows = []
        if revision_ids:
            period_rows = list(
                UniversityAdmissionPeriod.objects
                .select_for_update()
                .filter(university_revision_id__in=revision_ids)
                .order_by("id")
                .values_list("id", "name", "university_revision_id")
            )
            major_rows = list(
                UniversityMajor.objects
                .select_for_update()
                .filter(university_revision_id__in=revision_ids)
                .order_by("id")
                .values_list("id", "order", "university_revision_id")
            )
            media_rows = list(
                UniversityMedia.objects
                .select_for_update()
                .filter(university_revision_id__in=revision_ids)
                .order_by("id")
                .values_list("id", "file", "media_type", "university_revision_id")
            )

        media_paths = [file_path for _, file_path, _, _ in media_rows if file_path]

        audit_entries = []
        for trans_rev in translation_revisions:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION_REVISION,
                "object_id": trans_rev.pk,
                "object_repr": f"{trans_rev.name} (rev {trans_rev.revision_number})",
                "metadata": {
                    "university_id": str(university.pk),
                    "translation_id": str(trans_rev.translation_id),
                    "revision_number": trans_rev.revision_number,
                    "status": trans_rev.status,
                    "deleted_via": "University",
                },
            })
        for translation in translations:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION,
                "object_id": translation.pk,
                "object_repr": f"UniversityTranslation ({translation.language_code})",
                "metadata": {
                    "university_id": str(university.pk),
                    "language_code": translation.language_code,
                    "deleted_via": "University",
                },
            })
        for period_id, period_name, rev_id in period_rows:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_ADMISSION_PERIOD,
                "object_id": period_id,
                "object_repr": period_name,
                "metadata": {
                    "university_id": str(university.pk),
                    "revision_id": str(rev_id),
                    "deleted_via": "University",
                },
            })
        for major_id, major_order, rev_id in major_rows:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_MAJOR,
                "object_id": major_id,
                "object_repr": f"UniversityMajor #{major_order}",
                "metadata": {
                    "university_id": str(university.pk),
                    "revision_id": str(rev_id),
                    "deleted_via": "University",
                },
            })
        for media_id, file_path, media_type, rev_id in media_rows:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_MEDIA,
                "object_id": media_id,
                "object_repr": f"{media_type}: {file_path}",
                "metadata": {
                    "university_id": str(university.pk),
                    "revision_id": str(rev_id),
                    "media_type": media_type,
                    "deleted_via": "University",
                },
            })
        for revision in revisions:
            audit_entries.append({
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_REVISION,
                "object_id": revision.pk,
                "object_repr": (
                    f"Revision #{revision.revision_number} "
                    f"({revision.city}, {revision.country})"
                ),
                "metadata": {
                    "university_id": str(university.pk),
                    "revision_number": revision.revision_number,
                    "status": revision.status,
                    "deleted_via": "University",
                },
            })
        audit_entries.append({
            "object_type": UniversityAuditLog.ObjectType.UNIVERSITY,
            "object_id": university.pk,
            "object_repr": f"University {university.pk}",
            "metadata": {
                "status": university.status,
                "revisions_count": len(revisions),
                "translations_count": len(translations),
            },
        })

        # PROTECT bog'lanishlarni avval yechib olamiz.
        University.objects.filter(pk=university.pk).update(
            published_revision=None,
        )

        if translation_ids:
            UniversityTranslation.objects.filter(
                pk__in=translation_ids,
            ).update(published_revision=None)

            UniversityTranslationRevision.objects.filter(
                translation_id__in=translation_ids,
            ).delete()

            UniversityTranslation.objects.filter(
                pk__in=translation_ids,
            ).delete()

        if revision_ids:
            UniversityAdmissionPeriod.objects.filter(
                university_revision_id__in=revision_ids,
            ).delete()
            UniversityMajor.objects.filter(
                university_revision_id__in=revision_ids,
            ).delete()
            UniversityMedia.objects.filter(
                university_revision_id__in=revision_ids,
            ).delete()
            UniversityRevision.objects.filter(
                pk__in=revision_ids,
            ).delete()

        try:
            university.delete()
        except ProtectedError as exc:
            raise ValidationError(
                "Universitetga bog'langan himoyalangan yozuvlar mavjudligi "
                "sababli uni o'chirish mumkin emas."
            ) from exc

        AuditLogService.log_deletes(actor=actor, entries=audit_entries)
        MediaLifecycleService.schedule_cleanup(file_paths=media_paths)
