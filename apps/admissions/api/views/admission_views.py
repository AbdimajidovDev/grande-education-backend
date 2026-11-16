
from django.http import Http404

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.pagination import StandardResultsPagination
from apps.admissions.api.permissions import (
    CanViewAdmissions,
    CanViewAllAdmissions,
    CanAddAdmission,
)
from apps.admissions.api.serializers import (
    AdmissionCreateSerializer,
    AdmissionDetailSerializer,
    AdmissionListSerializer,
    AdmissionUpdateSerializer,
)
from apps.admissions.selectors.admission_selector import (
    get_admissions,
    get_admission_by_id,
)
from apps.admissions.services.admission_service import create_admission
from apps.rbac.services.role_service import RoleService

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)

from apps.admissions.api.permissions import CanChangeAdmission
from apps.admissions.api.serializers import AdmissionUpdateSerializer
from apps.admissions.services.admission_service import (
    create_admission,
    update_admission,
)
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)


def _get_admission_curator_scope(user):
    """
    Foydalanuvchining Admission ko'rish doirasini aniqlaydi.

    None — barcha Admissionlar.
    User ID — faqat shu kuratorga biriktirilgan Admissionlar.
    """

    if user.is_superuser:
        return None

    permissions = RoleService._get_actor_role_permissions(user)

    if "admissions.view_all_admissions" in permissions:
        return None

    return user.pk


@extend_schema_view(
    get=extend_schema(
        tags=["Admin - Admissions"],
        summary="Admissionlar ro'yxati",
        description="Admissionlarni pagination bilan qaytaradi.",
        responses={200: AdmissionListSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Admin - Admissions"],
        summary="Yangi Admission yaratish",
        description=(
            "Yangi Admission yaratadi va CREATED hodisasini "
            "faoliyat tarixiga yozadi."
        ),
        request=AdmissionCreateSerializer,
        responses={201: AdmissionDetailSerializer},
    ),
)
class AdmissionListCreateAPIView(ListCreateAPIView):
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        """
        GET va POST uchun alohida permissionlar.
        """

        if self.request.method == "POST":
            permission_classes = [
                IsAuthenticated,
                CanAddAdmission,
            ]
        else:
            permission_classes = [
                IsAuthenticated,
                CanViewAdmissions | CanViewAllAdmissions,
            ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdmissionCreateSerializer

        return AdmissionListSerializer

    def get_queryset(self):
        curator_id = _get_admission_curator_scope(
            self.request.user,
        )

        return get_admissions(
            curator_id=curator_id,
        )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admission = create_admission(
            validated_data=serializer.validated_data,
            actor=request.user,
        )

        response_serializer = AdmissionDetailSerializer(
            admission,
            context=self.get_serializer_context(),
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Admin - Admissions"],
        summary="Admission tafsilotlari",
        responses={200: AdmissionDetailSerializer},
    ),
    put=extend_schema(
        tags=["Admin - Admissions"],
        summary="Admission ma'lumotlarini to'liq yangilash",
        request=AdmissionUpdateSerializer,
        responses={200: AdmissionDetailSerializer},
    ),
    patch=extend_schema(
        tags=["Admin - Admissions"],
        summary="Admission ma'lumotlarini qisman yangilash",
        request=AdmissionUpdateSerializer,
        responses={200: AdmissionDetailSerializer},
    ),
)
class AdmissionDetailAPIView(RetrieveUpdateAPIView):
    lookup_field = "pk"

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            permission_classes = [
                IsAuthenticated,
                CanChangeAdmission,
            ]
        else:
            permission_classes = [
                IsAuthenticated,
                CanViewAdmissions | CanViewAllAdmissions,
            ]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return AdmissionUpdateSerializer

        return AdmissionDetailSerializer

    def get_object(self):
        curator_id = _get_admission_curator_scope(
            self.request.user,
        )

        admission = get_admission_by_id(
            admission_id=self.kwargs["pk"],
            curator_id=curator_id,
        )

        if admission is None:
            raise Http404

        return admission

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        admission = self.get_object()

        serializer = self.get_serializer(
            admission,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        update_admission(
            admission_id=admission.pk,
            validated_data=serializer.validated_data,
            actor=request.user,
        )

        admission.refresh_from_db()

        response_serializer = AdmissionDetailSerializer(
            admission,
            context=self.get_serializer_context(),
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )



@extend_schema_view(
    put=extend_schema(
        tags=["Admin - Admissions"],
        summary="Admission ma'lumotlarini to'liq yangilash",
        request=AdmissionUpdateSerializer,
        responses={200: AdmissionDetailSerializer},
    ),
    patch=extend_schema(
        tags=["Admin - Admissions"],
        summary="Admission ma'lumotlarini qisman yangilash",
        request=AdmissionUpdateSerializer,
        responses={200: AdmissionDetailSerializer},
    ),
)
class AdmissionUpdateAPIView(UpdateAPIView):
    serializer_class = AdmissionUpdateSerializer

    permission_classes = [
        IsAuthenticated,
        CanChangeAdmission,
    ]

    lookup_field = "pk"

    def get_object(self):
        curator_id = _get_admission_curator_scope(
            self.request.user,
        )

        admission = get_admission_by_id(
            admission_id=self.kwargs["pk"],
            curator_id=curator_id,
        )

        if admission is None:
            raise Http404

        return admission

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        admission = self.get_object()

        serializer = self.get_serializer(
            admission,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        update_admission(
            admission_id=admission.pk,
            validated_data=serializer.validated_data,
        )

        admission.refresh_from_db()

        response_serializer = AdmissionDetailSerializer(
            admission,
            context=self.get_serializer_context(),
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
