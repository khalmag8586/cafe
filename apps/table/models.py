from django.db import models
from django.conf import settings
import uuid

class Table(models.Model):
    id = models.UUIDField(primary_key=True,editable=False,default=uuid.uuid4)
    table_number = models.PositiveBigIntegerField(unique=True)
    no_of_pax = models.PositiveIntegerField(default=0)
    is_occupied = models.BooleanField(default=False)
    is_owner = models.BooleanField(
        default=False
    )  # Indicates if the table is owned by owner
    is_active=models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_created_table",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_updated_table",
        blank=True,
        null=True,
    )
