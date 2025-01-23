import os

from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse, JsonResponse

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
from rest_framework import (
    generics,
    status,
)

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.about_us.models import AboutUs
from apps.about_us.serializers import AboutUsSerializer
from cafe.custom_permissions import  HasPermissionOrInGroupWithPermission

class AboutUsCreateView(generics.CreateAPIView):
    serializer_class = AboutUsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='about_us.add_aboutus'
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
            {"detail": _("AboutUs created successfully")},
            status=status.HTTP_201_CREATED,
        )


# class AboutUsListView(generics.ListAPIView):
#     # queryset = AboutUs.objects.all()
#     serializer_class = AboutUsSerializer
#     def get_queryset(self):
#         # Get the first object from the queryset
#         queryset = AboutUs.objects.all()[:1]
#         return queryset
class AboutUsListView(generics.ListAPIView):
    queryset = AboutUs.objects.all()  # Remove any ordering
    serializer_class = AboutUsSerializer
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().order_by('created_at')[:1]  # Apply ordering before slicing
        serializer = self.get_serializer(queryset.first())
        return Response(serializer.data)


class AboutUsRetrieveView(generics.RetrieveAPIView):
    serializer_class = AboutUsSerializer
    lookup_field = "id"

    def get_object(self):
        aboutUs_id = self.request.query_params.get("aboutUs_id")
        aboutUs = get_object_or_404(AboutUs, id=aboutUs_id)
        return aboutUs


class AboutUsUpdateView(generics.UpdateAPIView):
    serializer_class = AboutUsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='about_us.change_aboutus'
    lookup_field = "id"

    def get_object(self):
        aboutUs_id = self.request.query_params.get("aboutUs_id")
        aboutUs = get_object_or_404(AboutUs, id=aboutUs_id)
        return aboutUs

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("AboutUs updated successfully")}, status=status.HTTP_200_OK
        )


class AboutUsDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='about_us.delete_aboutus'

    def delete(self, request, *args, **kwargs):
        aboutUs_ids = request.data.get("aboutUs_id", [])
        for aboutUs_id in aboutUs_ids:
            instance = get_object_or_404(AboutUs, id=aboutUs_id)
            instance.delete()

        return Response(
            {"detail": _("AboutUs permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


