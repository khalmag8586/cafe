from django.urls import path
from apps.section.views import (
    SectionCreateView,
    SectionListView,
    SectionRetrieveView,
    ActiveSectionListView,
    SectionChangeActiveView,
    SectionUpdateView,
    SectionMediaUpdateView,
    SectionMediaDeleteView,
    SectionDeleteView,
    SectionDialogView,
)

app_name = "section"

urlpatterns = [
    path("section_create/", SectionCreateView.as_view(), name="create-section"),
    path("section_list/", SectionListView.as_view(), name="list-section"),
    path("section_retrieve/", SectionRetrieveView.as_view(), name="retrieve-section"),
    path(
        "section_active_list/",
        ActiveSectionListView.as_view(),
        name="section-active-list",
    ),
    path(
        "change_section_status/",
        SectionChangeActiveView.as_view(),
        name="change-section-status",
    ),
    path("section_update/", SectionUpdateView.as_view(), name="section-update"),
    path(
        "section_media_update/",
        SectionMediaUpdateView.as_view(),
        name="section_media_update",
    ),
    path(
        "section_media_delete/",
        SectionMediaDeleteView.as_view(),
        name="section_media_delete",
    ),
    path("section_delete/", SectionDeleteView.as_view(), name="delete-section"),
    path("section_dialog/", SectionDialogView.as_view(), name="section-dialog"),
]
