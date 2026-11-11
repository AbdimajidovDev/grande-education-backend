
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.rbac.services.role_service import RoleService
from apps.universities.constants import SUPPORTED_LANGUAGES
from apps.universities.models import (
    FAQ,
    FAQTranslation,
    FAQTranslationRevision,
)


User = get_user_model()


class FAQTranslationService:
    """FAQ tarjimalari va ularning revisionlarini boshqaradi."""

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
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

        if f"universities.{permission}" not in actor_permissions:
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
            )

    @staticmethod
    def _get_revision_for_update(revision_id):
        """FAQ, Translation va Revision qatorlarini tartib bilan lock qiladi."""

        revision_info = (
            FAQTranslationRevision.objects
            .filter(pk=revision_id)
            .values("translation_id")
            .first()
        )

        if revision_info is None:
            raise ValidationError("FAQ revisioni topilmadi.")

        translation_info = (
            FAQTranslation.objects
            .filter(pk=revision_info["translation_id"])
            .values("faq_id")
            .first()
        )

        if translation_info is None:
            raise ValidationError("FAQ tarjimasi topilmadi.")

        faq = (
            FAQ.objects
            .select_for_update()
            .filter(pk=translation_info["faq_id"])
            .first()
        )

        if faq is None:
            raise ValidationError("FAQ topilmadi.")

        translation = (
            FAQTranslation.objects
            .select_for_update()
            .filter(
                pk=revision_info["translation_id"],
                faq_id=faq.pk,
            )
            .first()
        )

        if translation is None:
            raise ValidationError("FAQ tarjimasi topilmadi.")

        revision = (
            FAQTranslationRevision.objects
            .select_for_update()
            .filter(
                pk=revision_id,
                translation_id=translation.pk,
            )
            .first()
        )

        if revision is None:
            raise ValidationError("FAQ revisioni topilmadi.")

        revision.translation = translation
        revision.translation.faq = faq

        return revision

    @staticmethod
    @transaction.atomic
    def create_translation(
        *,
        actor: User,
        faq_id,
        language_code: str,
        question: str,
        answer: str,
    ) -> FAQTranslation:
        """Yangi tarjima va uning birinchi DRAFT revisionini yaratadi."""

        FAQTranslationService._ensure_permission(actor, "add_faq")

        if not isinstance(language_code, str):
            raise ValidationError({
                "language_code": "Til kodi matn ko'rinishida bo'lishi kerak."
            })

        if not isinstance(question, str) or not question.strip():
            raise ValidationError({
                "question": "Savol kiritilishi shart."
            })

        if not isinstance(answer, str) or not answer.strip():
            raise ValidationError({
                "answer": "Javob kiritilishi shart."
            })

        language_code = language_code.strip().lower()
        question = question.strip()
        answer = answer.strip()

        if language_code not in SUPPORTED_LANGUAGES:
            raise ValidationError({
                "language_code": "Qo'llab-quvvatlanmaydigan til kodi."
            })

        faq = (
            FAQ.objects
            .select_for_update()
            .filter(pk=faq_id)
            .first()
        )

        if faq is None:
            raise ValidationError("FAQ topilmadi.")

        try:
            with transaction.atomic():
                translation = FAQTranslation.objects.create(
                    faq=faq,
                    language_code=language_code,
                )

                FAQTranslationRevision.objects.create(
                    translation=translation,
                    revision_number=1,
                    question=question,
                    answer=answer,
                    status=FAQTranslationRevision.Status.DRAFT,
                    created_by=actor,
                )

        except IntegrityError as exc:
            raise ValidationError({
                "language_code": (
                    "Ushbu FAQ uchun mazkur tildagi tarjima "
                    "allaqachon mavjud."
                )
            }) from exc

        return translation

    @staticmethod
    @transaction.atomic
    def create_revision(
        *,
        actor: User,
        translation_id,
        question: str,
        answer: str,
    ) -> FAQTranslationRevision:
        """Mavjud tarjima uchun yangi DRAFT revision yaratadi."""

        FAQTranslationService._ensure_permission(actor, "change_faq")

        if not isinstance(question, str) or not question.strip():
            raise ValidationError({
                "question": "Savol kiritilishi shart."
            })

        if not isinstance(answer, str) or not answer.strip():
            raise ValidationError({
                "answer": "Javob kiritilishi shart."
            })

        question = question.strip()
        answer = answer.strip()

        translation_info = (
            FAQTranslation.objects
            .filter(pk=translation_id)
            .values("faq_id")
            .first()
        )

        if translation_info is None:
            raise ValidationError("FAQ tarjimasi topilmadi.")

        faq = (
            FAQ.objects
            .select_for_update()
            .filter(pk=translation_info["faq_id"])
            .first()
        )

        if faq is None:
            raise ValidationError("FAQ topilmadi.")

        translation = (
            FAQTranslation.objects
            .select_for_update()
            .filter(pk=translation_id, faq_id=faq.pk)
            .first()
        )

        if translation is None:
            raise ValidationError("FAQ tarjimasi topilmadi.")

        last_revision_number = (
            FAQTranslationRevision.objects
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
            return FAQTranslationRevision.objects.create(
                translation=translation,
                revision_number=next_revision_number,
                question=question,
                answer=answer,
                status=FAQTranslationRevision.Status.DRAFT,
                created_by=actor,
            )
        except IntegrityError as exc:
            raise ValidationError(
                "FAQ revisionini yaratishda ma'lumotlar "
                "to'qnashuvi yuz berdi."
            ) from exc

    @staticmethod
    @transaction.atomic
    def update_revision(
        *,
        actor: User,
        revision_id,
        question: str | None = None,
        answer: str | None = None,
    ) -> FAQTranslationRevision:
        """Faqat DRAFT holatidagi FAQ revisionini tahrirlaydi."""

        FAQTranslationService._ensure_permission(actor, "change_faq")

        if question is None and answer is None:
            raise ValidationError(
                "Yangilash uchun kamida bitta maydon yuborilishi kerak."
            )

        if question is not None:
            if not isinstance(question, str) or not question.strip():
                raise ValidationError({
                    "question": "Savol bo'sh bo'lishi mumkin emas."
                })
            question = question.strip()

        if answer is not None:
            if not isinstance(answer, str) or not answer.strip():
                raise ValidationError({
                    "answer": "Javob bo'sh bo'lishi mumkin emas."
                })
            answer = answer.strip()

        revision = FAQTranslationService._get_revision_for_update(
            revision_id
        )

        if revision.status != FAQTranslationRevision.Status.DRAFT:
            raise ValidationError(
                "Faqat DRAFT holatidagi FAQ revisionini tahrirlash mumkin."
            )

        update_fields = []

        if question is not None:
            revision.question = question
            update_fields.append("question")

        if answer is not None:
            revision.answer = answer
            update_fields.append("answer")

        update_fields.append("updated_at")
        revision.save(update_fields=update_fields)

        return revision

    @staticmethod
    @transaction.atomic
    def submit_for_review(
        *,
        actor: User,
        revision_id,
    ) -> FAQTranslationRevision:
        """DRAFT FAQ revisionini ko'rib chiqishga yuboradi."""

        FAQTranslationService._ensure_permission(
            actor,
            "submit_review_faq",
        )

        revision = FAQTranslationService._get_revision_for_update(
            revision_id
        )

        if revision.status != FAQTranslationRevision.Status.DRAFT:
            raise ValidationError(
                "Faqat DRAFT holatidagi FAQ revisionini "
                "ko'rib chiqishga yuborish mumkin."
            )

        revision.status = FAQTranslationRevision.Status.REVIEW
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
    ) -> FAQTranslationRevision:
        """REVIEW FAQ revisionini tasdiqlaydi."""

        FAQTranslationService._ensure_permission(
            actor,
            "approve_faq",
        )

        revision = FAQTranslationService._get_revision_for_update(
            revision_id
        )

        if revision.status != FAQTranslationRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi FAQ revisionini tasdiqlash mumkin."
            )

        if revision.approved_at is not None:
            raise ValidationError(
                "Ushbu FAQ revisioni allaqachon tasdiqlangan."
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
    ) -> FAQTranslationRevision:
        """REVIEW FAQ revisionini rad etadi."""

        FAQTranslationService._ensure_permission(
            actor,
            "reject_faq",
        )

        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError({
                "reason": "Rad etish sababi kiritilishi shart."
            })

        reason = reason.strip()

        revision = FAQTranslationService._get_revision_for_update(
            revision_id
        )

        if revision.status != FAQTranslationRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi FAQ revisionini rad etish mumkin."
            )

        revision.status = FAQTranslationRevision.Status.DRAFT
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
    ) -> FAQTranslationRevision:
        """Tasdiqlangan FAQ tarjima revisionini atomik nashr qiladi."""

        FAQTranslationService._ensure_permission(
            actor,
            "publish_faq",
        )

        revision = FAQTranslationService._get_revision_for_update(
            revision_id
        )

        translation = revision.translation

        if revision.status != FAQTranslationRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi FAQ revisionini nashr qilish mumkin."
            )

        if revision.approved_by_id is None or revision.approved_at is None:
            raise ValidationError(
                "FAQ revisionini nashr qilishdan oldin tasdiqlash kerak."
            )

        previous_revision = translation.published_revision

        if previous_revision:
            if previous_revision.translation_id != translation.pk:
                raise ValidationError(
                    "FAQ tarjimasining faol revision bog'lanishi noto'g'ri."
                )

            if previous_revision.pk != revision.pk:
                if (
                    previous_revision.status
                    != FAQTranslationRevision.Status.PUBLISHED
                ):
                    raise ValidationError(
                        "Avvalgi faol FAQ revisioni "
                        "PUBLISHED holatida emas."
                    )

                previous_revision.status = (
                    FAQTranslationRevision.Status.ARCHIVED
                )
                previous_revision.save(
                    update_fields=["status", "updated_at"]
                )

        revision.status = FAQTranslationRevision.Status.PUBLISHED
        revision.published_at = timezone.now()

        revision.save(
            update_fields=[
                "status",
                "published_at",
                "updated_at",
            ]
        )

        translation.published_revision = revision
        translation.save(
            update_fields=[
                "published_revision",
                "updated_at",
            ]
        )

        return revision
