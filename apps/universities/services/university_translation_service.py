from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from apps.rbac.services.role_service import RoleService
from apps.universities.models import (
    University,
    UniversityAuditLog,
    UniversityTranslation,
    UniversityTranslationRevision,
)
from apps.universities.services.audit_log_service import AuditLogService
from apps.universities.services.exceptions import ResourceNotFoundError
from django.utils import timezone
from apps.universities.constants import SUPPORTED_LANGUAGES

User = get_user_model()


class UniversityTranslationService:
    """Universitet tarjimalari va ularning revisionlarini boshqaradi."""

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
    ):
        """University, Translation va Revision qatorlarini tartib bilan lock qiladi."""

        revision_info = (
            UniversityTranslationRevision.objects
            .filter(pk=revision_id)
            .values("translation_id")
            .first()
        )

        if revision_info is None:
            raise not_found_exc(
                "Universitet tarjimasi revisioni topilmadi."
            )

        translation_info = (
            UniversityTranslation.objects
            .filter(pk=revision_info["translation_id"])
            .values("university_id")
            .first()
        )

        if translation_info is None:
            raise not_found_exc("Universitet tarjimasi topilmadi.")

        university = (
            University.objects
            .select_for_update()
            .filter(pk=translation_info["university_id"])
            .first()
        )

        if university is None:
            raise not_found_exc("Universitet topilmadi.")

        if (
            not allow_archived_university
            and university.status == University.Status.ARCHIVED
        ):
            raise ValidationError(
                "Arxivlangan universitet revisioni bilan amal bajarish mumkin emas."
            )

        translation = (
            UniversityTranslation.objects
            .select_for_update()
            .filter(
                pk=revision_info["translation_id"],
                university_id=university.pk,
            )
            .first()
        )

        if translation is None:
            raise not_found_exc("Universitet tarjimasi topilmadi.")

        revision = (
            UniversityTranslationRevision.objects
            .select_for_update()
            .filter(
                pk=revision_id,
                translation_id=translation.pk,
            )
            .first()
        )

        if revision is None:
            raise not_found_exc(
                "Universitet tarjimasi revisioni topilmadi."
            )

        translation.university = university
        revision.translation = translation

        return revision


    @staticmethod
    @transaction.atomic
    def create_translation(
        *,
        actor: User,
        university_id,
        language_code: str,
        name: str,
        slug: str,
        description: str = "",
        subtitle: str = "",
        features: list | None = None,
        accommodation_info: str = "",
        admission_note: str = "",
        seo_title: str = "",
        seo_description: str = "",
    ) -> UniversityTranslation:
        """
        Universitet uchun yangi tarjima va uning birinchi
        DRAFT revisionini yaratadi.
        """

        UniversityTranslationService._ensure_permission(
            actor,
            "add_university",
        )

        language_code = language_code.strip().lower()
        name = name.strip()
        slug = slug.strip()
        description = description.strip()
        subtitle = subtitle.strip()
        accommodation_info = accommodation_info.strip()
        admission_note = admission_note.strip()
        seo_title = seo_title.strip()
        seo_description = seo_description.strip()
        features_list = features if isinstance(features, list) else []

        if language_code not in SUPPORTED_LANGUAGES:
            raise ValidationError({
                "language_code": "Qo'llab-quvvatlanmaydigan til kodi."
            })

        if not name:
            raise ValidationError({
                "name": "Universitet nomi kiritilishi shart."
            })

        if not slug:
            raise ValidationError({
                "slug": "URL identifikatori kiritilishi shart."
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
                "Arxivlangan universitet uchun yangi tarjima yaratish mumkin emas."
            )

        try:
            with transaction.atomic():
                translation = UniversityTranslation.objects.create(
                    university=university,
                    language_code=language_code,
                )

                UniversityTranslationRevision.objects.create(
                    translation=translation,
                    revision_number=1,
                    name=name,
                    slug=slug,
                    subtitle=subtitle,
                    description=description,
                    features=features_list,
                    accommodation_info=accommodation_info,
                    admission_note=admission_note,
                    seo_title=seo_title,
                    seo_description=seo_description,
                    status=UniversityTranslationRevision.Status.DRAFT,
                    created_by=actor,
                )

        except IntegrityError as exc:
            raise ValidationError({
                "language_code": (
                    "Ushbu universitet uchun mazkur tildagi "
                    "tarjima allaqachon mavjud yoki URL identifikatori "
                    "band."
                )
            }) from exc

        return translation

    @staticmethod
    @transaction.atomic
    def create_revision(
        *,
        actor: User,
        translation_id,
        name: str,
        slug: str,
        description: str = "",
        subtitle: str = "",
        features: list | None = None,
        accommodation_info: str = "",
        admission_note: str = "",
        seo_title: str = "",
        seo_description: str = "",
    ) -> UniversityTranslationRevision:
        """Mavjud tarjima uchun yangi DRAFT revision yaratadi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "change_university",
        )

        name = name.strip()
        slug = slug.strip()
        description = description.strip()
        subtitle = subtitle.strip()
        accommodation_info = accommodation_info.strip()
        admission_note = admission_note.strip()
        seo_title = seo_title.strip()
        seo_description = seo_description.strip()
        features_list = features if isinstance(features, list) else []

        if not name:
            raise ValidationError({
                "name": "Universitet nomi kiritilishi shart."
            })

        if not slug:
            raise ValidationError({
                "slug": "URL identifikatori kiritilishi shart."
            })

        translation_info = (
            UniversityTranslation.objects
            .filter(pk=translation_id)
            .values("university_id")
            .first()
        )

        if translation_info is None:
            raise ValidationError("Universitet tarjimasi topilmadi.")

        university = (
            University.objects
            .select_for_update()
            .filter(pk=translation_info["university_id"])
            .first()
        )

        if university is None:
            raise ValidationError("Universitet topilmadi.")

        if university.status == University.Status.ARCHIVED:
            raise ValidationError(
                "Arxivlangan universitet uchun yangi revision yaratish mumkin emas."
            )

        translation = (
            UniversityTranslation.objects
            .select_for_update()
            .filter(pk=translation_id, university_id=university.pk)
            .first()
        )

        if translation is None:
            raise ValidationError("Universitet tarjimasi topilmadi.")

        last_revision_number = (
            UniversityTranslationRevision.objects
            .filter(translation=translation)
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
            return UniversityTranslationRevision.objects.create(
                translation=translation,
                revision_number=next_revision_number,
                name=name,
                slug=slug,
                subtitle=subtitle,
                description=description,
                features=features_list,
                accommodation_info=accommodation_info,
                admission_note=admission_note,
                seo_title=seo_title,
                seo_description=seo_description,
                status=UniversityTranslationRevision.Status.DRAFT,
                created_by=actor,
            )
        except IntegrityError as exc:
            raise ValidationError(
                "Tarjima revisionini yaratishda ma'lumotlar "
                "to'qnashuvi yuz berdi."
            ) from exc


    @staticmethod
    @transaction.atomic
    def update_revision(
            *,
            actor: User,
            revision_id,
            name: str | None = None,
            slug: str | None = None,
            description: str | None = None,
            subtitle: str | None = None,
            features: list | None = None,
            accommodation_info: str | None = None,
            admission_note: str | None = None,
            seo_title: str | None = None,
            seo_description: str | None = None,
    ) -> UniversityTranslationRevision:
        """Faqat DRAFT holatidagi tarjima revisionini tahrirlaydi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "change_university",
        )

        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError({
                    "name": "Universitet nomi bo'sh bo'lishi mumkin emas."
                })

        if slug is not None:
            slug = slug.strip()
            if not slug:
                raise ValidationError({
                    "slug": "URL identifikatori bo'sh bo'lishi mumkin emas."
                })

        if description is not None:
            description = description.strip()

        if subtitle is not None:
            subtitle = subtitle.strip()

        if accommodation_info is not None:
            accommodation_info = accommodation_info.strip()

        if admission_note is not None:
            admission_note = admission_note.strip()

        if seo_title is not None:
            seo_title = seo_title.strip()

        if seo_description is not None:
            seo_description = seo_description.strip()

        revision_info = (
            UniversityTranslationRevision.objects
            .filter(pk=revision_id)
            .values("translation_id")
            .first()
        )

        if revision_info is None:
            raise ValidationError(
                "Universitet tarjimasi revisioni topilmadi."
            )

        translation_info = (
            UniversityTranslation.objects
            .filter(pk=revision_info["translation_id"])
            .values("university_id")
            .first()
        )

        if translation_info is None:
            raise ValidationError("Universitet tarjimasi topilmadi.")

        university = (
            University.objects
            .select_for_update()
            .filter(pk=translation_info["university_id"])
            .first()
        )

        if university is None:
            raise ValidationError("Universitet topilmadi.")

        if university.status == University.Status.ARCHIVED:
            raise ValidationError(
                "Arxivlangan universitet revisionini tahrirlash mumkin emas."
            )

        translation = (
            UniversityTranslation.objects
            .select_for_update()
            .filter(
                pk=revision_info["translation_id"],
                university_id=university.pk,
            )
            .first()
        )

        if translation is None:
            raise ValidationError("Universitet tarjimasi topilmadi.")

        revision = (
            UniversityTranslationRevision.objects
            .select_for_update()
            .filter(
                pk=revision_id,
                translation_id=translation.pk,
            )
            .first()
        )

        if revision is None:
            raise ValidationError(
                "Universitet tarjimasi revisioni topilmadi."
            )

        if revision.status != UniversityTranslationRevision.Status.DRAFT:
            raise ValidationError(
                "Faqat DRAFT holatidagi tarjima revisionini "
                "tahrirlash mumkin."
            )

        update_fields = []

        if name is not None:
            revision.name = name
            update_fields.append("name")

        if slug is not None:
            revision.slug = slug
            update_fields.append("slug")

        if description is not None:
            revision.description = description
            update_fields.append("description")

        if subtitle is not None:
            revision.subtitle = subtitle
            update_fields.append("subtitle")

        if features is not None and isinstance(features, list):
            revision.features = features
            update_fields.append("features")

        if accommodation_info is not None:
            revision.accommodation_info = accommodation_info
            update_fields.append("accommodation_info")

        if admission_note is not None:
            revision.admission_note = admission_note
            update_fields.append("admission_note")

        if seo_title is not None:
            revision.seo_title = seo_title
            update_fields.append("seo_title")

        if seo_description is not None:
            revision.seo_description = seo_description
            update_fields.append("seo_description")

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
    ) -> UniversityTranslationRevision:
        """DRAFT tarjima revisionini ko'rib chiqishga yuboradi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "submit_review_university",
        )

        revision = UniversityTranslationService._get_revision_for_update(
            revision_id
        )

        if revision.status != UniversityTranslationRevision.Status.DRAFT:
            raise ValidationError(
                "Faqat DRAFT holatidagi tarjima revisionini "
                "ko'rib chiqishga yuborish mumkin."
            )

        revision.status = UniversityTranslationRevision.Status.REVIEW
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

        return revision

    @staticmethod
    @transaction.atomic
    def approve_revision(
        *,
        actor: User,
        revision_id,
    ) -> UniversityTranslationRevision:
        """REVIEW tarjima revisionini tasdiqlaydi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "approve_university",
        )

        revision = UniversityTranslationService._get_revision_for_update(
            revision_id
        )

        if revision.status != UniversityTranslationRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi tarjima revisionini "
                "tasdiqlash mumkin."
            )

        if revision.approved_at is not None:
            raise ValidationError(
                "Ushbu tarjima revisioni allaqachon tasdiqlangan."
            )

        revision.approved_by = actor
        revision.approved_at = timezone.now()

        revision.save(
            update_fields=[
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        return revision

    @staticmethod
    @transaction.atomic
    def reject_revision(
        *,
        actor: User,
        revision_id,
        reason: str,
    ) -> UniversityTranslationRevision:
        """REVIEW tarjima revisionini rad etadi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "reject_university",
        )

        reason = reason.strip()

        if not reason:
            raise ValidationError({
                "reason": "Rad etish sababi kiritilishi shart."
            })

        revision = UniversityTranslationService._get_revision_for_update(
            revision_id
        )

        if revision.status != UniversityTranslationRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi tarjima revisionini "
                "rad etish mumkin."
            )

        revision.status = UniversityTranslationRevision.Status.DRAFT
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

        return revision

    @staticmethod
    @transaction.atomic
    def publish_translation_revision(
            *,
            actor: User,
            revision_id,
    ) -> UniversityTranslationRevision:
        """Tasdiqlangan tarjima revisionini atomik nashr qiladi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "publish_university",
        )

        revision = UniversityTranslationService._get_revision_for_update(
            revision_id
        )

        translation = revision.translation

        if revision.status != UniversityTranslationRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi tarjima revisionini "
                "nashr qilish mumkin."
            )

        if revision.approved_by_id is None or revision.approved_at is None:
            raise ValidationError(
                "Tarjima revisionini nashr qilishdan oldin "
                "tasdiqlash kerak."
            )

        # Amaldagi tarjimalar orasida slug bandligini tekshirish.
        slug_exists = (
            UniversityTranslation.objects
            .filter(
                language_code=translation.language_code,
                slug=revision.slug,
            )
            .exclude(pk=translation.pk)
            .exists()
        )

        if slug_exists:
            raise ValidationError({
                "slug": (
                    "Ushbu til uchun URL identifikatori "
                    "boshqa universitetda ishlatilmoqda."
                )
            })

        previous_revision = translation.published_revision

        if previous_revision:
            if previous_revision.translation_id != translation.pk:
                raise ValidationError(
                    "Tarjimaning faol revision bog'lanishi noto'g'ri."
                )

            if previous_revision.pk != revision.pk:
                if (
                        previous_revision.status
                        != UniversityTranslationRevision.Status.PUBLISHED
                ):
                    raise ValidationError(
                        "Avvalgi faol tarjima revisioni "
                        "PUBLISHED holatida emas."
                    )

                previous_revision.status = (
                    UniversityTranslationRevision.Status.ARCHIVED
                )
                previous_revision.save(
                    update_fields=["status", "updated_at"]
                )

        revision.status = UniversityTranslationRevision.Status.PUBLISHED
        revision.published_at = timezone.now()

        revision.save(
            update_fields=[
                "status",
                "published_at",
                "updated_at",
            ]
        )

        translation.published_revision = revision
        translation.slug = revision.slug

        try:
            with transaction.atomic():
                translation.save(
                    update_fields=[
                        "published_revision",
                        "slug",
                        "updated_at",
                    ]
                )
        except IntegrityError as exc:
            raise ValidationError({
                "slug": (
                    "Ushbu til uchun URL identifikatori "
                    "allaqachon band."
                )
            }) from exc

        return revision

    @staticmethod
    @transaction.atomic
    def archive_revision(
        *,
        actor: User,
        revision_id,
    ) -> UniversityTranslationRevision:
        """PUBLISHED yoki DRAFT tarjima revisionini ARCHIVED holatiga o'tkazadi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "change_university",
        )

        revision = UniversityTranslationService._get_revision_for_update(
            revision_id,
            allow_archived_university=True,
            not_found_exc=ResourceNotFoundError,
        )

        if revision.status == UniversityTranslationRevision.Status.ARCHIVED:
            raise ValidationError(
                "Ushbu tarjima revisioni allaqachon arxivlangan."
            )

        if revision.status not in (
            UniversityTranslationRevision.Status.PUBLISHED,
            UniversityTranslationRevision.Status.DRAFT,
        ):
            raise ValidationError(
                "Faqat PUBLISHED yoki DRAFT holatidagi tarjima "
                "revisionini arxivlash mumkin."
            )

        translation = revision.translation
        university = translation.university
        previous_status = revision.status

        if translation.published_revision_id == revision.pk:
            if (
                university.status == University.Status.PUBLISHED
                and translation.language_code == "uz"
            ):
                raise ValidationError(
                    "Nashr qilingan universitetning asosiy (uz) tarjima "
                    "revisionini arxivlashdan oldin universitetni arxivlang."
                )
            translation.published_revision = None
            translation.slug = None
            translation.save(
                update_fields=["published_revision", "slug", "updated_at"]
            )

        revision.status = UniversityTranslationRevision.Status.ARCHIVED
        revision.save(update_fields=["status", "updated_at"])

        AuditLogService.log_archives(
            actor=actor,
            entries=[
                {
                    "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION_REVISION,
                    "object_id": revision.pk,
                    "object_repr": f"{revision.name} (rev {revision.revision_number})",
                    "metadata": {
                        "university_id": str(university.pk),
                        "translation_id": str(translation.pk),
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
    def delete_translation(*, actor: User, translation_id) -> None:
        """Faqat arxivlangan universitet tarjimasini va uning arxivlangan revisionlarini o'chiradi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "delete_universitytranslation",
        )

        translation_info = (
            UniversityTranslation.objects
            .filter(pk=translation_id)
            .values("university_id")
            .first()
        )

        if translation_info is None:
            raise ResourceNotFoundError("Universitet tarjimasi topilmadi.")

        university = (
            University.objects
            .select_for_update()
            .filter(pk=translation_info["university_id"])
            .first()
        )

        if university is None:
            raise ResourceNotFoundError("Universitet topilmadi.")

        translation = (
            UniversityTranslation.objects
            .select_for_update()
            .filter(pk=translation_id, university_id=university.pk)
            .first()
        )

        if translation is None:
            raise ResourceNotFoundError("Universitet tarjimasi topilmadi.")

        if translation.published_revision_id is not None:
            raise ValidationError(
                "Nashr qilingan universitet tarjimasini o'chirish mumkin emas."
            )

        if (
            university.status == University.Status.PUBLISHED
            and translation.language_code == "uz"
        ):
            raise ValidationError(
                "Nashr qilingan universitetning asosiy (uz) tarjimasini "
                "o'chirish mumkin emas."
            )

        revisions = list(
            UniversityTranslationRevision.objects
            .select_for_update()
            .filter(translation=translation)
            .order_by("id")
        )

        if any(
            rev.status != UniversityTranslationRevision.Status.ARCHIVED
            for rev in revisions
        ):
            raise ValidationError(
                "Faqat barcha reviziyalari ARCHIVED holatida bo'lgan "
                "tarjimani o'chirish mumkin."
            )

        if (
            not revisions
            and university.status != University.Status.ARCHIVED
        ):
            raise ValidationError(
                "Faqat arxivlangan tarjimani o'chirish mumkin."
            )

        audit_entries = [
            {
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION_REVISION,
                "object_id": rev.pk,
                "object_repr": f"{rev.name} (rev {rev.revision_number})",
                "metadata": {
                    "university_id": str(university.pk),
                    "translation_id": str(translation.pk),
                    "revision_number": rev.revision_number,
                    "status": rev.status,
                    "deleted_via": "UniversityTranslation",
                },
            }
            for rev in revisions
        ]
        audit_entries.append({
            "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION,
            "object_id": translation.pk,
            "object_repr": f"UniversityTranslation ({translation.language_code})",
            "metadata": {
                "university_id": str(university.pk),
                "language_code": translation.language_code,
                "revisions_count": len(revisions),
            },
        })

        if revisions:
            UniversityTranslation.objects.filter(pk=translation.pk).update(
                published_revision=None,
            )
            UniversityTranslationRevision.objects.filter(
                translation=translation,
            ).delete()

        try:
            translation.delete()
        except ProtectedError as exc:
            raise ValidationError(
                "Tarjimaga bog'langan himoyalangan yozuvlar mavjudligi "
                "sababli uni o'chirish mumkin emas."
            ) from exc

        AuditLogService.log_deletes(actor=actor, entries=audit_entries)

    @staticmethod
    @transaction.atomic
    def delete_revision(*, actor: User, revision_id) -> None:
        """Faqat ARCHIVED holatidagi tarjima revisionini o'chiradi."""

        UniversityTranslationService._ensure_permission(
            actor,
            "delete_universitytranslationrevision",
        )

        revision = UniversityTranslationService._get_revision_for_update(
            revision_id,
            allow_archived_university=True,
            not_found_exc=ResourceNotFoundError,
        )

        if revision.status != UniversityTranslationRevision.Status.ARCHIVED:
            raise ValidationError(
                "Faqat ARCHIVED holatidagi tarjima revisionini o'chirish mumkin."
            )

        if revision.translation.published_revision_id == revision.pk:
            raise ValidationError(
                "Tarjimaning joriy nashr qilingan revisionini o'chirish mumkin emas."
            )

        audit_entries = [
            {
                "object_type": UniversityAuditLog.ObjectType.UNIVERSITY_TRANSLATION_REVISION,
                "object_id": revision.pk,
                "object_repr": f"{revision.name} (rev {revision.revision_number})",
                "metadata": {
                    "university_id": str(revision.translation.university_id),
                    "translation_id": str(revision.translation_id),
                    "revision_number": revision.revision_number,
                    "status": revision.status,
                },
            }
        ]

        try:
            revision.delete()
        except ProtectedError as exc:
            raise ValidationError(
                "Tarjima revisioniga bog'langan himoyalangan yozuvlar "
                "mavjudligi sababli uni o'chirish mumkin emas."
            ) from exc

        AuditLogService.log_deletes(actor=actor, entries=audit_entries)
