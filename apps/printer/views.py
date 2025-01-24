from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

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

from apps.printer.models import Printer
from apps.printer.serializers import (
    PrinterSerializer,
    PrinterDialogSerializer,
    PrinterTypesDialogSerializer,
)

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import HasPermissionOrInGroupWithPermission


class PrinterCreateView(generics.CreateAPIView):
    serializer_class = PrinterSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "printer.add_printer"

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
            {"detail": _("Printer created successfully")},
            status=status.HTTP_201_CREATED,
        )


class PrinterListView(generics.ListAPIView):
    queryset = Printer.objects.all()
    serializer_class = PrinterSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "printer.view_printer"
    pagination_class = StandardResultsSetPagination
