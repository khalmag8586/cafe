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
from apps.section.models import Section, SectionMediaFiles
from apps.section.serializers import (
    SectionSerializer,
    SectionMediaSerializer,
    ActiveSectionSerializer,
    SectionDialogSerializer,
)

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import HasPermissionOrInGroupWithPermission


class SectionCreateView(generics.CreateAPIView):
    serializer_class = SectionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        section = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        media_files = self.request.FILES.getlist("uploaded_media")
        media_instances = [
            SectionMediaFiles.objects.create(section=section, media=media_file)
            for media_file in media_files
        ]
        for media_instance in media_instances:
            media_instance.save()
        section.gallery.set(media_instances)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"detail": _("Section created successfully")},
            status=status.HTTP_201_CREATED,
        )


class SectionListView(generics.ListAPIView):
    serializer_class = SectionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Section.objects.all().order_by("-created_at")
    pagination_class = StandardResultsSetPagination


class SectionRetrieveView(generics.RetrieveAPIView):
    serializer_class = SectionSerializer
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    lookup_field = "slug"

    def get_object(self):
        slug = self.request.query_params.get("slug")
        section = get_object_or_404(Section, slug=slug)
        return section


class ActiveSectionListView(generics.ListAPIView):
    queryset = Section.objects.filter(is_deleted=False, is_active=True).order_by(
        "-created_at"
    )
    serializer_class = SectionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

class SectionChangeActiveView(generics.UpdateAPIView):
    serializer_class = ActiveSectionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        section_ids = request.data.get("section_id", [])
        partial = kwargs.pop("partial", False)
        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {"detail": _("'is_active' field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for section_id in section_ids:
            instance = get_object_or_404(Section, id=section_id)
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
        return Response(
            {"detail": _("Section status changed successfully")},
            status=status.HTTP_200_OK,
        )


class SectionUpdateView(generics.UpdateAPIView):
    serializer_class = SectionSerializer
    lookup_field = "section_id"
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        section_id = self.request.query_params.get("section_id")
        section = get_object_or_404(Section, id=section_id)
        return section

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Section updated successfully")}, status=status.HTTP_200_OK
        )


class SectionMediaUpdateView(generics.UpdateAPIView):
    serializer_class = SectionMediaSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = SectionMediaFiles.objects.all()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def patch(self, request, *args, **kwargs):
        media_id = request.data.get(
            "media_id"
        )  # Get the image ID from the request body
        if not media_id:
            return Response(
                {"detail": _("Media ID is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            instance = self.get_queryset().get(id=media_id)
        except SectionMediaFiles.DoesNotExist:
            return Response(
                {"detail": _("Media not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # return Response(serializer.data)
        return Response(
            {"detail": _("Section Media updated successfully")},
            status=status.HTTP_200_OK,
        )


class SectionMediaDeleteView(generics.DestroyAPIView):
    serializer_class = SectionMediaSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = SectionMediaFiles.objects.all()

    def delete(self, request, *args, **kwargs):
        media_ids = request.data.get("media_id", [])
        for media_id in media_ids:
            instance = get_object_or_404(SectionMediaFiles, id=media_id)
            instance.delete()
        return Response(
            {"detail": _("Section Media deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class SectionDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        section_ids = request.data.get("section_id")
        for section_id in section_ids:
            instance = get_object_or_404(Section, id=section_id)
            instance.delete()
        return Response(
            {"detail": _("Section permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )

class SectionDialogView(generics.ListAPIView):
    queryset = Section.objects.filter(is_deleted=False)
    serializer_class = SectionDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
