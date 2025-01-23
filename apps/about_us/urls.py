from django.urls import path
from apps.about_us.views import (
    AboutUsCreateView,
    AboutUsListView,
    AboutUsRetrieveView,
    AboutUsUpdateView,
    AboutUsDeleteView,
    UploadFileView,
    DownloadFileView,get_pdf_file_names,
)

app_name = "about_us"
urlpatterns = [
    path("aboutUs_create/", AboutUsCreateView.as_view(), name="aboutUs_create"),
    path("aboutUs_list/", AboutUsListView.as_view(), name="aboutUs_list"),
    path("aboutUs_retrieve/", AboutUsRetrieveView.as_view(), name="aboutUs_retrieve"),
    path("aboutUs_update/", AboutUsUpdateView.as_view(), name="aboutUs_update"),
    path("aboutUs_delete/", AboutUsDeleteView.as_view(), name="aboutUs_delete"),
    path("upload_pdf_file/", UploadFileView.as_view(), name="upload-file"),
    path("download_file/", DownloadFileView.as_view(), name="download-file"),
    path('pdf_files_names/',get_pdf_file_names, name='pdf_files_names'),
]
