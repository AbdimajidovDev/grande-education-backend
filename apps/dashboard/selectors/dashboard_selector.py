
from datetime import datetime, time

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.admissions.models import Admission
from apps.directions.models import DirectionTranslation
from apps.inquiries.models import Inquiry
from apps.programs.models import Program
from apps.universities.models import University


ACTIVE_ADMISSION_STAGES = (
    "consultation",
    "selection",
    "exams",
    "documents",
)

PIPELINE_STAGES = (
    *ACTIVE_ADMISSION_STAGES,
    "arrival",
)


def _make_aware_start(date_value):
    return timezone.make_aware(
        datetime.combine(date_value, time.min)
    )


def get_inquiry_metrics() -> dict:
    today = timezone.localdate()
    current_month_date = today.replace(day=1)

    if current_month_date.month == 1:
        previous_month_date = current_month_date.replace(
            year=current_month_date.year - 1,
            month=12,
        )
    else:
        previous_month_date = current_month_date.replace(
            month=current_month_date.month - 1,
        )

    current_month_start = _make_aware_start(current_month_date)
    previous_month_start = _make_aware_start(previous_month_date)

    return Inquiry.objects.aggregate(
        total=Count("id"),
        total_before_month=Count(
            "id",
            filter=Q(created_at__lt=current_month_start),
        ),
        unread=Count("id", filter=Q(status="new")),
        new_this_month=Count(
            "id",
            filter=Q(created_at__gte=current_month_start),
        ),
        new_previous_month=Count(
            "id",
            filter=Q(
                created_at__gte=previous_month_start,
                created_at__lt=current_month_start,
            ),
        ),
    )


def get_admission_metrics() -> dict:
    today = timezone.localdate()

    current_week_start_date = today - timezone.timedelta(
        days=today.weekday()
    )
    previous_week_start_date = (
        current_week_start_date - timezone.timedelta(days=7)
    )

    current_week_start = _make_aware_start(
        current_week_start_date
    )
    previous_week_start = _make_aware_start(
        previous_week_start_date
    )

    return Admission.objects.aggregate(
        total=Count("id"),

        active=Count(
            "id",
            filter=Q(stage__in=ACTIVE_ADMISSION_STAGES),
        ),

        consultation=Count(
            "id",
            filter=Q(stage="consultation"),
        ),
        selection=Count(
            "id",
            filter=Q(stage="selection"),
        ),
        exams=Count(
            "id",
            filter=Q(stage="exams"),
        ),
        documents=Count(
            "id",
            filter=Q(stage="documents"),
        ),
        arrival=Count(
            "id",
            filter=Q(stage="arrival"),
        ),
        cancelled=Count(
            "id",
            filter=Q(stage="cancelled"),
        ),

        enrolled_inquiries=Count(
            "inquiry_id",
            distinct=True,
            filter=Q(
                stage="arrival",
                inquiry_id__isnull=False,
            ),
        ),

        current_week=Count(
            "id",
            filter=Q(
                created_at__gte=current_week_start,
                stage__in=ACTIVE_ADMISSION_STAGES,
            ),
        ),
        previous_week=Count(
            "id",
            filter=Q(
                created_at__gte=previous_week_start,
                created_at__lt=current_week_start,
                stage__in=ACTIVE_ADMISSION_STAGES,
            ),
        ),
    )

def get_monthly_inquiry_trends(start_date) -> dict:
    start_datetime = _make_aware_start(start_date)

    rows = (
        Inquiry.objects
        .filter(created_at__gte=start_datetime)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    return {
        row["month"].date().replace(day=1): row["count"]
        for row in rows
    }


def get_direction_distribution() -> list[dict]:
    rows = (
        Admission.objects
        .filter(direction__isnull=False)
        .values("direction_id")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    direction_ids = [
        row["direction_id"]
        for row in rows
    ]

    translations = {
        item.direction_id: item.title
        for item in DirectionTranslation.objects.filter(
            direction_id__in=direction_ids,
            language_code="uz",
        )
    }

    return [
        {
            "name": translations.get(
                row["direction_id"],
                "Noma'lum yo'nalish",
            ),
            "count": row["count"],
        }
        for row in rows
    ]


def get_university_metrics() -> dict:
    return University.objects.aggregate(
        total=Count("id"),
        published=Count(
            "id",
            filter=Q(status="published"),
        ),
    )


def get_program_metrics() -> dict:
    return Program.objects.aggregate(
        total=Count("id"),
        published=Count(
            "id",
            filter=Q(is_published=True),
        ),
    )


def get_weekly_active_admission_metrics() -> dict:
    today = timezone.localdate()

    current_week_start_date = today - timezone.timedelta(
        days=today.weekday()
    )
    previous_week_start_date = (
        current_week_start_date - timezone.timedelta(days=7)
    )

    current_week_start = _make_aware_start(
        current_week_start_date
    )
    previous_week_start = _make_aware_start(
        previous_week_start_date
    )

    return Admission.objects.aggregate(
        current_week=Count(
            "id",
            filter=Q(
                created_at__gte=current_week_start,
                stage__in=ACTIVE_ADMISSION_STAGES,
            ),
        ),
        previous_week=Count(
            "id",
            filter=Q(
                created_at__gte=previous_week_start,
                created_at__lt=current_week_start,
                stage__in=ACTIVE_ADMISSION_STAGES,
            ),
        ),
    )
