from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
import uuid

# from apps.product.models import Product
from apps.customer.models import Customer


class Rating(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )
    product = models.ForeignKey(
        "product.Product", on_delete=models.CASCADE, related_name="ratings"
    )
    stars = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="rating_created_by_customer",
    )
    updated_by = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="rating_updated_by_customer",
    )

    class Meta:
        unique_together = (("created_by", "product"),)
        index_together = (("created_by", "product"),)
