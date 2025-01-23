from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import (
    generics,
    status,
)
from rest_framework_simplejwt.authentication import JWTAuthentication

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import CustomerPermission
from apps.service.models import Service, ServiceImages
from apps.service.serializers import (
    ServiceSerializer,
    ServiceImageSerializer,
    ServiceDeleteSerializer,
    ServiceActiveSerializer,
    ServiceDialogSerializer,
)


class ServiceCreateView(generics.CreateAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.action = self.request.method.lower()

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
            {"detail": _("Service created successfully")},
            status=status.HTTP_201_CREATED,
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceSerializer
        elif self.action == "upload_image":
            return ServiceImageSerializer

        return self.serializer_class

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = ServiceSerializer
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [CustomerPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # search_fields = ["name", "name_ar", "service_symbol"]
    search_fields = [
        "name",
        "name_ar",
    ]
    ordering_fields = ["name", "-name", "name_ar", "-name_ar"]


class DeletedServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_deleted=True).order_by("-created_at")
    serializer_class = ServiceSerializer
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [CustomerPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # search_fields = ["name", "name_ar", "service_symbol"]
    search_fields = ["name", "name_ar"]
    ordering_fields = ["name", "-name", "name_ar", "-name_ar"]


class ServiceRetrieveView(generics.RetrieveAPIView):
    serializer_class = ServiceSerializer
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [CustomerPermission]
    lookup_field = "id"

    def get_object(self):
        service_id = self.request.query_params.get("service_id")
        service = get_object_or_404(Service, id=service_id)
        return service


class ActiveServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_deleted=False, is_active=True).order_by("-created_at")
    serializer_class = ServiceSerializer
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [CustomerPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # search_fields = ["name", "name_ar", "service_symbol"]
    search_fields = ["name", "name_ar"]
    ordering_fields = ["name", "-name", "name_ar", "-name_ar"]


class ServiceChangeActiveView(generics.UpdateAPIView):
    serializer_class = ServiceActiveSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        service_ids = request.data.get("service_id", [])
        partial = kwargs.pop("partial", False)
        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {"detail": _("'is_active' field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for service_id in service_ids:
            instance = get_object_or_404(Service, id=service_id)
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
        return Response(
            {"detail": _("Service status changed successfully")},
            status=status.HTTP_200_OK,
        )


class ServiceUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    lookup_field = "id"

    def get_object(self):
        service_id = self.request.query_params.get("service_id")
        service = get_object_or_404(Service, id=service_id)
        return service

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Service Updated successfully")}, status=status.HTTP_200_OK
        )


class ServiceImagesUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceImageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    queryset = ServiceImages.objects.all()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def patch(self, request, *args, **kwargs):
        image_id = request.data.get(
            "image_id"
        )  # Get the image ID from the request body
        if not image_id:
            return Response(
                {"detail": _("Image ID is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            instance = self.get_queryset().get(id=image_id)
        except ServiceImages.DoesNotExist:
            return Response(
                {"detail": _("Image not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # return Response(serializer.data)
        return Response(
            {"detail": _("Service image updated successfully")},
            status=status.HTTP_200_OK,
        )


class ServiceImagesDeleteView(generics.DestroyAPIView):
    serializer_class = ServiceImageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    queryset = ServiceImages.objects.all()

    def delete(self, request, *args, **kwargs):
        image_ids = request.data.get("image_id", [])
        for image_id in image_ids:
            instance = get_object_or_404(ServiceImages, id=image_id)
            instance.delete()
        return Response(
            {"detail": _("Service image deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class ServiceDeleteTemporaryView(generics.UpdateAPIView):
    serializer_class = ServiceDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        service_ids = request.data.get("service_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == False:
            return Response(
                {"detail": _("These services are not deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for service_id in service_ids:
            instance = get_object_or_404(Service, id=service_id)
            if instance.is_deleted:
                return Response(
                    {
                        "detail": _(
                            "Service with ID {} is already temp deleted".format(
                                service_id
                            )
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            instance.is_active = False
            instance.save()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        return Response(
            {"detail": _("Services temp deleted successfully")},
            status=status.HTTP_200_OK,
        )


class ServiceRestoreView(generics.RetrieveUpdateAPIView):

    serializer_class = ServiceDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def update(self, request, *args, **kwargs):
        service_ids = request.data.get("service_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == True:
            return Response(
                {"detail": _("services are already deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for service_id in service_ids:
            instance = get_object_or_404(Service, id=service_id)
            if instance.is_deleted == False:
                return Response(
                    {
                        "detail": _(
                            "service with ID {} is not deleted".format(service_id)
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            instance.is_active = True

            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        return Response(
            {"detail": _("Services restored successfully")}, status=status.HTTP_200_OK
        )


class ServiceDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def delete(self, request, *args, **kwargs):
        service_ids = request.data.get("service_id", [])
        for service_id in service_ids:
            instance = get_object_or_404(Service, id=service_id)
            instance.delete()

        return Response(
            {"detail": _("Service permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


# Service Dialogs
class ServiceDialogView(generics.ListAPIView):
    serializer_class = ServiceDialogSerializer
    queryset = Service.objects.filter(is_deleted=False, is_active=True)
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [CustomerPermission]


# class AvailableSymbolsView(APIView):
#     def get(self, request, format=None):
#         # Get all existing symbols
#         existing_symbols = Service.objects.values_list("service_symbol", flat=True)

#         # Generate available letters by excluding existing symbols
#         available_letters = [
#             chr(i) for i in range(65, 91) if chr(i) not in existing_symbols
#         ]

#         return Response(
#             {"available_symbols": available_letters}, status=status.HTTP_200_OK
#         )
