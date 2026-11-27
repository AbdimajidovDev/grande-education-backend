
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view

from apps.inquiries.api.cms.serializers import (
    AdminInquiryCreateSerializer,
    InquiryActivitySerializer,
    InquiryAssignmentSerializer,
    InquiryCommentCreateSerializer,
    InquiryDetailSerializer,
    InquiryListQuerySerializer,
    InquiryListSerializer,
    InquiryStatusUpdateSerializer,
)
from apps.inquiries.api.pagination import InquiryPagination
from apps.inquiries.api.permissions import (
    CanAddInquiry,
    CanAssignInquiry,
    CanChangeInquiry,
    CanChangeInquiryStatus,
    CanDeleteInquiry,
    CanViewAllInquiries,
    CanViewInquiries,
    CanViewInquiryActivity,
)
from apps.inquiries.selectors.inquiry_selector import (
    get_inquiries,
    get_inquiry_by_id,
    get_inquiry_activities,
)
from apps.inquiries.services.inquiry_service import (
    add_inquiry_comment,
    assign_inquiry,
    create_admin_inquiry,
    delete_inquiry,
    update_inquiry_status,
)
from apps.rbac.services.role_service import RoleService


def _get_inquiry_assignee_scope(user):
    """Barcha arizalarni ko'rish huquqi bo'lmagan xodim uchun assignee scope qaytaradi."""
    if user.is_superuser:
        return None

    permissions = RoleService._get_actor_role_permissions(user)
    if "inquiries.view_all_inquiries" in permissions:
        return None

    return user.pk



@extend_schema_view(
    get=extend_schema(
        tags=["Admin - Inquiries"],
        summary="Arizalar ro'yxati",
        description="Arizalarni filterlash, qidirish va pagination bilan olish.",
        parameters=[InquiryListQuerySerializer],
        responses={200: InquiryListSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Admin - Inquiries"],
        summary="Admin tomonidan yangi lead (ariza) yaratish",
        description=(
            "Call center yoki admin operatori mijoz nomidan yangi lead "
            "(Inquiry) yaratadi va CREATED hodisasini tarixga yozadi."
        ),
        request=AdminInquiryCreateSerializer,
        responses={201: InquiryDetailSerializer},
    ),
)
class InquiryListCreateAPIView(ListCreateAPIView):
    pagination_class = InquiryPagination

    def get_permissions(self):
        if self.request.method == "POST":
            permission_classes = [IsAuthenticated, CanAddInquiry]
        else:
            permission_classes = [
                IsAuthenticated,
                CanViewInquiries | CanViewAllInquiries,
            ]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminInquiryCreateSerializer
        return InquiryListSerializer

    def get_queryset(self):
        user = self.request.user

        query_serializer = InquiryListQuerySerializer(
            data=self.request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        filters = query_serializer.validated_data

        if user.is_superuser:
            return get_inquiries(filters=filters)

        permissions = RoleService._get_actor_role_permissions(user)

        if "inquiries.view_all_inquiries" in permissions:
            return get_inquiries(filters=filters)

        return get_inquiries(
            assignee_id=user.pk,
            filters=filters,
        )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inquiry = create_admin_inquiry(
            validated_data=serializer.validated_data,
            actor=request.user,
        )

        return Response(
            InquiryDetailSerializer(inquiry).data,
            status=status.HTTP_201_CREATED,
        )


InquiryListAPIView = InquiryListCreateAPIView



@extend_schema_view(
    get=extend_schema(
        tags=["Admin - Inquiries"],
        summary="Ariza tafsilotlari",
        responses={200: InquiryDetailSerializer},
    ),
    delete=extend_schema(
        tags=["Admin - Inquiries"],
        summary="Arizani o'chirish",
        description=(
            "Arizani va unga bog'liq harakatlar tarixini o'chiradi. "
            "Talab qilinadigan permission: inquiries.delete_inquiry. "
            "inquiries.view_all_inquiries huquqi bo'lmagan xodim faqat "
            "o'ziga biriktirilgan arizani o'chira oladi."
        ),
        responses={
            204: OpenApiResponse(description="Ariza muvaffaqiyatli o'chirildi."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
            404: OpenApiResponse(description="Inquiry not found."),
        },
    ),
)
class InquiryDetailAPIView(RetrieveDestroyAPIView):
    serializer_class = InquiryDetailSerializer
    lookup_field = "pk"

    def get_permissions(self):
        if self.request.method == "DELETE":
            permission_classes = [IsAuthenticated, CanDeleteInquiry]
        else:
            permission_classes = [
                IsAuthenticated,
                CanViewInquiries | CanViewAllInquiries,
            ]
        return [permission() for permission in permission_classes]

    def get_object(self):
        assignee_id = _get_inquiry_assignee_scope(self.request.user)

        inquiry = get_inquiry_by_id(
            inquiry_id=self.kwargs["pk"],
            assignee_id=assignee_id,
        )

        if inquiry is None:
            raise Http404

        self.check_object_permissions(self.request, inquiry)
        return inquiry

    def perform_destroy(self, instance):
        try:
            delete_inquiry(
                inquiry_id=instance.pk,
                actor=self.request.user,
            )
        except DjangoPermissionDenied as exc:
            raise DRFPermissionDenied(str(exc)) from exc



class InquiryStatusUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, CanChangeInquiryStatus]

    @extend_schema(
        tags=["Admin - Inquiries"],
        summary="Ariza statusini o'zgartirish",
        request=InquiryStatusUpdateSerializer,
        responses={200: InquiryDetailSerializer},
    )
    def patch(self, request, pk):
        user = request.user
        permissions = RoleService._get_actor_role_permissions(user)

        assignee_id = None
        if not user.is_superuser and "inquiries.view_all_inquiries" not in permissions:
            assignee_id = user.pk

        inquiry = get_inquiry_by_id(
            inquiry_id=pk,
            assignee_id=assignee_id,
        )

        if inquiry is None:
            from django.http import Http404
            raise Http404

        serializer = InquiryStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_inquiry = update_inquiry_status(
            inquiry_id=inquiry.pk,
            status=serializer.validated_data["status"],
            actor=user,
            note=serializer.validated_data.get("note", ""),
        )

        return Response(
            InquiryDetailSerializer(updated_inquiry).data,
            status=status.HTTP_200_OK,
        )



class InquiryAssignmentAPIView(APIView):
    permission_classes = [IsAuthenticated, CanAssignInquiry]

    @extend_schema(
        tags=["Admin - Inquiries"],
        summary="Arizani xodimga biriktirish",
        request=InquiryAssignmentSerializer,
        responses={200: InquiryDetailSerializer},
    )
    def patch(self, request, pk):
        user = request.user
        permissions = RoleService._get_actor_role_permissions(user)

        assignee_id = None
        if not user.is_superuser and "inquiries.view_all_inquiries" not in permissions:
            assignee_id = user.pk

        inquiry = get_inquiry_by_id(
            inquiry_id=pk,
            assignee_id=assignee_id,
        )

        if inquiry is None:
            from django.http import Http404
            raise Http404

        serializer = InquiryAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_inquiry = assign_inquiry(
            inquiry_id=inquiry.pk,
            assignee=serializer.validated_data["assignee"],
            actor=user,
            note=serializer.validated_data.get("note", ""),
        )

        return Response(
            InquiryDetailSerializer(updated_inquiry).data,
            status=status.HTTP_200_OK,
        )



@extend_schema_view(
    get=extend_schema(
        tags=["Admin - Inquiries"],
        summary="Ariza harakatlari tarixi",
        responses={200: InquiryActivitySerializer(many=True)},
    )
)
class InquiryActivityListAPIView(ListAPIView):
    serializer_class = InquiryActivitySerializer
    permission_classes = [IsAuthenticated, CanViewInquiryActivity]

    def get_queryset(self):
        user = self.request.user
        permissions = RoleService._get_actor_role_permissions(user)

        assignee_id = None
        if not user.is_superuser and "inquiries.view_all_inquiries" not in permissions:
            assignee_id = user.pk

        inquiry = get_inquiry_by_id(
            inquiry_id=self.kwargs["pk"],
            assignee_id=assignee_id,
        )

        if inquiry is None:
            from django.http import Http404
            raise Http404

        return get_inquiry_activities(inquiry_id=inquiry.pk)




class InquiryCommentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, CanChangeInquiry]

    @extend_schema(
        tags=["Admin - Inquiries"],
        summary="Arizaga izoh qo'shish",
        request=InquiryCommentCreateSerializer,
        responses={201: InquiryActivitySerializer},
    )
    def post(self, request, pk):
        user = request.user
        permissions = RoleService._get_actor_role_permissions(user)

        assignee_id = None
        if not user.is_superuser and "inquiries.view_all_inquiries" not in permissions:
            assignee_id = user.pk

        inquiry = get_inquiry_by_id(
            inquiry_id=pk,
            assignee_id=assignee_id,
        )

        if inquiry is None:
            from django.http import Http404
            raise Http404

        serializer = InquiryCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activity = add_inquiry_comment(
            inquiry_id=inquiry.pk,
            actor=user,
            note=serializer.validated_data["note"],
        )

        return Response(
            InquiryActivitySerializer(activity).data,
            status=status.HTTP_201_CREATED,
        )
