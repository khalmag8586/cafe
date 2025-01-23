import uuid

from django.db import models

from apps.product.models import Product
from apps.customer.models import Customer
from django.utils.translation import gettext_lazy as _


class Cart(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    customer = models.OneToOneField(
        Customer, related_name="customers", on_delete=models.CASCADE
    )
    total_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)


class CartItems(models.Model):
    PURCHASE_CHOICES = [("pdf", _("PDF")), ("sib", _("SIBELIUS"))]

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
        unique=True,
    )
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        blank=True,
        null=True,
    )
    product = models.ForeignKey(
        Product,
        related_name="cartitems",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    added_at = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveBigIntegerField(default=1)
    purchase_type = models.CharField(
        max_length=8, choices=PURCHASE_CHOICES, default="pdf"
    )
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    class Meta:
        unique_together = ("cart", "product", "purchase_type")

class Wishlist(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
        unique=True,
    )
    customer = models.OneToOneField(
        Customer, related_name="wishlist", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class WishlistItem(models.Model):
    PURCHASE_CHOICES = [("pdf", _("PDF")), ("sib", _("SIBELIUS"))]

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
        unique=True,
    )
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        related_name="wishlistitems",
        on_delete=models.CASCADE,
    )
    added_at = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(default=1)
    purchase_type = models.CharField(
        max_length=8, choices=PURCHASE_CHOICES, default="pdf"
    )
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
