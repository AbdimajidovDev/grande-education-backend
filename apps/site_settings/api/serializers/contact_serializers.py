
import re

from rest_framework import serializers

from apps.site_settings.models import (
    Office,
    ContactInfo,
    ContactAddress,
    WorkingHour,
    SocialLink,
)


class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = (
            "phone_raw",
            "email",
        )

    def validate_phone_raw(self, value):
        value = value.strip()

        if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
            raise serializers.ValidationError(
                "Phone number must be in international format, "
                "for example: +998705166600."
            )

        return value

    def validate_email(self, value):
        return value.strip().lower()


class ContactAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactAddress
        fields = (
            "city",
            "street",
            "landmark",
            "map_url",
        )

    def validate_city(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "City cannot be empty."
            )

        return value

    def validate_street(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Street cannot be empty."
            )

        return value

    def validate_landmark(self, value):
        return value.strip()

    def validate_map_url(self, value):
        value = value.strip()

        if not value.startswith("https://"):
            raise serializers.ValidationError(
                "Map URL must use HTTPS."
            )

        return value


class WorkingHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHour
        fields = (
            "weekday",
            "opens_at",
            "closes_at",
            "is_closed",
        )

    def validate(self, attrs):
        is_closed = attrs.get(
            "is_closed",
            getattr(self.instance, "is_closed", False),
        )

        opens_at = attrs.get(
            "opens_at",
            getattr(self.instance, "opens_at", None),
        )

        closes_at = attrs.get(
            "closes_at",
            getattr(self.instance, "closes_at", None),
        )

        if is_closed:
            if opens_at is not None or closes_at is not None:
                raise serializers.ValidationError(
                    "Closed days must not have opening or closing times."
                )
        else:
            if opens_at is None or closes_at is None:
                raise serializers.ValidationError(
                    "Opening and closing times are required."
                )

            if opens_at >= closes_at:
                raise serializers.ValidationError(
                    "Closing time must be later than opening time."
                )

        return attrs


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = (
            "platform",
            "username",
            "url",
            "is_active",
            "order",
        )

    def validate_username(self, value):
        return value.strip()

    def validate_url(self, value):
        value = value.strip()

        if not value.startswith("https://"):
            raise serializers.ValidationError(
                "Social media URL must use HTTPS."
            )

        return value


class OfficeAdminSerializer(serializers.ModelSerializer):
    contact_info = ContactInfoSerializer()
    address = ContactAddressSerializer()

    working_hours = WorkingHourSerializer(
        many=True,
        required=False,
    )

    social_links = SocialLinkSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = Office
        fields = (
            "id",
            "name",
            "is_active",
            "is_main",
            "contact_info",
            "address",
            "working_hours",
            "social_links",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = " ".join(value.split())

        if not value:
            raise serializers.ValidationError(
                "Office name cannot be empty."
            )

        queryset = Office.objects.filter(name__iexact=value)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "An office with this name already exists."
            )

        return value

    def validate_working_hours(self, value):
        weekdays = [item["weekday"] for item in value]

        if len(weekdays) != len(set(weekdays)):
            raise serializers.ValidationError(
                "A weekday can only be specified once per office."
            )

        return value

    def validate_social_links(self, value):
        platforms = [item["platform"] for item in value]

        if len(platforms) != len(set(platforms)):
            raise serializers.ValidationError(
                "A social platform can only be specified once per office."
            )

        return value



from rest_framework import serializers


WEEKDAY_NAMES_UZ = {
    1: "Dushanba",
    2: "Seshanba",
    3: "Chorshanba",
    4: "Payshanba",
    5: "Juma",
    6: "Shanba",
    7: "Yakshanba",
}


def format_phone_number(phone_raw):
    """
    Format Uzbek phone numbers for frontend display.
    Keep other international numbers unchanged.
    """
    if phone_raw.startswith("+998") and len(phone_raw) == 13:
        return (
            f"+998 {phone_raw[4:6]} "
            f"{phone_raw[6:9]} "
            f"{phone_raw[9:11]} "
            f"{phone_raw[11:13]}"
        )

    return phone_raw


def format_weekday_range(weekdays):
    names = [WEEKDAY_NAMES_UZ[day] for day in weekdays]

    if len(names) == 1:
        return names[0]

    if all(
        weekdays[index] + 1 == weekdays[index + 1]
        for index in range(len(weekdays) - 1)
    ):
        return f"{names[0]} — {names[-1]}"

    return ", ".join(names)


def format_working_hours(working_hours):
    """
    Group consecutive days with identical working schedules.

    Example:
    {
        "days": "Dushanba — Shanba; Yakshanba",
        "time": "09:00 — 19:00; Yopiq"
    }
    """
    if not working_hours:
        return {
            "days": "",
            "time": "",
        }

    groups = []

    for item in working_hours:
        if item.is_closed:
            schedule = "closed"
            time_label = "Yopiq"
        else:
            schedule = (
                item.opens_at,
                item.closes_at,
            )
            time_label = (
                f"{item.opens_at.strftime('%H:%M')} — "
                f"{item.closes_at.strftime('%H:%M')}"
            )

        if groups and groups[-1]["schedule"] == schedule:
            groups[-1]["weekdays"].append(item.weekday)
        else:
            groups.append({
                "schedule": schedule,
                "time": time_label,
                "weekdays": [item.weekday],
            })

    return {
        "days": "; ".join(
            format_weekday_range(group["weekdays"])
            for group in groups
        ),
        "time": "; ".join(
            group["time"]
            for group in groups
        ),
    }


class SocialLinkPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = (
            "username",
            "url",
        )


class ContactPublicSerializer(serializers.Serializer):
    phone = serializers.SerializerMethodField()
    phone_raw = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    telegram = serializers.SerializerMethodField()
    instagram = serializers.SerializerMethodField()
    facebook = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    working_hours = serializers.SerializerMethodField()

    def get_contact_info(self, obj):
        try:
            return obj.contact_info
        except ContactInfo.DoesNotExist:
            return None

    def get_phone(self, obj):
        contact = self.get_contact_info(obj)
        return format_phone_number(contact.phone_raw) if contact else ""

    def get_phone_raw(self, obj):
        contact = self.get_contact_info(obj)
        return contact.phone_raw if contact else ""

    def get_email(self, obj):
        contact = self.get_contact_info(obj)
        return contact.email if contact else ""

    def get_social_link(self, obj, platform):
        return next(
            (
                link
                for link in obj.available_social_links
                if link.platform == platform
            ),
            None,
        )

    def serialize_social_link(self, obj, platform):
        link = self.get_social_link(obj, platform)

        if not link:
            return {}

        data = {
            "url": link.url,
        }

        if link.username:
            data["username"] = link.username

        return data

    def get_telegram(self, obj):
        return self.serialize_social_link(obj, "telegram")

    def get_instagram(self, obj):
        return self.serialize_social_link(obj, "instagram")

    def get_facebook(self, obj):
        return self.serialize_social_link(obj, "facebook")

    def get_address(self, obj):
        try:
            address = obj.address
        except ContactAddress.DoesNotExist:
            return {
                "city": "",
                "street": "",
                "landmark": "",
                "map_url": "",
            }

        return {
            "city": address.city,
            "street": address.street,
            "landmark": address.landmark,
            "map_url": address.map_url,
        }

    def get_working_hours(self, obj):
        return format_working_hours(
            obj.available_working_hours
        )

