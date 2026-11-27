
from rest_framework import serializers

from apps.inquiries.models import Inquiry, InquiryCategory
from apps.universities.models import University



class InquiryListSerializer(serializers.ModelSerializer):
    category = serializers.CharField(
        source="category.slug",
        read_only=True,
    )
    university_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    assignee_username = serializers.CharField(
        source="assignee.username",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Inquiry
        fields = (
            "id",
            "full_name",
            "phone_number",
            "email",
            "category",
            "university_id",
            "contact_method",
            "status",
            "assignee_username",
            "created_at",
        )
        read_only_fields = fields



class InquiryListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Inquiry.Status.choices,
        required=False,
    )
    category = serializers.SlugField(
        max_length=120,
        required=False,
    )
    university_id = serializers.UUIDField(
        required=False,
    )
    assignee_id = serializers.IntegerField(
        min_value=1,
        required=False,
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    search = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=False,
    )

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError({
                "date_to": "Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas."
            })

        return attrs



class InquiryDetailSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.slug", read_only=True)
    university_id = serializers.UUIDField(read_only=True, allow_null=True)
    assignee_username = serializers.CharField(
        source="assignee.username",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Inquiry
        fields = (
            "id",
            "full_name",
            "phone_number",
            "email",
            "category",
            "university_id",
            "contact_method",
            "message",
            "consent_accepted",
            "consent_version",
            "locale",
            "status",
            "assignee",
            "assignee_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields



class InquiryStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Inquiry.Status.choices,
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )

    def validate_note(self, value):
        return value.strip()



from apps.users.models import User


class InquiryAssignmentSerializer(serializers.Serializer):
    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee",
        queryset=User.objects.filter(is_active=True),
        allow_null=True,
        required=True,
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )

    def validate_note(self, value):
        return value.strip()



from apps.inquiries.models import InquiryActivity


class InquiryActivitySerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(
        source="actor.username",
        read_only=True,
        default=None,
    )

    class Meta:
        model = InquiryActivity
        fields = (
            "id",
            "action",
            "note",
            "actor_username",
            "created_at",
        )
        read_only_fields = fields



class InquiryCommentCreateSerializer(serializers.Serializer):
    note = serializers.CharField(
        max_length=1000,
        allow_blank=False,
        trim_whitespace=True,
    )


class InquiryAdminValidationMixin:
    def validate_full_name(self, value):
        if not value:
            raise serializers.ValidationError("Ism va familiya kiritilishi shart.")
        return value

    def validate_phone_number(self, value):
        if not value:
            raise serializers.ValidationError("Telefon raqami kiritilishi shart.")
        return value

    def validate_locale(self, value):
        value = value.lower()
        if not value:
            raise serializers.ValidationError("Til kodi kiritilishi shart.")
        return value


class AdminInquiryCreateSerializer(InquiryAdminValidationMixin, serializers.Serializer):
    full_name = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )
    phone_number = serializers.CharField(
        max_length=20,
        trim_whitespace=True,
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default="",
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=InquiryCategory.objects.filter(is_active=True),
    )
    university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )
    contact_method = serializers.ChoiceField(
        choices=Inquiry.ContactMethod.choices,
        required=False,
        default=Inquiry.ContactMethod.PHONE,
    )
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    locale = serializers.CharField(
        max_length=10,
        required=False,
        default="uz",
        trim_whitespace=True,
    )
    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee",
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        default=None,
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=1000,
        trim_whitespace=True,
    )


class AdminInquiryUpdateSerializer(InquiryAdminValidationMixin, serializers.Serializer):
    full_name = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )
    phone_number = serializers.CharField(
        max_length=20,
        trim_whitespace=True,
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=InquiryCategory.objects.all(),
    )
    university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),
        required=False,
        allow_null=True,
    )
    contact_method = serializers.ChoiceField(
        choices=Inquiry.ContactMethod.choices,
        required=False,
    )
    message = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    locale = serializers.CharField(
        max_length=10,
        required=False,
        trim_whitespace=True,
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=1000,
        trim_whitespace=True,
    )

    def validate_category(self, value):
        if not value.is_active and (
            self.instance is None or self.instance.category_id != value.pk
        ):
            raise serializers.ValidationError("Tanlangan kategoriya faol emas.")
        return value
