
import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.inquiries.api.public.serializers import InquiryCreateSerializer
from apps.inquiries.services.inquiry_service import create_inquiry


class PublicInquiryCreateAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_inquiry"

    @extend_schema(
        tags=["Public - Inquiries"],
        summary="Yangi ariza yuborish",
        description=(
                "Foydalanuvchidan yangi ariza qabul qiladi. "
                "Idempotency-Key orqali takroriy so'rovlarni nazorat qiladi."
        ),
        request=InquiryCreateSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "status": {"type": "string"},
                        },
                    },
                    "requestId": {"type": "string", "format": "uuid"},
                },
            },
            200: {
                "description": "Takroriy so'rov — avval yaratilgan ariza qaytariladi.",
            },
            409: {"description": "Idempotency conflict."},
            422: {"description": "Validation error."},
            429: {"description": "Too many requests."},
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inquiry, created = create_inquiry(serializer.validated_data)

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        response_status = (
            status.HTTP_201_CREATED
            if created
            else status.HTTP_200_OK
        )

        return Response(
            {
                "data": {
                    "id": str(inquiry.id),
                    "status": inquiry.status,
                },
                "requestId": request_id,
            },
            status=response_status,
            headers={"X-Request-ID": request_id},
        )
