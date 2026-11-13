from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.programs.api.permissions import ProgramModelPermissions
from apps.programs.api.serializers import ProgramAdminSerializer
from apps.programs.models import Program


@extend_schema_view(
    list=extend_schema(
        tags=["Admin Programs"],
        summary="List programs",
        description="Returns all programs, including unpublished programs.",
        responses={200: ProgramAdminSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Admin Programs"],
        summary="Create program",
        description=(
            "Creates a program with its translations. "
            "Supports JSON and multipart form data."
        ),
        request=ProgramAdminSerializer,
        responses={201: ProgramAdminSerializer},
    ),
    retrieve=extend_schema(
        tags=["Admin Programs"],
        summary="Retrieve program",
        responses={200: ProgramAdminSerializer},
    ),
    update=extend_schema(
        tags=["Admin Programs"],
        summary="Update program",
        request=ProgramAdminSerializer,
        responses={200: ProgramAdminSerializer},
    ),
    partial_update=extend_schema(
        tags=["Admin Programs"],
        summary="Partially update program",
        request=ProgramAdminSerializer,
        responses={200: ProgramAdminSerializer},
    ),
    destroy=extend_schema(
        tags=["Admin Programs"],
        summary="Delete program",
        responses={204: None},
    ),
)
class ProgramViewSet(viewsets.ModelViewSet):
    serializer_class = ProgramAdminSerializer
    permission_classes = [ProgramModelPermissions]

    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    queryset = (
        Program.objects
        .prefetch_related("translations")
        .all()
    )