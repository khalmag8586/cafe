from django.db import models
from django.utils.translation import gettext_lazy as _

from django.conf import settings
import uuid
from decimal import Decimal
from datetime import time
from django.utils import timezone

from apps.product.models import Product
from apps.table.models import Table


class BusinessDay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    is_closed =models.BooleanField(default=False)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="day_closed_by_user",
    )
    # def close_day(self, user):
    #     """Close the business day."""
    #     self.end_time = now()
    #     self.is_closed = True
    #     self.closed_by = user
    #     self.save()


class Discount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="discount_created_by_user",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="discount_updated_by_user",
    )


class Order(models.Model):

    SHIFT_CHOICES = [
        ("morning", _("Morning")),
        ("evening", _("Evening")),
    ]
    id = models.BigAutoField(primary_key=True, editable=False)
    table = models.ForeignKey(
        Table, on_delete=models.SET_NULL, null=True, related_name="tables"
    )
    number_of_pax = models.PositiveIntegerField()
    check_out_time = models.DateTimeField(auto_now=True)
    hall = models.CharField(max_length=100)
    shift = models.CharField(
        max_length=100, default="morning", choices=SHIFT_CHOICES, editable=False
    )
    kot_number = models.PositiveIntegerField(unique=True, blank=True, null=True)

    final_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.ForeignKey(Discount, on_delete=models.SET_NULL, null=True)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    business_day = models.ForeignKey(BusinessDay, on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="order_created_by_user",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="order_updated_by_user",
    )

    def save(self, *args, **kwargs):
        # Generate a unique ID if not set
        if not self.id:
            last_order = Order.objects.order_by("-id").first()
            self.id = (last_order.id + 1) if last_order else 1
        # Set created_at to current time if it is None
        if self.created_at is None:
            self.created_at = timezone.now()
        # Automatically set the shift based on check_in_time
        created_at = self.created_at.time()  # Extract time from datetime
        morning_start = time(9, 0)  # 9:00 AM
        morning_end = time(19, 0)  # 7:00 PM

        if morning_start <= created_at <= morning_end:
            self.shift = "morning"
        else:
            self.shift = "evening"

        # make auto kot number
        if not self.kot_number:
            last_order = Order.objects.order_by("-kot_number").first()
            self.kot_number = (last_order.kot_number + 1) if last_order else 1
        # Update the associated table's fields
        if self.table:
            # Ensure order hall matches table hall
            self.hall = self.table.hall

            if self.is_paid:
                # Scenario 2: Order is paid
                # Reset table fields to their origin
                self.table.no_of_pax = 0
                self.table.is_occupied = False
            else:
                # Scenario 1: Order is created or updated (not paid)
                # Update table fields based on the order
                self.table.no_of_pax = self.number_of_pax
                self.table.is_occupied = True
            # Save the table object
            self.table.save()

        super(Order, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Update the associated table's fields
        if self.table:
            self.table.no_of_pax = 0
            self.table.is_occupied = False
            self.table.save()
        super(Order, self).delete(*args, **kwargs)


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
    quantity = models.PositiveIntegerField()
    remaining_quantity = models.PositiveIntegerField()  # Unpaid quantity
    is_paid = models.BooleanField(default=False)
    quantity_to_print = models.PositiveIntegerField(default=0)
    is_printed = models.BooleanField(default=False)
    cancelled_quantity = models.PositiveIntegerField(default=0)  # Cancelled quantity
    paid_by = models.IntegerField(
        null=True, blank=True
    )  # Track which pax paid for this item
    notes = models.TextField(null=True, blank=True)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # Ensure `quantity` is not None
        self.quantity = self.quantity or 0

        # If remaining_quantity is None, initialize it to match quantity
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity

        # Ensure remaining_quantity is non-negative and does not exceed quantity

        if self.remaining_quantity > self.quantity:
            self.remaining_quantity = self.quantity

        # Automatically mark as paid if remaining_quantity is zero
        self.is_paid = self.remaining_quantity == 0
        # self.is_printed = self.quantity_to_print == 0
        # Recalculate sub_total based on remaining_quantity
        if not self.product.price:
            raise ValueError("Product price must be set to calculate sub_total.")
        self.sub_total = self.product.price * self.remaining_quantity

        super(OrderItems, self).save(*args, **kwargs)


class Payment(models.Model):
    PAYMENT_CHOICES = [
        ("cash", "Cash"),
        ("card", "Visa Card"),
        ("multi", "Multi"),
    ]
    orders = models.ManyToManyField(
        "Order", related_name="payments"
    )  # Changed from ForeignKey to ManyToMany

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    visa_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=50, default="cash", choices=PAYMENT_CHOICES
    )  # e.g., 'cash', 'credit card', etc.
    business_day = models.ForeignKey(BusinessDay, on_delete=models.SET_NULL, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        self.amount = self.cash_amount + self.visa_amount  # Ensure consistency
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.id}"
