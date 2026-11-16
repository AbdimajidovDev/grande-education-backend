
from rest_framework import serializers

from apps.admissions.models import Admission, AdmissionActivity


class AdmissionActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionActivity
        fields = [
            "id",
            "actor",
            "action",
            "field_name",
            "old_value",
            "new_value",
            "note",
            "created_at",
        ]
        read_only_fields = fields


class AdmissionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admission
        fields = [
            "id",
            "full_name",
            "phone_number",
            "university",
            "program",
            "direction",
            "stage",
            "curator",
            "created_at",
        ]
        read_only_fields = fields


class AdmissionDetailSerializer(serializers.ModelSerializer):
    activities = AdmissionActivitySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Admission
        fields = [
            "id",
            "inquiry",
            "full_name",
            "passport_full_name",
            "phone_number",
            "email",
            "university",
            "program",
            "direction",
            "hsk_level",
            "stage",
            "curator",
            "created_at",
            "updated_at",
            "activities",
        ]
        read_only_fields = fields


class AdmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admission
        fields = [
            "inquiry",
            "full_name",
            "passport_full_name",
            "phone_number",
            "email",
            "university",
            "program",
            "direction",
            "hsk_level",
        ]


class AdmissionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admission
        fields = [
            "inquiry",
            "full_name",
            "passport_full_name",
            "phone_number",
            "email",
            "university",
            "program",
            "direction",
            "hsk_level",
        ]


class AdmissionStageUpdateSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(
        choices=Admission.Stage.choices,
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class AdmissionCuratorAssignSerializer(serializers.Serializer):
    curator_id = serializers.UUIDField()
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class AdmissionCommentCreateSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
