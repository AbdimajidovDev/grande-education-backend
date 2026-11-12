from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class LoginSerializer(TokenObtainPairSerializer):
    """
    Username va password orqali autentifikatsiya.
    Access va refresh tokenlarni yaratadi.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_active:
            self.fail("no_active_account")

        return data


from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.users.models import User


class LoginSerializer(TokenObtainPairSerializer):
    """
    Username va password orqali autentifikatsiya.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_active:
            self.fail("no_active_account")

        return data


class MeRoleSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class MeSerializer(serializers.ModelSerializer):
    roles = MeRoleSerializer(
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
            "is_staff",
            "is_superuser",
            "roles",
        )
        read_only_fields = fields

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    confirm_new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({
                "current_password": "Joriy parol noto'g'ri."
            })

        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError({
                "confirm_new_password": "Yangi parollar mos emas."
            })

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({
                "new_password": "Yangi parol eski paroldan farq qilishi kerak."
            })

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({
                "new_password": list(exc.messages)
            })

        return attrs



class ForgotPasswordSerializer(serializers.Serializer):
    """Parolni tiklash uchun email manzilini qabul qiladi."""

    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """Parolni tiklash uchun foydalanuvchi ma'lumotlarini tekshiradi."""

    uid = serializers.CharField(
        write_only=True,
        trim_whitespace=True,
    )
    token = serializers.CharField(
        write_only=True,
        trim_whitespace=True,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    confirm_new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError({
                "confirm_new_password": "Yangi parollar mos emas."
            })

        return attrs

