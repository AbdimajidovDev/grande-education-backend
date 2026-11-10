
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.services.role_service import RoleService
from apps.rbac.selectors.role_selectors import RoleSelector
from apps.rbac.api.serializers import (
    PermissionSerializer,
    RoleListSerializer,
    RoleDetailSerializer,
    RoleCreateSerializer,
    RoleUpdateSerializer,
    RolePermissionSerializer,
    RoleUserQuerySerializer,
)

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
    inline_serializer,
)
from apps.rbac.permissions.role_permissions import (
    CanManageRoles,
    CanViewUsers,
)
from apps.rbac.api.serializers import (
    RoleUserListSerializer,
    RoleUserPaginatedResponseSerializer
)

from django.http import Http404

from apps.common.pagination import StandardResultsPagination




def handle_service_validation_error(exc):
    """
    Convert Django validation errors into DRF validation errors.
    """
    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)

    raise serializers.ValidationError(exc.messages)


class RoleListCreateAPIView(APIView):
    permission_classes = [CanManageRoles]

    @extend_schema(
        operation_id="rbac_list_roles",
        tags=["RBAC - Roles"],
        summary="Barcha rollarni olish",
        description=(
            "Retrieves all roles registered in the system. "
            "Returns role ID, name and the number of users "
            "assigned to each role. Requires authentication."
        ),
        responses={
            200: RoleListSerializer(many=True),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def get(self, request):
        roles = RoleSelector.get_roles()

        serializer = RoleListSerializer(
            roles,
            many=True,
        )

        return Response(serializer.data)

    @extend_schema(
        operation_id="rbac_create_role",
        tags=["RBAC - Roles"],
        summary="Create a new role",
        description=(
            "Creates a new role in the system. "
            "Only Super Admin or a user with the "
            "rbac.manage_roles permission can perform this operation. "
            "Role names must be unique, case-insensitively."
        ),
        request=RoleCreateSerializer,
        responses={
            201: OpenApiResponse(response=RoleDetailSerializer, description="Role successfully created.",),
            400: OpenApiResponse(description="Invalid input or duplicate role name."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
        },
        examples=[
            OpenApiExample(
                "Create role request",
                value={"name": "Content Editor"},
                request_only=True,
            ),
            OpenApiExample(
                "Successful response",
                value={
                    "id": 5,
                    "name": "Content Editor",
                    "user_count": 0,
                    "permissions": [],
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def post(self, request):
        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            role = RoleService.create_role(
                name=serializer.validated_data["name"],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)

        return Response(
            RoleDetailSerializer(role).data,
            status=status.HTTP_201_CREATED,
        )


class RoleDetailAPIView(APIView):
    permission_classes = [CanManageRoles]

    @extend_schema(
        operation_id="rbac_get_role_detail",
        tags=["RBAC - Roles"],
        summary="Get role details",
        description=(
            "Retrieves detailed information about a specific role, "
            "including its ID, name, assigned permissions and user count. "
            "Authentication is required."
        ),
        responses={
            200: RoleDetailSerializer,
            401: OpenApiResponse(
                description="Authentication credentials are missing or invalid."
            ),
            404: OpenApiResponse(
                description="The requested role does not exist."
            ),
        },
        examples=[
            OpenApiExample(
                "Successful response",
                value={
                    "id": 5,
                    "name": "Content Editor",
                    "user_count": 3,
                    "permissions": [
                        {
                            "id": 12,
                            "name": "Can view university",
                            "codename": "view_university",
                            "app_label": "universities",
                            "model": "university",
                        }
                    ],
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Role not found",
                value={"detail": "Role not found."},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def get(self, request, role_id):
        """
        Retrieve a specific role.
        """
        role = RoleSelector.get_role_by_id(role_id=role_id)

        if role is None:
            return Response(
                {"detail": "Role not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(RoleDetailSerializer(role).data)

    @extend_schema(
        operation_id="rbac_update_role",
        tags=["RBAC - Roles"],
        summary="Update role",
        description=(
            "Updates the name of an existing role. "
            "Only Super Admin or users with rbac.manage_roles "
            "permission can perform this operation. "
            "The role ID, assigned users and permissions remain unchanged. "
            "Role names must be unique, case-insensitively."
        ),
        request=RoleUpdateSerializer,
        responses={
            200: RoleDetailSerializer,
            400: OpenApiResponse(
                description="Invalid role name or duplicate role name."
            ),
            401: OpenApiResponse(
                description="Authentication credentials are missing or invalid."
            ),
            403: OpenApiResponse(
                description="Insufficient permissions."
            ),
            404: OpenApiResponse(
                description="The requested role does not exist."
            ),
        },
        examples=[
            OpenApiExample(
                "Update role request",
                value={"name": "Senior Content Editor"},
                request_only=True,
            ),
            OpenApiExample(
                "Successful response",
                value={
                    "id": 5,
                    "name": "Senior Content Editor",
                    "user_count": 3,
                    "permissions": [],
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def put(self, request, role_id):
        """
        Update an existing role.
        """
        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            role = RoleService.update_role(
                role_id=role_id,
                name=serializer.validated_data["name"],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)

        return Response(RoleDetailSerializer(role).data)

    @extend_schema(
        operation_id="rbac_delete_role",
        tags=["RBAC - Roles"],
        summary="Delete role",
        description=(
            "Deletes an existing role. "
            "Only Super Admin or users with rbac.manage_roles "
            "permission can perform this operation. "
            "A role assigned to one or more users cannot be deleted. "
            "All assigned users must be reassigned before deletion."
        ),
        responses={
            204: OpenApiResponse(
                description="Role successfully deleted. No response body."
            ),
            400: OpenApiResponse(
                description="Role cannot be deleted because users are assigned to it."
            ),
            401: OpenApiResponse(
                description="Authentication credentials are missing or invalid."
            ),
            403: OpenApiResponse(
                description="Insufficient permissions."
            ),
            404: OpenApiResponse(
                description="The requested role does not exist."
            ),
        },
        examples=[
            OpenApiExample(
                "Role cannot be deleted",
                value={
                    "role": [
                        "Cannot delete a role assigned to users. "
                        "Reassign users before deleting this role."
                    ]
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def delete(self, request, role_id):
        """
        Delete an existing role.
        """
        try:
            RoleService.delete_role(
                role_id=role_id,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)


class RolePermissionAPIView(APIView):
    permission_classes = [CanManageRoles]

    @extend_schema(
        operation_id="rbac_get_role_permissions",
        tags=["RBAC - Permissions"],
        summary="Get role permissions",
        description=(
            "Retrieves all permissions currently assigned to a specific role. "
            "Returns permission ID, name, codename, application label and model. "
            "Authentication is required."
        ),
        responses={
            200: PermissionSerializer(many=True),
            401: OpenApiResponse(
                description="Authentication credentials are missing or invalid."
            ),
            404: OpenApiResponse(
                description="The requested role does not exist."
            ),
        },
        examples=[
            OpenApiExample(
                "Successful response",
                value=[
                    {
                        "id": 12,
                        "name": "Can view university",
                        "codename": "view_university",
                        "app_label": "universities",
                        "model": "university",
                    },
                    {
                        "id": 13,
                        "name": "Can add university",
                        "codename": "add_university",
                        "app_label": "universities",
                        "model": "university",
                    },
                ],
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request, role_id):
        """
        Retrieve permissions assigned to a role.
        """
        role = RoleSelector.get_role_by_id(role_id=role_id)

        if role is None:
            return Response(
                {"detail": "Role not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        permissions = RoleSelector.get_role_permissions(
            role_id=role_id,
        )

        serializer = PermissionSerializer(
            permissions,
            many=True,
        )

        return Response(serializer.data)

    @extend_schema(
        operation_id="rbac_assign_role_permissions",
        tags=["RBAC - Permissions"],
        summary="Assign permissions to role",
        description=(
            "Assigns one or more permissions to an existing role. "
            "Existing permissions are preserved. "
            "Only Super Admin or users with rbac.manage_roles permission "
            "can perform this operation. "
            "A non-superuser role manager can only assign permissions "
            "that they personally possess. "
            "Only Super Admin can grant rbac.manage_roles."
        ),
        request=RolePermissionSerializer,
        responses={
            200: inline_serializer(
                name="AssignPermissionsResponse",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
            400: OpenApiResponse(
                description="Invalid permission IDs or unknown permissions."
            ),
            401: OpenApiResponse(
                description="Authentication credentials are missing or invalid."
            ),
            403: OpenApiResponse(
                description="Insufficient permissions or unauthorized permission delegation."
            ),
            404: OpenApiResponse(
                description="The requested role does not exist."
            ),
        },
        examples=[
            OpenApiExample(
                "Assign permissions request",
                value={
                    "permission_ids": [12, 13, 14]
                },
                request_only=True,
            ),
            OpenApiExample(
                "Successful response",
                value={
                    "detail": "Permissions assigned successfully."
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request, role_id):
        """
        Assign permissions to a role.
        """
        serializer = RolePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            RoleService.assign_permissions(
                role_id=role_id,
                permission_ids=serializer.validated_data["permission_ids"],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)

        return Response(
            {"detail": "Permissions assigned successfully."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="rbac_remove_role_permissions",
        tags=["RBAC - Permissions"],
        summary="Remove permissions from role",
        description=(
            "Removes selected permissions from an existing role. "
            "Permissions not included in the request remain unchanged. "
            "Only Super Admin or users with rbac.manage_roles permission "
            "can perform this operation. "
            "A non-superuser role manager can only remove permissions "
            "that they personally possess. "
            "Only Super Admin can revoke rbac.manage_roles."
        ),
        request=RolePermissionSerializer,
        responses={
            200: inline_serializer(
                name="RemovePermissionsResponse",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
            400: OpenApiResponse(
                description="Invalid permission IDs or unknown permissions."
            ),
            401: OpenApiResponse(
                description="Authentication credentials are missing or invalid."
            ),
            403: OpenApiResponse(
                description="Insufficient permissions or unauthorized permission delegation."
            ),
            404: OpenApiResponse(
                description="The requested role does not exist."
            ),
        },
        examples=[
            OpenApiExample(
                "Remove permissions request",
                value={
                    "permission_ids": [12, 13]
                },
                request_only=True,
            ),
            OpenApiExample(
                "Successful response",
                value={
                    "detail": "Permissions removed successfully."
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def delete(self, request, role_id):
        """
        Remove permissions from a role.
        """
        serializer = RolePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            RoleService.remove_permissions(
                role_id=role_id,
                permission_ids=serializer.validated_data["permission_ids"],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)

        return Response(
            {"detail": "Permissions removed successfully."},
            status=status.HTTP_200_OK,
        )


class PermissionListAPIView(APIView):
    permission_classes = [CanManageRoles]

    @extend_schema(
        operation_id="rbac_list_all_permissions",
        tags=["RBAC - Permissions"],
        summary="Get all system permissions",
        description=(
            "Retrieves all permissions registered in the Django application. "
            "Permissions are grouped logically by application label and "
            "include their ID, name, codename, application label and model. "
            "This endpoint is intended for the admin frontend permission "
            "management interface. Authentication is required."
        ),
        responses={
            200: PermissionSerializer(many=True),
            401: OpenApiResponse(
                description="Authentication credentials are missing or invalid."
            ),
        },
        examples=[
            OpenApiExample(
                "Successful response",
                value=[
                    {
                        "id": 12,
                        "name": "Can view university",
                        "codename": "view_university",
                        "app_label": "universities",
                        "model": "university",
                    },
                    {
                        "id": 13,
                        "name": "Can add university",
                        "codename": "add_university",
                        "app_label": "universities",
                        "model": "university",
                    },
                    {
                        "id": 20,
                        "name": "Can view program",
                        "codename": "view_program",
                        "app_label": "programs",
                        "model": "program",
                    },
                ],
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        """
        Retrieve all system permissions.
        """
        permissions = RoleSelector.get_all_permissions()

        serializer = PermissionSerializer(
            permissions,
            many=True,
        )

        return Response(serializer.data)


class RoleUserAPIView(APIView):
    permission_classes = [CanViewUsers]
    pagination_class = StandardResultsPagination


    @extend_schema(
        summary="Rolga biriktirilgan foydalanuvchilarni olish",
        description=(
            "Berilgan rolga biriktirilgan foydalanuvchilar ro‘yxatini "
            "qidiruv, holat bo‘yicha filtrlash va sahifalash imkoniyati "
            "bilan qaytaradi."
        ),
        tags=["RBAC - Rollar"],
        operation_id="get_role_users",
        parameters=[RoleUserQuerySerializer],
        responses={
            200: RoleUserPaginatedResponseSerializer,
            404: OpenApiResponse(
                description="Bunday rol mavjud emas."
            ),
            400: OpenApiResponse(
                description="So‘rov parametrlarida xatolik mavjud."
            ),
        },
    )
    def get(self, request, role_id):

        if not RoleSelector.role_exists(role_id=role_id):
            raise Http404("Bunday rol mavjud emas.")

        query_serializer = RoleUserQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        users = RoleSelector.get_role_users(
            role_id=role_id,
            search=query_serializer.validated_data.get("search"),
            is_active=query_serializer.validated_data.get("is_active"),
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            users,
            request,
            view=self,
        )

        serializer = RoleUserListSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)

