from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid


class Printer(models.Model):
    PRINTER_TYPES_CHOICES = [
        ("cashier", _("Cashier")),
        ("barista", _("Barista")),
        ("shisha", _("Shisha Maker")),
        ("kitchen", _("Kitchen")),
    ]
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    name = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)
    printer_type = models.CharField(max_length=100, choices=PRINTER_TYPES_CHOICES)
    ip_address = models.CharField(max_length=20)  # Store the printer's IP address
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_created_printer",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_updated_printer",
        blank=True,
        null=True,
    )
