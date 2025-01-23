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
from cafe.custom_permissions import CustomerPermission

class AboutUsCreateView(generics.CreateAPIView):
    serializer_class = AboutUsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

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
    permission_classes = [CustomerPermission]
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
    permission_classes = [CustomerPermission]

    def delete(self, request, *args, **kwargs):
        aboutUs_ids = request.data.get("aboutUs_id", [])
        for aboutUs_id in aboutUs_ids:
            instance = get_object_or_404(AboutUs, id=aboutUs_id)
            instance.delete()

        return Response(
            {"detail": _("AboutUs permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class DownloadFileView(APIView):
    def get(self, request):

        file_name = request.query_params.get("file_name")
        if not file_name:
            return Response(
                {"error": "File name not provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        file_path = os.path.join("uploads", file_name)
        if not os.path.exists(file_path):
            return Response(
                {"error": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            with open(file_path, "rb") as fh:
                response = HttpResponse(
                    fh.read(), content_type="application/octet-stream"
                )
                response["Content-Disposition"] = (
                    "attachment; filename=" + os.path.basename(file_path)
                )
                return response
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadFileView(APIView):
    parser_classes = [MultiPartParser]
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def post(self, request, format=None):
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            # Process the uploaded file (e.g., save it to disk)
            file_path = handle_uploaded_file(uploaded_file)
            return Response(
                {"detail": _("File uploaded successfully"), "file_path": file_path},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"detail": _("No file uploaded")}, status=status.HTTP_400_BAD_REQUEST
            )


def handle_uploaded_file(uploaded_file):
    # Define the directory where you want to save the uploaded files
    upload_dir = "uploads/"
    # Create the directory if it doesn't exist
    os.makedirs(upload_dir, exist_ok=True)
    # Generate a unique filename
    file_name = uploaded_file.name
    file_path = os.path.join(upload_dir, file_name)
    # Write the uploaded file to disk
    with open(file_path, "wb") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    return file_path


def get_pdf_file_names(request):
    upload_dir = (
        "uploads"  # Adjust this path to the actual path of your uploads directory
    )
    if os.path.exists(upload_dir):
        pdf_files = [
            f
            for f in os.listdir(upload_dir)
            if os.path.isfile(os.path.join(upload_dir, f))
            and f.lower().endswith(".pdf")
        ]
        return JsonResponse({"pdf_files": pdf_files})
    else:
        return JsonResponse({"error": "Uploads directory does not exist"})
