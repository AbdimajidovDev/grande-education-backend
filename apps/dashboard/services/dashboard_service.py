
from datetime import date

from django.utils import timezone

from apps.dashboard.selectors.dashboard_selector import (
    get_admission_metrics,
    get_direction_distribution,
    get_inquiry_metrics,
    get_monthly_inquiry_trends,
    get_program_metrics,
    get_university_metrics,
)


MONTH_NAMES = {
    1: "Yan",
    2: "Fev",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Iyun",
    7: "Iyul",
    8: "Avg",
    9: "Sen",
    10: "Okt",
    11: "Noy",
    12: "Dek",
}


def calculate_percentage_growth(
    current: int,
    previous: int,
) -> str | None:
    if previous == 0:
        return None

    growth = ((current - previous) / previous) * 100
    return f"{growth:+.1f}%"


def calculate_percentage(
    numerator: int,
    denominator: int,
) -> str:
    if denominator == 0:
        return "0.0%"

    percentage = (numerator / denominator) * 100
    return f"{percentage:.1f}%"


def get_six_months_start_date(today: date) -> date:
    month = today.month - 5
    year = today.year

    while month <= 0:
        month += 12
        year -= 1

    return date(year, month, 1)


def build_monthly_trends(data: dict, today: date) -> list[dict]:
    start_date = get_six_months_start_date(today)

    trends = []
    year = start_date.year
    month = start_date.month

    for _ in range(6):
        month_date = date(year, month, 1)

        trends.append({
            "month": MONTH_NAMES[month],
            "count": data.get(month_date, 0),
        })

        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

    return trends


def build_directions_distribution(rows: list[dict]) -> list[dict]:
    total = sum(row["count"] for row in rows)

    return [
        {
            "name": row["name"],
            "count": row["count"],
            "percentage": round(
                (row["count"] / total) * 100
            ) if total else 0,
        }
        for row in rows
    ]


def get_dashboard_overview() -> dict:
    today = timezone.localdate()

    inquiries = get_inquiry_metrics()
    admissions = get_admission_metrics()
    universities = get_university_metrics()
    programs = get_program_metrics()

    monthly_start = get_six_months_start_date(today)
    monthly_data = get_monthly_inquiry_trends(monthly_start)

    directions = get_direction_distribution()

    active_admissions_growth = (
            admissions["current_week"]
            - admissions["previous_week"]
    )

    return {
        "kpi": {
            "total_leads": inquiries["total"],
            "total_leads_growth": calculate_percentage_growth(
                inquiries["total"],
                inquiries["total_before_month"],
            ),
            "new_leads": inquiries["new_this_month"],
            "active_admissions": admissions["active"],
            "active_admissions_growth": (
                f"{active_admissions_growth:+d} nafar bu hafta"
            ),
            "enrolled_rate": calculate_percentage(
                admissions["enrolled_inquiries"],
                inquiries["total"],
            ),
            "total_universities": universities["total"],
            "total_programs": programs["total"],
        },
        "pipeline_stages": {
            "CONSULTATION": admissions["consultation"],
            "SELECTION": admissions["selection"],
            "EXAMS": admissions["exams"],
            "DOCUMENTS": admissions["documents"],
            "ARRIVAL": admissions["arrival"],
        },
        "monthly_trends": build_monthly_trends(
            monthly_data,
            today,
        ),
        "directions_distribution": build_directions_distribution(
            directions,
        ),
    }
