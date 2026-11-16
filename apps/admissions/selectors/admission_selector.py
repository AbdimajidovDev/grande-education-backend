
from django.db.models import Q, QuerySet

from apps.admissions.models import Admission


def get_admissions(
    *,
    stage: str | None = None,
    curator_id=None,
    university_id=None,
    program_id=None,
    inquiry_id=None,
    search: str | None = None,
    date_from=None,
    date_to=None,
) -> QuerySet[Admission]:
    """
    Admission yozuvlarini filterlar asosida qaytaradi.
    """

    queryset = (
        Admission.objects
        .select_related(
            "inquiry",
            "university",
            "program",
            "direction",
            "curator",
        )
    )

    if stage:
        queryset = queryset.filter(stage=stage)

    if curator_id is not None:
        queryset = queryset.filter(curator_id=curator_id)

    if university_id is not None:
        queryset = queryset.filter(university_id=university_id)

    if program_id is not None:
        queryset = queryset.filter(program_id=program_id)

    if inquiry_id is not None:
        queryset = queryset.filter(inquiry_id=inquiry_id)

    if search:
        search = search.strip()

        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(passport_full_name__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(email__icontains=search)
            )

    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)

    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    return queryset.order_by("-created_at")


def get_admission_by_id(
    *,
    admission_id,
    curator_id=None,
) -> Admission | None:
    return (
        get_admissions(curator_id=curator_id)
        .prefetch_related("activities__actor")
        .filter(pk=admission_id)
        .first()
    )

