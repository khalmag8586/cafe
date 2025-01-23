from django.urls import path

from apps.rating.views import (
    RatingCreateView,
    RatingListView,
    RatingRetrieveView,
    RatingUpdateView,
    RatingDeleteView,
    RatingDialogView,
)

app_name = "rating"
urlpatterns = [
    path("rating_create/", RatingCreateView.as_view(), name="create_rating"),
    path("rating_list/", RatingListView.as_view(), name="all-of-ratings"),
    path("rating_retrieve/", RatingRetrieveView.as_view(), name="rating-retrieve"),
    path("rating_update/", RatingUpdateView.as_view(), name="rating-update"),
    path("rating_delete/", RatingDeleteView.as_view(), name="rating-delete"),
    path("rating_dialog/", RatingDialogView.as_view(), name="rating-dialog"),
]
