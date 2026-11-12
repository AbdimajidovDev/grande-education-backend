
from django.db.models import Q, QuerySet

from apps.inquiries.models import Inquiry


def get_inquiries(
    *,
    assignee_id: int | None = None,
    filters: dict | None = None,
) -> QuerySet[Inquiry]:
    queryset = (
        Inquiry.objects
        .select_related(
            "category",
            "university",
            "assignee",
        )
    )

    if assignee_id is not None:
        queryset = queryset.filter(assignee_id=assignee_id)

    filters = filters or {}

    if status := filters.get("status"):
        queryset = queryset.filter(status=status)

    if category := filters.get("category"):
        queryset = queryset.filter(category__slug=category)

    if university_id := filters.get("university_id"):
        queryset = queryset.filter(university_id=university_id)

    if assignee_filter := filters.get("assignee_id"):
        queryset = queryset.filter(assignee_id=assignee_filter)

    if date_from := filters.get("date_from"):
        queryset = queryset.filter(created_at__date__gte=date_from)

    if date_to := filters.get("date_to"):
        queryset = queryset.filter(created_at__date__lte=date_to)

    if search := filters.get("search"):
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(phone_number__icontains=search)
            | Q(email__icontains=search)
        )

    return queryset.order_by("-created_at")



def get_inquiry_by_id(
    *,
    inquiry_id,
    assignee_id: int | None = None,
) -> Inquiry | None:
    return (
        get_inquiries(assignee_id=assignee_id)
        .filter(pk=inquiry_id)
        .first()
    )



from apps.inquiries.models import InquiryActivity


def get_inquiry_activities(*, inquiry_id):
    return (
        InquiryActivity.objects
        .filter(inquiry_id=inquiry_id)
        .select_related("actor")
        .order_by("-created_at")
    )
