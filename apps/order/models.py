from django.db import models

from django.conf import settings
import uuid
from decimal import Decimal
from apps.product.models import Product


class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("Pending", ("Pending")),
        ("Complete", ("Complete")),
        ("Failed", ("Failed")),
    ]
    PAYMENT_METHOD_CHOICES = [
        ("PayPal", ("PayPal")),
    ]
    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True,
        editable=False,
    )
    order_number = models.PositiveBigIntegerField(unique=True, auto_created=True)
    payment_method = models.CharField(
        max_length=16,
        choices=PAYMENT_METHOD_CHOICES,
        default="PayPal",  # Set a default value
    )
    payment_status = models.CharField(
        max_length=8,
        default="Pending",
        choices=PAYMENT_STATUS_CHOICES,
    )
    final_total = models.DecimalField(max_digits=10, decimal_places=2)
    paypal_payment_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="order_created_by_customer",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="order_updated_by_customer",
    )

    # def calculate_final_total(self):
    #     order_items_total = self.order_items.aggregate(
    #         total=models.Sum(
    #             models.F("quantity") * models.F("cart__items__grand_total"),
    #             output_field=models.DecimalField(),
    #         )
    #     ).get("total", Decimal(0.0))
    #     return order_items_total

    # def calculate_final_total(self):
    #     order_items_total = self.order_items.aggregate(
    #         total=models.Sum(
    #             models.F("quantity") * models.F("cartitems__sub_total"),
    #             output_field=models.DecimalField(),
    #         )
    #     ).get("total", Decimal(0.0))
    #     return order_items_total

    # def save(self, *args, **kwargs):
    #     self.final_total = self.calculate_final_total()
    #     super(Order, self).save(*args, **kwargs)
    def save(self, *args, **kwargs):
        if not self.order_number:
            last_order = Order.objects.all().order_by("order_number").last()
            if last_order:
                self.order_number = last_order.order_number + 1
            else:
                self.order_number = 1000

        if not self.final_total:  # Check if final_total is not set
            self.final_total = 0  # Initialize final_total to 0

        super(Order, self).save(*args, **kwargs)

        if self.order_items.exists():  # Check if order_items exist
            self.final_total = sum(
                item.sub_total * item.quantity for item in self.order_items.all()
            )
            super(Order, self).save(*args, **kwargs)


class OrderItems(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True,
        editable=False,
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="order_items",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    purchase_type = models.CharField(max_length=100)  # Example field, adjust as needed
    quantity = models.PositiveIntegerField()
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)

    # def save(self, *args, **kwargs):
    #     self.sub_total = self.quantity * self.price
    #     super(OrderItems, self).save(*args, **kwargs)
