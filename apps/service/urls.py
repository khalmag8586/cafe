from django.urls import path
from apps.service.views import (
    ServiceCreateView,
    ServiceListView,
    DeletedServiceListView,
    ServiceRetrieveView,
    ActiveServiceListView,
    ServiceUpdateView,
    ServiceImagesUpdateView,
    ServiceImagesDeleteView,
    ServiceChangeActiveView,
    ServiceDeleteTemporaryView,
    ServiceRestoreView,
    ServiceDeleteView,
    ServiceDialogView,
    # AvailableSymbolsView,

)

app_name = "service"
urlpatterns = [
    path("service_create/", ServiceCreateView.as_view(), name="service-create"),
    path("service_list/", ServiceListView.as_view(), name="service-list"),
    path(
        "deleted_service_list/",
        DeletedServiceListView.as_view(),
        name="deleted-service-list",
    ),
    path("service_retrieve/", ServiceRetrieveView.as_view(), name="service-retrieve"),
    path('active_service/',ActiveServiceListView.as_view(),name='active-service'),
    path('change_service_status/',ServiceChangeActiveView.as_view(),name='change_service_status'),
    path('service_update/',ServiceUpdateView.as_view(),name='service-update'),
    path('service_image_update/',ServiceImagesUpdateView.as_view(),name='service-image-update'),
    path('service_image_delete/',ServiceImagesDeleteView.as_view(),name='service-image-delete'),
    path('service_temp_delete/',ServiceDeleteTemporaryView.as_view(),name='service-temp-delete'),
    path('service_restore/',ServiceRestoreView.as_view(),name='service-restore'),
    path('service_delete/',ServiceDeleteView.as_view(),name='service-delete'),
    path('service_dialog/',ServiceDialogView.as_view(),name='service-dialog'),
    # path('available_symbols/', AvailableSymbolsView.as_view(), name='available_symbols'),

]
