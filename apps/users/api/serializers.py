import phonenumbers

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers

from apps.users.models import User


def validate_username(value: str) -> str:
    value = value.strip()

    if not value:
        raise serializers.ValidationError(
            "Username bo'sh bo'lishi mumkin emas."
        )

    username_field = User._meta.get_field("username")

    try:
        username_field.run_validators(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages) from exc

    return value


class PhoneNumberField(serializers.CharField):
    """
    Telefon raqamini tekshiradi va E.164 formatiga o'tkazadi.
    Standart region: Uzbekistan.
    """

    def to_internal_value(self, data):
        value = super().to_internal_value(data)

        if not value:
            return value

        try:
            phone_number = phonenumbers.parse(value, "UZ")
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError(
                "Telefon raqami noto'g'ri formatda."
            )

        if not phonenumbers.is_valid_number(phone_number):
            raise serializers.ValidationError(
                "Kiritilgan telefon raqami haqiqiy emas."
            )

        return phonenumbers.format_number(
            phone_number,
            phonenumbers.PhoneNumberFormat.E164,
        )


class EmployeeRoleSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class EmployeeCreateSerializer(serializers.Serializer):
    """Yangi xodim yaratish uchun input serializer."""

    username = serializers.CharField(max_length=150, validators=[validate_username], )
    password = serializers.CharField(write_only=True, trim_whitespace=False,)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True,)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True,)
    email = serializers.EmailField(required=False, allow_blank=True,)
    phone_number = PhoneNumberField(required=False, allow_blank=True, max_length=20,)
    role_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text=(
            "Xodimga biriktiriladigan rollar ID raqamlari. "
            "Ixtiyoriy. Bir nechta rol ID sini yuborish mumkin. "
            "Bo'sh qoldirilsa, xodim rolsiz yaratiladi."
        ),
    )

    def validate_role_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Rol ID raqamlari takrorlanmasligi kerak."
            )

        return value


class EmployeeUpdateSerializer(serializers.Serializer):
    """Xodim profilini yangilash uchun input serializer."""

    username = serializers.CharField(
        max_length=150,
        required=False,
        validators=[validate_username],
    )
    first_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )
    phone_number = PhoneNumberField(
        required=False,
        allow_blank=True,
        max_length=20,
    )



class EmployeeListSerializer(serializers.ModelSerializer):
    """Xodim ma'lumotlarini API orqali qaytarish uchun serializer."""
    roles = EmployeeRoleSerializer(
        source="groups",
        many=True,
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_active",
            "date_joined",
            "last_login",
            "roles",
        )
        read_only_fields = fields


class EmployeeQuerySerializer(serializers.Serializer):
    search = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    is_active = serializers.BooleanField(required=False)



class EmployeeRoleManagementSerializer(serializers.Serializer):
    role_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=True,
        allow_empty=False,
        write_only=True,
        help_text="Xodimga qo'shiladigan yoki undan olib tashlanadigan rol ID raqamlari.",
    )

    def validate_role_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Rol ID raqamlari takrorlanmasligi kerak."
            )

        return value