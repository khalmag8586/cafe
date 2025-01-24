from django.urls import path
from apps.printer.views import (
    PrinterCreateView,
    PrinterListView,
)

app_name = "printer"

urlpatterns = [
    path("create_printer/", PrinterCreateView.as_view(), name="create printer"),
    path("printer_list/", PrinterListView.as_view(), name="printer list"),
]
