from django.urls import path
from apps.about_us.views import (
    AboutUsCreateView,
    AboutUsListView,
    AboutUsRetrieveView,
    AboutUsUpdateView,
    AboutUsDeleteView,

)

app_name = "about_us"
urlpatterns = [
    path("aboutUs_create/", AboutUsCreateView.as_view(), name="aboutUs_create"),
    path("aboutUs_list/", AboutUsListView.as_view(), name="aboutUs_list"),
    path("aboutUs_retrieve/", AboutUsRetrieveView.as_view(), name="aboutUs_retrieve"),
    path("aboutUs_update/", AboutUsUpdateView.as_view(), name="aboutUs_update"),
    path("aboutUs_delete/", AboutUsDeleteView.as_view(), name="aboutUs_delete"),
]
