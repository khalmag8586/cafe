from django.urls import path
from apps.printer.views import (
    PrinterCreateView,
    PrinterListView,
    PrinterUpdateView,
    PrinterDeleteView,
)

app_name = "printer"

urlpatterns = [
    path("create_printer/", PrinterCreateView.as_view(), name="create printer"),
    path("printer_list/", PrinterListView.as_view(), name="printer list"),
    path("update_printer/", PrinterUpdateView.as_view(), name="update printer"),
    path("printer_delete/", PrinterDeleteView.as_view(), name="delete printer"),
]
