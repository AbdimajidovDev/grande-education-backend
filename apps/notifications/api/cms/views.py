from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsPagination
from apps.notifications.api.cms.serializers import (
    MarkAllReadResponseSerializer,
    NotificationListQuerySerializer,
    NotificationSerializer,
    UnreadCountSerializer,
)
from apps.notifications.api.permissions import IsActiveEmployee
from apps.notifications.selectors.notification_selectors import (
    get_unread_count,
    get_user_notifications,
)
from apps.notifications.services import (
    NotificationNotFoundError,
    NotificationService,
)

TAGS = ["Admin - Notifications"]

COMMON_ERRORS = {
    401: OpenApiResponse(description="Authentication required."),
    403: OpenApiResponse(description="Faol xodim emas."),
}


@extend_schema_view(
    get=extend_schema(
        tags=TAGS,
        summary="Mening bildirishnomalarim",
        description=(
            "Joriy xodimning bildirishnomalari, eng yangisi birinchi. "
            "`is_read` bo'yicha filter va pagination (`page`, `page_size`)."
        ),
        parameters=[NotificationListQuerySerializer],
        responses={200: NotificationSerializer(many=True), **COMMON_ERRORS},
    ),
)
class NotificationListAPIView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsActiveEmployee]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        query_serializer = NotificationListQuerySerializer(
            data=self.request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        return get_user_notifications(
            user_id=self.request.user.pk,
            is_read=query_serializer.validated_data.get("is_read"),
        )


class NotificationUnreadCountAPIView(APIView):
    permission_classes = [IsAuthenticated, IsActiveEmployee]

    @extend_schema(
        tags=TAGS,
        summary="O'qilmagan bildirishnomalar soni",
        responses={200: UnreadCountSerializer, **COMMON_ERRORS},
    )
    def get(self, request):
        return Response(
            {"unread_count": get_unread_count(user_id=request.user.pk)},
            status=status.HTTP_200_OK,
        )


class NotificationMarkReadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsActiveEmployee]

    @extend_schema(
        tags=TAGS,
        summary="Bildirishnomani o'qilgan qilish",
        description=(
            "Idempotent. Boshqa xodimga tegishli yoki mavjud bo'lmagan ID "
            "uchun 404 qaytariladi."
        ),
        request=None,
        responses={
            200: NotificationSerializer,
            404: OpenApiResponse(description="Bildirishnoma topilmadi."),
            **COMMON_ERRORS,
        },
    )
    def patch(self, request, notification_id):
        try:
            notification = NotificationService.mark_as_read(
                user=request.user,
                notification_id=notification_id,
            )
        except NotificationNotFoundError as exc:
            raise Http404 from exc

        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK,
        )


class NotificationMarkAllReadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsActiveEmployee]

    @extend_schema(
        tags=TAGS,
        summary="Barcha bildirishnomalarni o'qilgan qilish",
        request=None,
        responses={200: MarkAllReadResponseSerializer, **COMMON_ERRORS},
    )
    def post(self, request):
        updated_count = NotificationService.mark_all_as_read(user=request.user)

        return Response(
            {
                "updated_count": updated_count,
                "unread_count": get_unread_count(user_id=request.user.pk),
            },
            status=status.HTTP_200_OK,
        )
