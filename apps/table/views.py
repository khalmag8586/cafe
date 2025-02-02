from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import AnonymousUser
from django.db.models import Avg

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import (
    generics,
    status,
)
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.table.models import Table
from apps.table.serializers import (
    TableSerializer,
    TableActiveSerializer,
    TableCurrentOrderDialogSerializer,
)

from cafe.custom_permissions import HasPermissionOrInGroupWithPermission
from cafe.pagination import StandardResultsSetPagination


class TableCreateView(generics.CreateAPIView):
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.add_table"

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("Table created successfully")},
            status=status.HTTP_201_CREATED,
        )


class TableListView(generics.ListAPIView):
    queryset = Table.objects.all().order_by("table_number")
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.view_table"
    pagination_class = StandardResultsSetPagination


class TableAvailableListView(generics.ListAPIView):
    queryset = Table.objects.filter(is_occupied=False).order_by("table_number")
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.view_table"
    pagination_class = StandardResultsSetPagination


class TableActiveListView(generics.ListAPIView):
    queryset = Table.objects.filter(is_active=True).order_by("table_number")
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.view_table"
    pagination_class = StandardResultsSetPagination


class TableInActiveListView(generics.ListAPIView):
    queryset = Table.objects.filter(is_active=False).order_by("table_number")
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.view_table"
    pagination_class = StandardResultsSetPagination


class TableOccupiedListView(generics.ListAPIView):
    queryset = Table.objects.filter(is_occupied=True).order_by("table_number")
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.view_table"
    pagination_class = StandardResultsSetPagination


class TableRetrieveView(generics.RetrieveAPIView):
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.view_table"
    lookup_field = "id"

    def get_object(self):
        table_id = self.request.query_params.get("table_id")
        table = get_object_or_404(Table, id=table_id)
        return table


class TableUpdateView(generics.UpdateAPIView):
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.change_table"
    lookup_field = "id"

    def get_object(self):
        table_id = self.request.query_params.get("table_id")
        table = get_object_or_404(Table, id=table_id)
        return table

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Table updated successfully")}, status=status.HTTP_200_OK
        )


class TableChangeActiveView(generics.UpdateAPIView):
    serializer_class = TableActiveSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.change_table"

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        table_ids = request.data.get("table_id", [])
        partial = kwargs.pop("partial", False)
        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {"detail": _("'is_active' field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for table_id in table_ids:
            instance = get_object_or_404(Table, id=table_id)
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
        return Response(
            {"detail": _("Table status changed successfully")},
            status=status.HTTP_200_OK,
        )


class TableDeleteView(generics.DestroyAPIView):
    serializer_class = TableSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "table.delete_table"

    def delete(self, request, *args, **kwargs):
        table_ids = request.data.get("table_id", [])
        for table_id in table_ids:
            instance = get_object_or_404(Table, id=table_id)
            instance.delete()
        return Response(
            {"detail": _("Table permanently deleted successfully")},
            status=status.HTTP_200_OK,
        )


class TableCurrentOrderDialogView(generics.ListAPIView):
    serializer_class = TableCurrentOrderDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Table.objects.filter(is_active=True, is_occupied=True).order_by(
        "table_number"
    )
