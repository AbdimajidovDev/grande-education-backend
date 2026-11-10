
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.universities.models import University, UniversityRevision
from django.utils import timezone


User = get_user_model()


class UniversityRevisionService:
    """Universitet umumiy ma'lumotlari revisionlarini boshqaradi."""

    @staticmethod
    def _ensure_permission(actor: User, permission: str) -> None:
        if not actor or not actor.is_authenticated:
            raise PermissionDenied(
                "Ushbu amal uchun autentifikatsiya talab qilinadi."
            )

        if not actor.is_superuser and not actor.has_perm(
                f"universities.{permission}"
        ):
            raise PermissionDenied(
                "Ushbu amalni bajarish uchun ruxsatingiz mavjud emas."
            )

    @staticmethod
    @transaction.atomic
    def create_revision(
        *,
        actor: User,
        university_id,
        city: str,
        country: str,
    ) -> UniversityRevision:
        """Universitet uchun yangi DRAFT revision yaratadi."""

        UniversityRevisionService._ensure_permission(
            actor,
            "change_university",
        )

        city = city.strip()
        country = country.strip()

        if not city:
            raise ValidationError({"city": "Shahar nomi kiritilishi shart."})

        if not country:
            raise ValidationError({"country": "Mamlakat nomi kiritilishi shart."})

        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise ValidationError("Universitet topilmadi.")

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
        city: str,
        country: str,
    ) -> UniversityRevision:
        """Faqat DRAFT holatidagi revisionni tahrirlaydi."""

        UniversityRevisionService._ensure_permission(
            actor,
            "change_university",
        )

        city = city.strip()
        country = country.strip()

        if not city:
            raise ValidationError({"city": "Shahar nomi kiritilishi shart."})

        if not country:
            raise ValidationError({"country": "Mamlakat nomi kiritilishi shart."})

        revision = (
            UniversityRevision.objects
            .select_for_update()
            .filter(pk=revision_id)
            .first()
        )

        if revision is None:
            raise ValidationError("Universitet revisioni topilmadi.")

        if revision.status != UniversityRevision.Status.DRAFT:
            raise ValidationError(
                "Faqat DRAFT holatidagi revisionni tahrirlash mumkin."
            )

        revision.city = city
        revision.country = country
        revision.save(update_fields=["city", "country", "updated_at"])

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

        revision = (
            UniversityRevision.objects
            .select_for_update()
            .filter(pk=revision_id)
            .first()
        )

        if revision is None:
            raise ValidationError("Universitet revisioni topilmadi.")

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

        return revision

    @staticmethod
    @transaction.atomic
    def approve_revision(*, actor: User, revision_id) -> UniversityRevision:
        UniversityRevisionService._ensure_permission(
            actor,
            "approve_university",
        )

        revision = (
            UniversityRevision.objects
            .select_for_update()
            .filter(pk=revision_id)
            .first()
        )

        if revision is None:
            raise ValidationError("Universitet revisioni topilmadi.")

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

        revision = (
            UniversityRevision.objects
            .select_for_update()
            .filter(pk=revision_id)
            .first()
        )

        if revision is None:
            raise ValidationError("Universitet revisioni topilmadi.")

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

        return revision

    @staticmethod
    @transaction.atomic
    def publish_revision(
            *,
            actor: User,
            revision_id,
    ) -> UniversityRevision:
        UniversityRevisionService._ensure_permission(
            actor,
            "publish_university",
        )

        # Revision qaysi universitetga tegishli ekanini aniqlaymiz.
        university_id = (
            UniversityRevision.objects
            .filter(pk=revision_id)
            .values_list("university_id", flat=True)
            .first()
        )

        if university_id is None:
            raise ValidationError("Universitet revisioni topilmadi.")

        # Bir universitetga tegishli operatsiyalarni ketma-ket bajarish uchun.
        university = (
            University.objects
            .select_for_update()
            .filter(pk=university_id)
            .first()
        )

        if university is None:
            raise ValidationError("Universitet topilmadi.")

        # Revisionni ham bloklaymiz.
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

        if revision.status != UniversityRevision.Status.REVIEW:
            raise ValidationError(
                "Faqat REVIEW holatidagi revisionni nashr qilish mumkin."
            )

        if revision.approved_by is None or revision.approved_at is None:
            raise ValidationError(
                "Revision nashr qilishdan oldin tasdiqlanishi kerak."
            )

        # Avvalgi nashr qilingan revisionni arxivlaymiz.
        previous_revision = university.published_revision

        if previous_revision and previous_revision.pk != revision.pk:
            previous_revision.status = UniversityRevision.Status.ARCHIVED
            previous_revision.save(
                update_fields=["status", "updated_at"]
            )

        # Yangi revisionni nashr qilamiz.
        revision.status = UniversityRevision.Status.PUBLISHED
        revision.published_at = timezone.now()
        revision.save(
            update_fields=[
                "status",
                "published_at",
                "updated_at",
            ]
        )

        # Universitetning faol revisionini yangilaymiz.
        university.published_revision = revision
        university.updated_by = actor
        university.save(
            update_fields=[
                "published_revision",
                "updated_by",
                "updated_at",
            ]
        )

        return revision
