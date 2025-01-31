from django.urls import path

from apps.table.views import (
    TableCreateView,
    TableListView,
    TableAvailableListView,
    TableOccupiedListView,
    TableActiveListView,
    TableInActiveListView,
    TableRetrieveView,
    TableUpdateView,
    TableChangeActiveView,
    TableDeleteView,
    TableCurrentOrderDialogView,
)

app_name = "table"

urlpatterns = [
    path("table_create/", TableCreateView.as_view(), name="table create"),
    path("table_list/", TableListView.as_view(), name="table list"),
    path(
        "table_available_list/",
        TableAvailableListView.as_view(),
        name="table available list",
    ),
    path(
        "table_occupied_list/",
        TableOccupiedListView.as_view(),
        name="table occupied list",
    ),
    path("table_active_list/", TableActiveListView.as_view(), name="table active list"),
    path(
        "table_in_active_list/",
        TableInActiveListView.as_view(),
        name="table in active list",
    ),
    path("table_retrieve/", TableRetrieveView.as_view(), name="table retrieve"),
    path("table_update/", TableUpdateView.as_view(), name="table update"),
    path(
        "table_change_status/",
        TableChangeActiveView.as_view(),
        name="table change active",
    ),
    path("table_delete/", TableDeleteView.as_view(), name="table delete"),
    path(
        "table_current_order_dialog/",
        TableCurrentOrderDialogView.as_view(),
        name="table current order dialog",
    ),
]
