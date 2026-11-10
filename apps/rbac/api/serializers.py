
from django.contrib.auth.models import Group, Permission
from rest_framework import serializers


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(
        source="content_type.app_label",
        read_only=True,
    )

    model = serializers.CharField(
        source="content_type.model",
        read_only=True,
    )

    class Meta:
        model = Permission
        fields = [
            "id",
            "name",
            "codename",
            "app_label",
            "model",
        ]


class RoleListSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "user_count",
        ]


class RoleDetailSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "user_count",
            "permissions",
        ]


class RoleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
    )


class RoleUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
    )


class RolePermissionSerializer(serializers.Serializer):
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    def validate_permission_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate permission IDs are not allowed."
            )

        return value


class RoleUsersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=100,
        error_messages={
            "max_length": "Bir so‘rovda ko‘pi bilan 100 ta foydalanuvchini yuborish mumkin.",
        },
    )

    def validate_user_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Foydalanuvchi ID'lari takrorlanmasligi kerak."
            )
        return value


class RoleUserListSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class RoleUsersMutationResponseSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()
    role_name = serializers.CharField()
    user_ids = serializers.ListField(
        child=serializers.IntegerField()
    )
    affected_count = serializers.IntegerField()


class RoleUserPaginatedResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField(help_text="Jami foydalanuvchilar soni.")
    next = serializers.URLField(allow_null=True, help_text="Keyingi sahifa manzili.")
    previous = serializers.URLField(allow_null=True, help_text="Oldingi sahifa manzili.")
    results = RoleUserListSerializer(many=True)


class RoleUserQuerySerializer(serializers.Serializer):
    search = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=100,
        trim_whitespace=True,
    )
    is_active = serializers.BooleanField(required=False)

