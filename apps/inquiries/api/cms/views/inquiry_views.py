
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.inquiries.api.cms.serializers import (
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
    CanAssignInquiry,
    CanChangeInquiry,
    CanChangeInquiryStatus,
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
    update_inquiry_status,
)
from apps.rbac.services.role_service import RoleService



@extend_schema_view(
    get=extend_schema(
        tags=["Admin - Inquiries"],
        summary="Arizalar ro'yxati",
        description="Arizalarni filterlash, qidirish va pagination bilan olish.",
        parameters=[InquiryListQuerySerializer],
        responses={200: InquiryListSerializer(many=True)},
    )
)
class InquiryListAPIView(ListAPIView):
    serializer_class = InquiryListSerializer
    pagination_class = InquiryPagination

    permission_classes = [
        IsAuthenticated,
        CanViewInquiries | CanViewAllInquiries,
    ]


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



@extend_schema_view(
    get=extend_schema(
        tags=["Admin - Inquiries"],
        summary="Ariza tafsilotlari",
        responses={200: InquiryDetailSerializer},
    )
)
class InquiryDetailAPIView(RetrieveAPIView):
    serializer_class = InquiryDetailSerializer
    permission_classes = [IsAuthenticated, CanViewInquiries | CanViewAllInquiries]
    lookup_field = "pk"

    def get_object(self):
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

        self.check_object_permissions(self.request, inquiry)
        return inquiry



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
