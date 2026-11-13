
import uuid

from django.db import models
from django.db.models import Q


class Program(models.Model):

    class Category(models.TextChoices):
        LANGUAGE = "language", "Language"
        PROFESSION = "profession", "Profession"

    class Format(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        HYBRID = "hybrid", "Hybrid"

    class PricingType(models.TextChoices):
        FREE = "free", "Free"
        PAID = "paid", "Paid"

    class PricePeriod(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ONE_TIME = "one_time", "One time"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )

    duration = models.CharField(
        max_length=100,
    )

    format = models.CharField(
        max_length=20,
        choices=Format.choices,
    )

    pricing_type = models.CharField(
        max_length=10,
        choices=PricingType.choices,
    )

    price_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        default="UZS",
    )

    price_period = models.CharField(
        max_length=20,
        choices=PricePeriod.choices,
        null=True,
        blank=True,
    )

    image = models.ImageField(
        upload_to="programs/",
        null=True,
        blank=True,
    )

    order = models.PositiveIntegerField(default=0)

    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "programs"
        ordering = ["order", "-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        pricing_type="free",
                        price_amount__isnull=True,
                        price_period__isnull=True,
                    )
                    | Q(
                        pricing_type="paid",
                        price_amount__gt=0,
                        price_period__isnull=False,
                    )
                ),
                name="valid_program_pricing",
            ),
        ]

        indexes = [
            models.Index(
                fields=["is_published", "order"],
                name="programs_published_order_idx",
            ),
            models.Index(
                fields=["category", "is_published"],
                name="programs_category_pub_idx",
            ),
        ]

    def __str__(self):
        return self.slug
