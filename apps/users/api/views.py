from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.common.pagination import StandardResultsPagination

from apps.users.api.permissions import (
    CanViewEmployees,
    CanCreateEmployees,
    CanUpdateEmployees,
    CanManageEmployeeStatus,
    CanAssignEmployeeRoles
)
from apps.users.api.serializers import (
    EmployeeCreateSerializer,
    EmployeeListSerializer,
    EmployeeQuerySerializer,
    EmployeeUpdateSerializer,
    EmployeeRoleManagementSerializer
)
from apps.users.selectors.employee_selector import EmployeeSelector
from apps.users.services.employee_service import EmployeeService
from apps.users.services.exceptions import EmployeeNotFoundError
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from apps.rbac.services.role_service import RoleService


def handle_service_validation_error(exc):
    """Django ValidationError'ni DRF ValidationError'ga aylantiradi."""

    if hasattr(exc, "message_dict"):
        raise serializers.ValidationError(exc.message_dict)

    raise serializers.ValidationError(exc.messages)


class EmployeeListCreateAPIView(APIView):
    """CMS xodimlarini ro'yxatlash va yaratish API."""

    pagination_class = StandardResultsPagination

    def get_permissions(self):
        permission_map = {
            "GET": CanViewEmployees,
            "POST": CanCreateEmployees,
        }

        permission_class = permission_map.get(self.request.method, IsAuthenticated,)

        return [permission_class()]

    @extend_schema(
        operation_id="list_employees",
        tags=["Users - Employees"],
        summary="Get employees",
        description=(
            "Returns CMS employees with search, status filtering "
            "and pagination."
        ),
        responses={
            200: EmployeeListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
        },
    )
    def get(self, request):
        query_serializer = EmployeeQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        queryset = EmployeeSelector.get_employee_queryset(
            **query_serializer.validated_data
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        serializer = EmployeeListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="create_employee",
        tags=["Users - Employees"],
        summary="Create employee",
        request=EmployeeCreateSerializer,
        responses={
            201: EmployeeListSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Insufficient permissions."),
        },
    )
    def post(self, request):
        serializer = EmployeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            employee = EmployeeService.create_employee(
                actor=request.user,
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
                first_name=serializer.validated_data.get("first_name", ""),
                last_name=serializer.validated_data.get("last_name", ""),
                email=serializer.validated_data.get("email", ""),
                phone_number=serializer.validated_data.get("phone_number", ""),
                role_ids=serializer.validated_data.get("role_ids", []),
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise DRFPermissionDenied(str(exc))

        response_serializer = EmployeeListSerializer(employee)

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class EmployeeDetailAPIView(APIView):
    def get_permissions(self):
        permission_map = {
            "GET": CanViewEmployees,
            "PATCH": CanUpdateEmployees,
            "DELETE": CanManageEmployeeStatus,
        }

        permission_class = permission_map.get(
            self.request.method,
            IsAuthenticated,
        )

        return [permission_class()]

    def get_object(self, employee_id):
        employee = EmployeeSelector.get_employee_by_id(
            employee_id=employee_id
        )

        if employee is None:
            raise NotFound("Xodim topilmadi.")

        return employee

    @extend_schema(
        operation_id="retrieve_employee",
        tags=["Users - Xodimlar"],
        summary="Xodim ma'lumotlarini olish",
        responses={
            200: EmployeeListSerializer,
            401: OpenApiResponse(description="Autentifikatsiya talab qilinadi."),
            403: OpenApiResponse(description="Ushbu amal uchun ruxsat mavjud emas."),
            404: OpenApiResponse(description="Xodim topilmadi."),
        },
    )
    def get(self, request, pk):
        employee = self.get_object(pk)
        return Response(EmployeeListSerializer(employee).data)

    @extend_schema(
        operation_id="update_employee",
        tags=["Users - Xodimlar"],
        summary="Xodim ma'lumotlarini yangilash",
        request=EmployeeUpdateSerializer,
        responses={
            200: EmployeeListSerializer,
            400: OpenApiResponse(description="Yuborilgan ma'lumotlar noto'g'ri."),
            401: OpenApiResponse(description="Autentifikatsiya talab qilinadi."),
            403: OpenApiResponse(description="Ushbu amal uchun ruxsat mavjud emas."),
            404: OpenApiResponse(description="Xodim topilmadi."),
        },
    )
    def patch(self, request, pk):
        serializer = EmployeeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            employee = EmployeeService.update_employee(
                actor=request.user,
                employee_id=pk,
                **serializer.validated_data,
            )
        except EmployeeNotFoundError as exc:
            raise NotFound(str(exc)) from exc
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)

        return Response(EmployeeListSerializer(employee).data)

    @extend_schema(
        operation_id="deactivate_employee",
        tags=["Users - Xodimlar"],
        summary="Xodimni deaktivatsiya qilish",
        responses={
            204: OpenApiResponse(description="Xodim muvaffaqiyatli deaktivatsiya qilindi."),
            400: OpenApiResponse(description="Ushbu amalni bajarish mumkin emas."),
            401: OpenApiResponse(description="Autentifikatsiya talab qilinadi."),
            403: OpenApiResponse(description="Ushbu amal uchun ruxsat mavjud emas."),
            404: OpenApiResponse(description="Xodim topilmadi."),
        },
    )
    def delete(self, request, pk):
        try:
            EmployeeService.deactivate_employee(
                actor=request.user,
                employee_id=pk,
            )
        except EmployeeNotFoundError as exc:
            raise NotFound(str(exc)) from exc
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)

        return Response(status=status.HTTP_204_NO_CONTENT)



class EmployeeActivateAPIView(APIView):
    permission_classes = [CanManageEmployeeStatus]

    @extend_schema(
        operation_id="activate_employee",
        tags=["Users - Xodimlar"],
        summary="Xodimni qayta faollashtirish",
        responses={
            200: EmployeeListSerializer,
            400: OpenApiResponse(description="Ushbu amalni bajarish mumkin emas."),
            401: OpenApiResponse(description="Autentifikatsiya talab qilinadi."),
            403: OpenApiResponse(description="Ushbu amal uchun ruxsat mavjud emas."),
            404: OpenApiResponse(description="Xodim topilmadi."),
        },
    )
    def post(self, request, pk):
        try:
            employee = EmployeeService.activate_employee(
                actor=request.user,
                employee_id=pk,
            )
        except EmployeeNotFoundError as exc:
            raise NotFound(str(exc)) from exc
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)

        return Response(EmployeeListSerializer(employee).data)


class EmployeeRoleAssignmentAPIView(APIView):
    permission_classes = [CanAssignEmployeeRoles]

    @extend_schema(
        tags=["Users - Xodimlar"],
        operation_id="employee_assign_roles",
        summary="Xodimga rol biriktirish",
        description=(
                "Xodimga bir yoki bir nechta rol biriktiradi. "
                "Faqat foydalanuvchida mavjud permissionlardan "
                "tashkil topgan rollarni biriktirish mumkin."
        ),
        request=EmployeeRoleManagementSerializer,
        responses={
            200: EmployeeListSerializer,
            400: OpenApiResponse(
                description="So'rov ma'lumotlari noto'g'ri."
            ),
            403: OpenApiResponse(
                description="Amalni bajarish uchun ruxsat yo'q."
            ),
            404: OpenApiResponse(
                description="Xodim topilmadi."
            ),
        },
    )
    def post(self, request, pk):
        serializer = EmployeeRoleManagementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = EmployeeSelector.get_employee_by_id(
            employee_id=pk,
        )

        if employee is None:
            raise NotFound("Xodim topilmadi.")

        try:
            RoleService.assign_employee_to_roles(
                role_ids=serializer.validated_data["role_ids"],
                employee=employee,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise DRFPermissionDenied(str(exc))

        return Response(
            EmployeeListSerializer(employee).data,
            status=status.HTTP_200_OK,
        )


class EmployeeRoleRemovalAPIView(APIView):
    permission_classes = [CanAssignEmployeeRoles]

    @extend_schema(
        tags=["Users - Xodimlar"],
        operation_id="employee_remove_roles",
        summary="Xodimdan rolni olib tashlash",
        description=(
                "Xodimdan bir yoki bir nechta rolni olib tashlaydi. "
                "Faqat ushbu xodimga biriktirilgan rollarni olib tashlash mumkin."
        ),
        request=EmployeeRoleManagementSerializer,
        responses={
            200: EmployeeListSerializer,
            400: OpenApiResponse(
                description="So'rov ma'lumotlari noto'g'ri."
            ),
            403: OpenApiResponse(
                description="Amalni bajarish uchun ruxsat yo'q."
            ),
            404: OpenApiResponse(
                description="Xodim topilmadi."
            ),
        },
    )
    def post(self, request, pk):
        serializer = EmployeeRoleManagementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = EmployeeSelector.get_employee_by_id(
            employee_id=pk,
        )

        if employee is None:
            raise NotFound("Xodim topilmadi.")

        try:
            RoleService.remove_employee_from_roles(
                role_ids=serializer.validated_data["role_ids"],
                employee=employee,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            handle_service_validation_error(exc)
        except DjangoPermissionDenied as exc:
            raise DRFPermissionDenied(str(exc))

        return Response(
            EmployeeListSerializer(employee).data,
            status=status.HTTP_200_OK,
        )