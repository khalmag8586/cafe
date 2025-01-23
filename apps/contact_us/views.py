import os

from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import (
    generics,
    status,
)

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.contact_us.models import ContactUs
from .serializers import ContactUsSerializer, ContactUsReadSerializer

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import  HasPermissionOrInGroupWithPermission

class ContactUSCreateView(generics.CreateAPIView):
    serializer_class = ContactUsSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("ContactUs created successfully")},
            status=status.HTTP_201_CREATED,
        )


class ContactUsListView(generics.ListAPIView):
    serializer_class = ContactUsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='contact_us.view_contactus'
    queryset = ContactUs.objects.all().order_by("-created_at")
    pagination_class = StandardResultsSetPagination


class ContactUsRetrieveView(generics.RetrieveAPIView):
    serializer_class = ContactUsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='contact_us.view_contactus'
    lookup_field = "id"

    def get_object(self):
        contactUs_id = self.request.query_params.get("contactUs_id")
        contactUs = get_object_or_404(ContactUs, id=contactUs_id)
        return contactUs


class ContactUsChangeRead(generics.UpdateAPIView):
    serializer_class = ContactUsReadSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='contact_us.change_contactus'

    def get_object(self):
        contactUs_id = self.request.query_params.get("contactUs_id")
        contactUs = get_object_or_404(ContactUs, id=contactUs_id)
        return contactUs

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("ContactUs updated successfully")}, status=status.HTTP_200_OK
        )


class ContactUsDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='contact_us.delete_contactus'

    def delete(self, request, *args, **kwargs):
        contactUs_ids = request.data.get("contactUs_id", [])
        for contactUs_id in contactUs_ids:
            instance = get_object_or_404(ContactUs, id=contactUs_id)
            instance.delete()

        return Response(
            {"detail": _("ContactUs permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )
