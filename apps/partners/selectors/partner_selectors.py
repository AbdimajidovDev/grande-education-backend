
from apps.partners.models import Partner


def get_public_partners():
    """
    Returns active partners for the public website.
    """
    return (
        Partner.objects
        .filter(is_active=True)
        .order_by("order", "name")
    )


def get_admin_partners():
    """
    Returns all partners for admin management.
    """
    return (
        Partner.objects
        .all()
        .order_by("order", "name")
    )


def get_partner_by_id(*, partner_id):
    """
    Returns a single partner by its UUID.
    """
    return Partner.objects.filter(pk=partner_id).first()
