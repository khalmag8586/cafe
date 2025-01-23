from django.urls import path

from apps.contact_us.views import (
    ContactUSCreateView,
    ContactUsListView,
    ContactUsRetrieveView,ContactUsChangeRead,ContactUsDeleteView
)

app_name = "contact_us"

urlpatterns = [
    path(
        "contact_us_create/", ContactUSCreateView.as_view(), name="  contact_us_create"
    ),
    path("contact_us_list/", ContactUsListView.as_view(), name="  contact_us_list"),
    path(
        "contact_us_retrieve/",
        ContactUsRetrieveView.as_view(),
        name="  contact_us_retrieve",
    ),
    path("contact_us_change_read/",ContactUsChangeRead.as_view(),name='contact_us_change_status'),
    path('contact_us_delete/',ContactUsDeleteView.as_view() ,name='contact_us_delete')
]
