from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.db.models import Sum, Q
from django.utils.timezone import now
from django.conf import settings
from django.http import FileResponse, Http404
from django.utils.dateparse import parse_date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.generics import GenericAPIView

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend


from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.order.models import (
    Order,
    OrderItems,
    Payment,
    Discount,
    BusinessDay,
)
from apps.product.models import Product
from apps.order.serializers import (
    OrderSerializer,
    OrderItemsSerializer,
    OrderDeletedSerializer,
    PaymentSerializer,
    PaymentMethodSerializer,
    DiscountSerializer,
    DiscountActiveSerializer,
    BusinessDaySerializer,
)
from apps.order.filters import OrderFilter, PaymentFilter
from apps.printer.models import Printer
from apps.category.models import Category

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import HasPermissionOrInGroupWithPermission
from cafe.util import (
    print_to_printer,
    format_bill,
    split_format_bill,
    group_format_bill,
    generate_report,
    print_report,
    save_report_as_pdf,
    generate_sales_report,
    save_sales_report_as_pdf,
    print_sales_report,
)

from decimal import Decimal
import os
from datetime import timedelta


# Order Views
class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.add_order"

    def perform_create(self, serializer):
        user = self.request.user
        order = serializer.save(created_by=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        created_object_id = serializer.instance.id

        return Response(
            {"id": created_object_id, "detail": _("Order created successfully")},
            status=status.HTTP_201_CREATED,
        )


class OrderAddMoreItems(generics.CreateAPIView):
    serializer_class = OrderItemsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Get the order_id from the URL parameters
        order_id = request.query_params.get("order_id")
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": _("Order does not exist.")},
                status=status.HTTP_404_NOT_FOUND,
            )
        if order.is_paid:
            return Response(
                {"detail": _("Order is already paid, You can not add more items")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        items = request.data
        new_items = []  # To store newly added items for printing

        # Calculate the total for new items
        new_items_total = Decimal("0.00")

        for item_data in items:
            product_id = item_data.get("product")
            quantity = int(item_data.get("quantity", 1))  # Default quantity to 1
            notes = item_data.get("notes")
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"detail": _("Product not found")},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if the product is already in the order
            order_item = OrderItems.objects.filter(order=order, product=product).first()
            if order_item:
                # Update the quantity and remaining_quantity
                order_item.quantity += quantity
                order_item.notes = notes
                order_item.remaining_quantity += quantity  # Add to remaining_quantity
                order_item.quantity_to_print += quantity  # Add to quantity_to_print
                order_item.is_printed = False
                order_item.save()
                new_items_total += order_item.sub_total
            else:
                # Create a new order item with quantity and remaining_quantity
                order_item = OrderItems.objects.create(
                    order=order,
                    product=product,
                    notes=notes,
                    quantity=quantity,
                    remaining_quantity=quantity,  # Initialize remaining_quantity
                    quantity_to_print=quantity,
                    is_printed=False,
                )
                new_items.append(order_item)
                new_items_total += order_item.sub_total

        # Recalculate final_total and vat for the order
        order.final_total = OrderItems.objects.filter(order=order).aggregate(
            total=Sum("sub_total")
        )["total"] or Decimal("0.00")
        order.vat = order.final_total - (
            order.final_total / Decimal("1.05")
        )  # Assuming 5% VAT
        # Apply discount if applicable
        discount_value = order.discount.value if order.discount else Decimal("0.00")
        # Calculate grand_total
        order.grand_total = order.final_total - discount_value
        # Ensure grand_total is non-negative (in case of large discounts)
        if order.grand_total < Decimal("0.00"):
            order.grand_total = Decimal("0.00")
        order.save()

        return Response(
            {"detail": _("Items added to order successfully")},
            status=status.HTTP_201_CREATED,
        )


class OrderItemNote(generics.UpdateAPIView):
    queryset = OrderItems.objects.all()
    serializer_class = OrderItemsSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_object(self):
        order_item_id = self.request.query_params.get("order_item_id")
        order_item = get_object_or_404(OrderItems, id=order_item_id)
        return order_item

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Notes updated successfully")}, status=status.HTTP_200_OK
        )


class OrderPrintNewItems(generics.GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_all_categories(self, category):
        """Recursively fetch all parent and child categories."""
        categories = set()
        categories.add(category)

        # Get all parent categories
        parent = category.parent
        while parent:
            categories.add(parent)
            print(f"Found parent: {parent.name}")
            parent = parent.parent

        # Get all child categories
        def get_children(cat):
            children = Category.objects.filter(parent=cat)
            for child in children:
                categories.add(child)
                print(f"Found child: {child.name}")
                get_children(child)

        get_children(category)

        print(
            f"Final category set for '{category.name}': {[c.name for c in categories]}"
        )
        return categories

    def category_matches(self, item, target_category_name):
        """Check if a product belongs to a category or any of its subcategories."""
        target_category_name = target_category_name.lower()  # Normalize input

        for category in item.product.category.all():
            all_categories = self.get_all_categories(category)  # Fetch full hierarchy

            # Debugging output: Print all category names being checked
            print(
                f"Checking item '{item.product.name}' against category '{target_category_name}'"
            )
            print("All related categories:", [c.name.lower() for c in all_categories])

            if any(c.name.lower() == target_category_name for c in all_categories):
                print(f" Match found: '{target_category_name}' in {category.name}")
                return True

        print(f" No match for '{target_category_name}' in item '{item.product.name}'")
        return False

    def post(self, request, *args, **kwargs):
        order_id = request.query_params.get("order_id")
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": _("Order does not exist.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get unprinted items
        new_items = OrderItems.objects.filter(order=order, is_printed=False)

        if not new_items.exists():
            return Response(
                {"detail": _("No new items to print.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch the printers
        barista_printer = Printer.objects.filter(printer_type="barista").first()
        shisha_printer = Printer.objects.filter(printer_type="shisha").first()
        kitchen_printer = Printer.objects.filter(printer_type="kitchen").first()

        # Group items by category, including subcategories
        barista_items = [
            item for item in new_items if self.category_matches(item, "drinks")
        ]
        shisha_items = [
            item for item in new_items if self.category_matches(item, "shisha")
        ]
        kitchen_items = [
            item for item in new_items if self.category_matches(item, "food")
        ]

        # Prepare text output for each category
        barista_text, shisha_text, kitchen_text = [], [], []

        # Print for barista
        if barista_printer and barista_items:
            current_time = now().strftime("%H:%M")  # Format time as HH:MM
            barista_text.append("New Drinks Order:")
            barista_text.append(
                f"Order No: {order.id} - Table No:{order.table.table_number}"
            )
            barista_text.append(f"Time: {current_time}")  # Print formatted time
            barista_text.append("---------")
            for item in barista_items:
                barista_text.append(
                    f"{item.product.name} - {item.quantity_to_print} Nos"
                )
                barista_text.append(f"{item.product.name_ar}")
                barista_text.append(f"Notes: {item.notes}")
            print_to_printer(barista_printer.ip_address, "\n".join(barista_text))

        # Print for shisha
        if shisha_printer and shisha_items:
            current_time = now().strftime("%H:%M")  # Format time as HH:MM
            shisha_text.append("New Shisha Order:")
            shisha_text.append(
                f"Order No: {order.id} - Table No:{order.table.table_number}"
            )
            shisha_text.append(f"Time: {current_time}")  # Print formatted time
            shisha_text.append("---------")

            for item in shisha_items:
                shisha_text.append(
                    f"{item.product.name} - {item.quantity_to_print} Nos"
                )
                shisha_text.append(f"Notes: {item.notes}")
                shisha_text.append(f"{item.product.name_ar}")
            print_to_printer(shisha_printer.ip_address, "\n".join(shisha_text))

        # Print for food
        if kitchen_printer and kitchen_items:
            current_time = now().strftime("%H:%M")  # Format time as HH:MM
            kitchen_text.append("New Kitchen Order:")
            kitchen_text.append(
                f"Order No: {order.id} - Table No:{order.table.table_number}"
            )
            kitchen_text.append(f"Time: {current_time}")  # Print formatted time
            kitchen_text.append("---------")
            for item in kitchen_items:
                kitchen_text.append(
                    f"{item.product.name} - {item.quantity_to_print} Nos"
                )
                kitchen_text.append(f"{item.product.name_ar}")
                kitchen_text.append(f"Notes: {item.notes}")
            print_to_printer(kitchen_printer.ip_address, "\n".join(kitchen_text))

        # Mark items as printed and reset `quantity_to_print`
        new_items.update(
            quantity_to_print=0,
            is_printed=True,
        )

        return Response(
            {
                "detail": _("New items printed successfully."),
                "barista_text": (
                    barista_text if barista_text else _("No drinks to print.")
                ),
                "shisha_text": shisha_text if shisha_text else _("No shisha to print."),
                "kitchen_text": (
                    kitchen_text if kitchen_text else _("No food to print.")
                ),
            },
            status=status.HTTP_200_OK,
        )


class OrderRemoveItems(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = OrderItemsSerializer

    def get_all_categories(self, category):
        """Recursively fetch all parent and child categories."""
        categories = set()
        categories.add(category)

        # Get all parent categories
        parent = category.parent
        while parent:
            categories.add(parent)
            parent = parent.parent

        # Get all child categories
        def get_children(cat):
            children = Category.objects.filter(parent=cat)
            for child in children:
                categories.add(child)
                get_children(child)

        get_children(category)
        return categories

    def category_matches(self, item, target_category_name):
        """Check if a product belongs to a category or any of its subcategories."""
        target_category_name = target_category_name.lower()

        for category in item.product.category.all():
            all_categories = self.get_all_categories(category)
            if any(c.name.lower() == target_category_name for c in all_categories):
                return True
        return False

    def destroy(self, request, *args, **kwargs):
        order_id = request.query_params.get("order_id")
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": _("Order does not exist.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        items = request.data
        cancel_reason = items[0].get("cancel_reason") if items else None
        removed_items = []
        removed_items_total = Decimal("0.00")

        # Fetch printers
        barista_printer = Printer.objects.filter(printer_type="barista").first()
        shisha_printer = Printer.objects.filter(printer_type="shisha").first()
        kitchen_printer = Printer.objects.filter(printer_type="kitchen").first()

        barista_text, shisha_text, kitchen_text = [], [], []

        for item_data in items:
            product_id = item_data.get("product")
            quantity_to_remove = int(item_data.get("quantity", 1))

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"detail": _("Product not found.")},
                    status=status.HTTP_404_NOT_FOUND,
                )

            order_item = get_object_or_404(OrderItems, order=order, product=product)

            # Prevent removing an already canceled item
            if order_item.quantity == 0:
                return Response(
                    {
                        "detail": _(
                            f"Item '{order_item.product.name}' is already canceled and cannot be removed again."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Ensure removal does not exceed available quantity
            if quantity_to_remove > order_item.quantity:
                quantity_to_remove = order_item.quantity  # Limit removal

            removed_items.append(order_item.product.name)
            removed_items_total += (
                order_item.sub_total / order_item.quantity
            ) * quantity_to_remove

            # Update item details (without deleting)
            if order_item.is_printed:

                order_item.cancelled_quantity += quantity_to_remove
            # ✅ Fix: Only reduce by removed amount, not reset to zero
            order_item.quantity -= quantity_to_remove
            order_item.remaining_quantity -= quantity_to_remove

            # If all items are removed, update sub_total
            if order_item.quantity == 0:
                order_item.sub_total = 0  # Since it no longer contributes to total

            order_item.quantity_to_print = 0
            order_item.save()

            # Print removal notification if previously printed
            current_time = now().strftime("%H:%M")
            order_time = order.created_at.strftime("%H:%M")

            item_text = [
                f"Order No: {order.id} - Table No: {order.table.table_number}",
                f"Order Time: {order_time}",
                f"Cancel Time: {current_time}",
                f"Removed Item: {order_item.product.name} - {quantity_to_remove} Nos",
                f"              {order_item.product.name_ar}",
                f"Cancel Reason: {cancel_reason}",
            ]

            if (
                order_item.is_printed
                and self.category_matches(order_item, "drinks")
                and barista_printer
            ):
                barista_text.extend(item_text)
                print_to_printer(barista_printer.ip_address, "\n".join(barista_text))

            if (
                order_item.is_printed
                and self.category_matches(order_item, "shisha")
                and shisha_printer
            ):
                shisha_text.extend(item_text)
                print_to_printer(shisha_printer.ip_address, "\n".join(shisha_text))

            if (
                order_item.is_printed
                and self.category_matches(order_item, "food")
                and kitchen_printer
            ):
                kitchen_text.extend(item_text)
                print_to_printer(kitchen_printer.ip_address, "\n".join(kitchen_text))

        # Update order totals
        order.final_total -= removed_items_total
        order.final_total = max(0, order.final_total)  # Ensure no negative totals
        order.vat = order.final_total - (order.final_total / Decimal("1.05"))
        discount_value = order.discount.value if order.discount else Decimal("0.00")
        order.grand_total = max(Decimal("0.00"), order.final_total - discount_value)
        order.save()

        return Response(
            {
                "detail": _("Items removed from order successfully."),
                "removed_items": removed_items,
                "barista_text": (
                    barista_text if barista_text else _("No drinks removed.")
                ),
                "shisha_text": shisha_text if shisha_text else _("No shisha removed."),
                "kitchen_text": kitchen_text if kitchen_text else _("No food removed."),
            },
            status=status.HTTP_200_OK,
        )


class OrderChangeTableView(generics.UpdateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.change_order"
    lookup_field = "id"

    def get_object(self):
        order_id = self.request.query_params.get("order_id")
        order = get_object_or_404(Order, id=order_id)
        return order

    def update(self, request, *args, **kwargs):
        from apps.table.models import Table

        order = self.get_object()
        old_table = order.table
        new_table_id = request.data.get("new_table")

        # Validate new table
        if not new_table_id:
            return Response(
                {"detail": _("New table ID is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_table = get_object_or_404(Table, id=new_table_id)

        # Prevent assigning the same table
        if old_table and old_table.id == new_table.id:
            return Response(
                {"detail": _("Table is the same.")}, status=status.HTTP_400_BAD_REQUEST
            )

        # Update order table
        order.table = new_table
        order.save()

        # Check if the old table is still in use
        if old_table:
            old_table_in_use = Order.objects.filter(table=old_table).exists()
            print(f"Old table in use: {old_table_in_use}")  # Debugging line
            if not old_table_in_use:
                old_table.is_occupied = False
                old_table.save()
                print(
                    f"Old table {old_table.id} marked as unoccupied."
                )  # Debugging line

        # Mark the new table as occupied
        new_table.is_occupied = True
        new_table.save()
        print(f"New table {new_table.id} marked as occupied.")  # Debugging line

        return Response(
            {"detail": _("Table changed successfully.")}, status=status.HTTP_200_OK
        )


class ApplyDiscountToOrderView(generics.UpdateAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.add_discount"
    lookup_field = "id"

    def get_object(self):
        order_id = self.request.query_params.get("order_id")
        return get_object_or_404(Order, id=order_id)

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        # Check if the order is already paid
        if order.is_paid:
            return Response(
                {"detail": _("Cannot apply discount to a paid order")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get discount value and reason from request body
        discount_value = Decimal(request.data.get("value", "0.00"))
        discount_reason = request.data.get("discount_reason", None)

        # Check if the order is associated with a table that is owned (is_owner=True)
        if order.table and order.table.is_owner:
            discount_value = order.final_total  # Set discount to full order total

        # Ensure discount does not exceed order final total
        discount_value = min(discount_value, order.final_total)

        # Create a new discount record
        discount = Discount.objects.create(
            value=discount_value,
            discount_reason=discount_reason,
            created_by=request.user,
            updated_by=request.user,
        )

        # Apply discount to order
        order.discount = discount
        order.grand_total = order.final_total - discount_value

        # Ensure grand_total is not negative
        order.grand_total = max(order.grand_total, Decimal("0.00"))

        # Save updated order
        order.save()

        return Response(
            {"detail": _("Discount applied successfully")},
            status=status.HTTP_200_OK,
        )


class RemoveDiscountFromOrderView(generics.UpdateAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.delete_discount"
    lookup_field = "id"

    def get_object(self):
        order_id = self.request.query_params.get("order_id")
        order = get_object_or_404(Order, id=order_id)
        return order

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        # Check if the order is already paid
        if order.is_paid:
            return Response(
                {"detail": _("Cannot remove discount from a paid order")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if a discount is applied to the order
        if not order.discount:
            return Response(
                {"detail": _("No discount applied to this order")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove the discount and recalculate grand total
        discount_value = order.discount.value
        order.discount = None  # Remove the applied discount
        order.grand_total += discount_value  # Recalculate the grand total by adding the discount value back

        # Ensure total is not negative
        if order.grand_total < Decimal("0.00"):
            order.grand_total = Decimal("0.00")

        # Save the updated order
        order.save()

        return Response(
            {"detail": _("Discount removed and grand total recalculated successfully")},
            status=status.HTTP_200_OK,
        )


class SplitBillView(generics.CreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        order_id = request.query_params.get("order_id")
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": _("Order not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.is_paid:
            return Response(
                {"detail": _("Cannot split an order because it's already fully paid.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = request.data.get("items")
        payment_method = request.data.get("payment_method")
        cash_amount = request.data.get("cash_amount", 0)
        visa_amount = request.data.get("visa_amount", 0)

        if not items:
            return Response(
                {"detail": _("Items are required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            total_payment_amount = Decimal("0.00")
            selected_items = []

            with transaction.atomic():
                # 🔹 Find the last open business day
                last_business_day = (
                    BusinessDay.objects.filter(end_time__isnull=True)
                    .order_by("-start_time")
                    .first()
                )

                if not last_business_day:
                    return Response(
                        {
                            "error": _(
                                "No active business day found. Please start a new business day."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                for item_data in items:
                    product_id = item_data.get("product")
                    quantity_to_pay = item_data.get("quantity")

                    if not product_id or quantity_to_pay is None:
                        return Response(
                            {"detail": _("Product ID and quantity are required.")},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    order_item = OrderItems.objects.get(
                        product__id=product_id, order=order
                    )

                    if quantity_to_pay > order_item.remaining_quantity:
                        return Response(
                            {
                                "detail": _(
                                    "Quantity exceeds remaining unpaid quantity."
                                )
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    item_total = Decimal(quantity_to_pay) * order_item.product.price
                    total_payment_amount += item_total

                    order_item.remaining_quantity -= quantity_to_pay

                    if order_item.remaining_quantity == 0:
                        order_item.is_paid = True

                    order_item.sub_total = (
                        order_item.remaining_quantity * order_item.product.price
                    )
                    order_item.save()

                    selected_items.append(
                        {"product": order_item.product, "quantity": quantity_to_pay}
                    )

                vat = total_payment_amount - (total_payment_amount / Decimal("1.05"))

                # Handle different payment methods
                if payment_method == "multi":
                    try:
                        cash_amount = Decimal(cash_amount)
                        visa_amount = Decimal(visa_amount)
                    except ValueError:
                        return Response(
                            {"detail": _("Invalid cash or visa amount.")},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if cash_amount + visa_amount != total_payment_amount:
                        return Response(
                            {
                                "detail": _(
                                    "Cash and Visa amounts must sum to the total amount."
                                )
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                elif payment_method == "cash":
                    cash_amount, visa_amount = total_payment_amount, 0
                elif payment_method == "card":
                    cash_amount, visa_amount = 0, total_payment_amount
                else:
                    return Response(
                        {"detail": _("Invalid payment method.")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # 🔹 Create payment and assign to business day
                payment = Payment.objects.create(
                    amount=total_payment_amount,
                    payment_method=payment_method,
                    cash_amount=cash_amount,
                    visa_amount=visa_amount,
                    created_by=request.user,
                    business_day=last_business_day,  # Assign payment to business day
                )
                payment.orders.add(order)

                # Generate the formatted bill **after** payment is created
                formatted_bill, logo_path, pdf_path = split_format_bill(
                    order,
                    payment.id,
                    selected_items,
                    total_payment_amount,
                    vat,
                    save_as_pdf=True,
                )

                # Print receipt if a cashier printer exists
                cashier_printer = Printer.objects.filter(printer_type="cashier").first()
                if cashier_printer:
                    try:
                        print_to_printer(
                            cashier_printer.ip_address, formatted_bill, logo_path
                        )
                    except Exception as e:
                        print(f"Printing failed for order {order.id}: {e}")

                self.recalculate_order(
                    order, last_business_day
                )  # Assign business day to order

            return Response(
                {
                    "detail": _("Bill split successfully."),
                    "formatted_bill": formatted_bill,
                    "pdf_path": request.build_absolute_uri(pdf_path),
                    "payment_id": payment.id,
                },
                status=status.HTTP_200_OK,
            )

        except OrderItems.DoesNotExist:
            return Response(
                {"error": _("Order item not found for the specified product.")},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def recalculate_order(self, order, business_day):
        """Recalculates order totals after splitting a bill."""
        order_items = OrderItems.objects.filter(order=order)

        final_total = sum(
            (
                Decimal(item.remaining_quantity) * item.product.price
                for item in order_items
            )
        )

        vat = final_total - (final_total / Decimal("1.05"))

        discount_value = order.discount.value if order.discount else Decimal("0.00")

        order.final_total = final_total
        order.vat = vat.quantize(Decimal("0.01"))
        order.grand_total = max(order.final_total - discount_value, Decimal("0.00"))

        if all(item.is_paid for item in order_items):
            order.is_paid = True
            order.check_out_time = now()

        order.business_day = business_day  # 🔹 Assign order to business day
        order.save()


class GenerateBillView(generics.RetrieveAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.filter(is_paid=False)
    serializer_class = OrderSerializer

    def get_object(self):
        order_id = self.request.query_params.get("order_id")
        return get_object_or_404(Order, id=order_id)

    def retrieve(self, request, *args, **kwargs):
        order = self.get_object()

        if order.is_paid:
            return Response(
                {"detail": _("Order has already been checked out.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_payment_amount = order.grand_total
        vat = order.vat

        if total_payment_amount is None:
            return Response(
                {"detail": _("Grand total is missing for the order.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate the bill
        formatted_bill, logo_path, pdf_path = format_bill(
            order, None, total_payment_amount, vat, save_as_pdf=True
        )

        # Optionally print the bill
        cashier_printer = Printer.objects.filter(printer_type="cashier").first()
        if cashier_printer:
            try:
                print_to_printer(cashier_printer.ip_address, formatted_bill, logo_path)
            except Exception as e:
                print(f"Failed to print order {order.id}: {e}")

        response_data = {
            "detail": _("Bill generated successfully."),
            "bill": formatted_bill,
            "pdf_path": request.build_absolute_uri(pdf_path),
        }
        return Response(response_data, status=status.HTTP_200_OK)


class CheckoutOrderView(generics.UpdateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_object(self):
        order_id = self.request.query_params.get("order_id")
        return get_object_or_404(Order, id=order_id)

    def update(self, request, *args, **kwargs):
        order = self.get_object()

        if order.is_paid:
            return Response(
                {"detail": _("Order is already checked out.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        grand_total = order.grand_total
        if grand_total is None:
            return Response(
                {"detail": _("Final total is missing for the order.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method = request.data.get("payment_method")
        cash_amount = request.data.get("cash_amount", 0)
        visa_amount = request.data.get("visa_amount", 0)

        if not payment_method:
            return Response(
                {"detail": _("Payment method is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate multi-payment amounts
        if payment_method == "multi":
            try:
                cash_amount = Decimal(cash_amount)
                visa_amount = Decimal(visa_amount)
            except ValueError:
                return Response(
                    {"detail": _("Invalid cash or visa amount.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if cash_amount + visa_amount != grand_total:
                return Response(
                    {
                        "detail": _(
                            "Cash and Visa amounts must sum to the total amount."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:  # Single payment type (Cash or Visa)
            if payment_method == "cash":
                cash_amount, visa_amount = grand_total, 0
            elif payment_method == "card":
                cash_amount, visa_amount = 0, grand_total
            else:
                return Response(
                    {"detail": _("Invalid payment method.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        order_items = list(OrderItems.objects.filter(order=order))

        # 🔹 Find the last open business day
        last_business_day = (
            BusinessDay.objects.filter(end_time__isnull=True)
            .order_by("-start_time")
            .first()
        )

        if not last_business_day:
            return Response(
                {
                    "detail": _(
                        "No active business day found. Please start a new business day."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔹 Assign the order and payment to the last business day
        with transaction.atomic():
            payment = Payment.objects.create(
                amount=grand_total,
                payment_method=payment_method,
                cash_amount=cash_amount,
                visa_amount=visa_amount,
                created_by=request.user,
                business_day=last_business_day,  # Assign payment to business day
            )
            payment.orders.add(order)

            order.is_paid = True
            order.check_out_time = now()
            order.business_day = last_business_day  # Assign order to business day
            order.save()

        #  Move `format_bill` **after** creating payment
        formatted_bill, logo_path, pdf_path = format_bill(
            order, payment.id, grand_total, order.vat, save_as_pdf=True
        )

        # Update order items
        for item in order_items:
            item.is_paid = True
            item.remaining_quantity = 0
            item.save()

        # Print receipt if a cashier printer exists
        cashier_printer = Printer.objects.filter(printer_type="cashier").first()
        if cashier_printer:
            try:
                print_to_printer(cashier_printer.ip_address, formatted_bill, logo_path)
            except Exception as e:
                print(f"Failed to print order {order.id}: {e}")

        response_data = {
            "detail": _("Order checked out and payment recorded successfully."),
            "bill": formatted_bill,
            "pdf_path": request.build_absolute_uri(pdf_path),
        }
        if logo_path:
            response_data["logo"] = logo_path

        return Response(response_data, status=status.HTTP_200_OK)


class GroupBillsView(generics.CreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        order_ids = request.data.get("order_ids")
        if not order_ids:
            return Response({"error": _("Order IDs are required.")}, status=400)

        try:
            orders = Order.objects.filter(id__in=order_ids, is_paid=False)
            if not orders.exists():
                return Response({"error": _("No unpaid orders found.")}, status=400)

            total_payment_amount = sum(
                order.grand_total for order in orders if order.grand_total
            )
            if total_payment_amount == 0:
                return Response(
                    {"error": _("Orders have missing or zero final totals.")},
                    status=400,
                )

            vat = sum(order.vat for order in orders if order.vat)

            payment_method = request.data.get("payment_method")
            cash_amount = request.data.get("cash_amount", 0)
            visa_amount = request.data.get("visa_amount", 0)

            if not payment_method:
                return Response({"error": _("Payment method is required.")}, status=400)

            with transaction.atomic():
                # 🔹 Find the last open business day
                last_business_day = (
                    BusinessDay.objects.filter(end_time__isnull=True)
                    .order_by("-start_time")
                    .first()
                )

                if not last_business_day:
                    return Response(
                        {
                            "error": _(
                                "No active business day found. Please start a new business day."
                            )
                        },
                        status=400,
                    )

                # Handle different payment methods
                if payment_method == "multi":
                    try:
                        cash_amount = Decimal(cash_amount)
                        visa_amount = Decimal(visa_amount)
                    except ValueError:
                        return Response(
                            {"error": _("Invalid cash or visa amount.")}, status=400
                        )

                    if cash_amount + visa_amount != total_payment_amount:
                        return Response(
                            {
                                "error": _(
                                    "Cash and Visa amounts must sum to the total amount."
                                )
                            },
                            status=400,
                        )
                elif payment_method == "cash":
                    cash_amount, visa_amount = total_payment_amount, 0
                elif payment_method == "card":
                    cash_amount, visa_amount = 0, total_payment_amount
                else:
                    return Response({"error": _("Invalid payment method.")}, status=400)

                # 🔹 Create a single payment record for all orders
                payment = Payment.objects.create(
                    amount=total_payment_amount,
                    payment_method=payment_method,
                    cash_amount=cash_amount,
                    visa_amount=visa_amount,
                    created_by=request.user,
                    business_day=last_business_day,  # Assign payment to business day
                )
                payment.orders.set(orders)

                # 🔹 Update and mark orders as paid
                for order in orders:
                    order.is_paid = True
                    order.check_out_time = now()
                    order.business_day = (
                        last_business_day  # Assign order to business day
                    )
                    order.save()

                # Generate the combined bill **after** payment is created
                formatted_bill, logo_path, pdf_path = group_format_bill(
                    orders, payment.id, total_payment_amount, vat, save_as_pdf=True
                )

                # Update all order items
                for order in orders:
                    order_items = OrderItems.objects.filter(order=order)
                    for item in order_items:
                        item.is_paid = True
                        item.remaining_quantity = 0
                        item.save()

                # Print the combined bill if a cashier printer exists
                cashier_printer = Printer.objects.filter(printer_type="cashier").first()
                if cashier_printer:
                    try:
                        print_to_printer(
                            cashier_printer.ip_address, formatted_bill, logo_path
                        )
                    except Exception as e:
                        print(f"Failed to print group bill: {e}")

            return Response(
                {
                    "detail": _("Group bills processed successfully."),
                    "combined_bill": formatted_bill,
                    "pdf_path": request.build_absolute_uri(pdf_path),
                    "logo": logo_path if logo_path else None,
                },
                status=200,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class FetchInvoiceView(GenericAPIView):
    def get(self, request, *args, **kwargs):
        # Extract the invoice ID from query parameters
        invoice_id = request.query_params.get("invoice_id")
        if not invoice_id:
            return Response({"detail": _("Invoice ID is required.")}, status=400)

        # Define the path to the invoices folder
        invoice_folder = os.path.join(settings.MEDIA_ROOT, "uploads", "bills")

        # Generate the expected file name
        filename = f"invoice_{invoice_id}.pdf"
        file_path = os.path.join(invoice_folder, filename)

        # Check if the file exists
        if not os.path.exists(file_path):
            raise Http404("Invoice not found.")

        # Serve the file as a response
        return FileResponse(open(file_path, "rb"), content_type="application/pdf")


class OrderUnpaidListView(generics.ListAPIView):
    queryset = Order.objects.filter(is_paid=False, is_deleted=False).order_by(
        "-created_at"
    )
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.view_order"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ["id", "created_at"]


class OrderPaidListView(generics.ListAPIView):
    queryset = Order.objects.filter(is_paid=True, is_deleted=False).order_by(
        "-created_at"
    )
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.view_order"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ["id", "created_at"]


class OrderDeletedListView(generics.ListAPIView):
    queryset = Order.objects.filter(is_deleted=True).order_by("-created_at")
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.view_order"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ["id", "created_at"]


class OrderRetrieve(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.view_order"
    lookup_field = "id"

    def get_object(self):
        order_id = self.request.query_params.get("order_id")
        order = get_object_or_404(Order, id=order_id)
        return order


class OrderDeleteTemporaryView(generics.UpdateAPIView):
    serializer_class = OrderDeletedSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.delete_order"

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        order_ids = request.data.get("order_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == False:
            return Response(
                {"detail": _("These orders are not deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for order_id in order_ids:
            instance = get_object_or_404(Order, id=order_id)
            if instance.is_deleted:
                return Response(
                    {
                        "detail": _(
                            "Product with ID {} is already temp deleted".format(
                                order_id
                            )
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            instance.is_active = False
            instance.save()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        return Response(
            {"detail": _("Orders temp deleted successfully")},
            status=status.HTTP_200_OK,
        )


class OrderRestoreView(generics.RetrieveUpdateAPIView):

    serializer_class = OrderDeletedSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.delete_order"

    def update(self, request, *args, **kwargs):
        order_ids = request.data.get("order_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == True:
            return Response(
                {"detail": _("Products are already deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for order_id in order_ids:
            instance = get_object_or_404(Order, id=order_id)
            if instance.is_deleted == False:
                return Response(
                    {"detail": _("Product with ID {} is not deleted".format(order_id))},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            instance.is_active = True

            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        return Response(
            {"detail": _("Orders restored successfully")}, status=status.HTTP_200_OK
        )


class OrderDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.delete_order"

    def delete(self, request, *args, **kwargs):
        order_ids = request.data.get("order_id", [])
        for order_id in order_ids:
            instance = get_object_or_404(Order, id=order_id)
            instance.delete()
        return Response(
            {"detail": _("Order permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


# payment views


class PaymentListView(generics.ListAPIView):
    queryset = Payment.objects.all().order_by("-created_at")
    serializer_class = PaymentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "payment.view_payment"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ["id", "created_at"]


class PaymentRetrieveView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "payment.view_payment"
    lookup_field = "id"

    def get_object(self):
        payment_id = self.request.query_params.get("payment_id")
        payment = get_object_or_404(Payment, id=payment_id)
        return payment


class PaymentDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.delete_payment"

    def delete(self, request, *args, **kwargs):
        payment_ids = request.data.get("payment_id", [])
        for payment_id in payment_ids:
            instance = get_object_or_404(Payment, id=payment_id)
            instance.delete()
        return Response(
            {"detail": _("Payment permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class PaymentMethodDialogView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        payment_method_choices = [
            {"value": "cash", "display": _("Cash")},
            {"value": "card", "display": _("Visa Card")},
            {"value": "multi", "display": _("Multi")},
        ]
        serializer = PaymentMethodSerializer(payment_method_choices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# discount Views
class DiscountCreateView(generics.CreateAPIView):
    serializer_class = DiscountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.add_discount"

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(created_by=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        created_object_id = serializer.instance.id

        return Response(
            {"id": created_object_id, "detail": _("Discount created successfully")},
            status=status.HTTP_201_CREATED,
        )


class DiscountListView(generics.ListAPIView):
    queryset = Discount.objects.filter(is_active=True).order_by("-id")
    serializer_class = DiscountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.view_discount"
    pagination_class = StandardResultsSetPagination


class DiscountInactiveListView(generics.ListAPIView):
    queryset = Discount.objects.filter(is_active=False).order_by("-id")
    serializer_class = DiscountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.view_discount"
    pagination_class = StandardResultsSetPagination


class DiscountRetrieveView(generics.RetrieveAPIView):
    serializer_class = DiscountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.view_discount"
    lookup_field = "id"

    def get_object(self):
        discount_id = self.request.query_params.get("discount_id")
        discount = get_object_or_404(Discount, id=discount_id)
        return discount


class DiscountUpdateView(generics.UpdateAPIView):
    serializer_class = DiscountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.change_discount"
    lookup_field = "id"

    def get_object(self):
        discount_id = self.request.query_params.get("discount_id")
        discount = get_object_or_404(Discount, id=discount_id)
        return discount

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Discount updated successfully")}, status=status.HTTP_200_OK
        )


class DiscountChangeStatusView(generics.UpdateAPIView):
    serializer_class = DiscountActiveSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.change_discount"

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        discount_ids = request.data.get("discount_id", [])
        partial = kwargs.pop("partial", False)
        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {"detail": _("'is_active' field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for discount_id in discount_ids:
            instance = get_object_or_404(Discount, id=discount_id)
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
        return Response(
            {"detail": _("Discount status changed successfully")},
            status=status.HTTP_200_OK,
        )


class DiscountDeleteView(generics.DestroyAPIView):
    serializer_class = DiscountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.delete_discount"

    def delete(self, request, *args, **kwargs):
        discount_ids = request.data.get("discount_id", [])
        for discount_id in discount_ids:
            instance = get_object_or_404(Discount, id=discount_id)
            instance.delete()
        return Response(
            {"detail": _("Discount permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class CloseDayAPIView(generics.CreateAPIView):
    serializer_class = BusinessDaySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.add_businessday"

    def create(self, request, *args, **kwargs):
        current_time = now()

        # Check if there's any existing business day (open or closed)
        last_business_day = BusinessDay.objects.order_by("-start_time").first()

        if last_business_day:
            # If there is an open business day, close it
            if last_business_day.end_time is None:
                last_business_day.end_time = current_time
                last_business_day.closed_by = request.user
                last_business_day.save()

                # Assign all orders and payments made after the last closing time
                Order.objects.filter(
                    business_day__isnull=True,
                    created_at__gte=last_business_day.start_time,
                ).update(business_day=last_business_day)

                Payment.objects.filter(
                    business_day__isnull=True,
                    created_at__gte=last_business_day.start_time,
                ).update(business_day=last_business_day)

        else:
            # No business day exists (first day of operation)
            new_business_day = BusinessDay.objects.create(start_time=current_time)
            return Response(
                {
                    "detail": _("First business day started."),
                    "business_day_id": str(new_business_day.id),
                },
                status=status.HTTP_201_CREATED,
            )

        # Create a new business day
        new_business_day = BusinessDay.objects.create(start_time=current_time)

        return Response(
            {"detail": _("Business day closed successfully and new one started.")},
            status=status.HTTP_200_OK,
        )


class CloseDayListView(generics.ListAPIView):
    queryset = BusinessDay.objects.all()
    serializer_class = BusinessDaySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class CloseDayDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, *args, **kwargs):
        businessday_ids = request.data.get("closeday_id", [])
        for businessday_id in businessday_ids:
            instance = get_object_or_404(BusinessDay, id=businessday_id)
            instance.delete()
        return Response(
            {"detail": _("Business day deleted successfully.")},
            status=status.HTTP_204_NO_CONTENT,
        )


class XReportView(generics.GenericAPIView):
    """
    Generate X Report, save as PDF, print the report, and return file path.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        day = request.query_params.get("day")
        if not day:
            return Response(
                {"detail": _("Please provide a day in query params.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parsed_day = parse_date(day)
            if not parsed_day:
                raise ValueError
        except ValueError:
            return Response(
                {"detail": _("Invalid date format. Use YYYY-MM-DD.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        business_day = (
            BusinessDay.objects.filter(
                Q(start_time__date__lte=parsed_day)
                & (
                    Q(end_time__date__gte=parsed_day) | Q(end_time__isnull=True)
                )  # Ensures the day is ongoing or ended after parsed_day
            )
            .order_by("-start_time")
            .first()
        )
        if not business_day:
            return Response(
                {"detail": _("No business day found for this date.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Ensure orders are from this business day
        orders = Order.objects.filter(business_day=business_day)

        if not orders.exists():
            return Response({"detail": _("No orders found for this business day.")})

        # Generate the report
        report_data = generate_report(business_day)

        pdf_path = save_report_as_pdf(report_data, report_type="X", date=parsed_day)

        # Print the report
        print_result = print_report(report_data, report_type="X")

        if isinstance(print_result, str) and print_result.startswith("Printing failed"):
            return Response(
                {
                    "detail": _(
                        "X Report generated successfully, but printing failed."
                    ),
                    "pdf_path": request.build_absolute_uri(pdf_path),
                    "print_error": print_result,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "detail": _("X Report generated and printed successfully."),
                "pdf_path": request.build_absolute_uri(pdf_path),
            }
        )


class ZReportView(generics.GenericAPIView):
    """
    Close the current business day, generate the Z Report,
    save it as a PDF, and print it.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        current_time = now()

        # Get the last business day (open or closed)
        last_business_day = BusinessDay.objects.order_by("-start_time").first()

        if last_business_day:
            if last_business_day.end_time is None:
                # Close the current open business day
                last_business_day.end_time = current_time
                last_business_day.is_closed = True
                last_business_day.closed_by = request.user
                last_business_day.save()

        # else:
        #     # No business day exists (first day of operation)
        #     first_business_day = BusinessDay.objects.create(
        #         start_time=current_time - timedelta(days=1)
        #     )
        #     return Response(
        #         {
        #             "detail": _("First business day started for yesterday."),
        #             "business_day_id": str(first_business_day.id),
        #         },
        #         status=status.HTTP_201_CREATED,
        #     )

        # **Prevent creating a new business day if one already exists for today**
        existing_business_day = BusinessDay.objects.filter(
            start_time__date=current_time.date(), end_time__isnull=True
        ).first()

        if existing_business_day:
            return Response(
                {
                    "detail": _("An open business day already exists for today."),
                    "business_day_id": str(existing_business_day.id),
                },
                status=status.HTTP_400_BAD_REQUEST,  # Invalid request
            )

        # Otherwise, create a new business day
        new_business_day = BusinessDay.objects.create(start_time=current_time)

        # Generate the Z Report for the closed business day
        report_data = generate_report(last_business_day)
        pdf_path = save_report_as_pdf(
            report_data, report_type="Z", date=last_business_day.start_time.date()
        )

        # Print the report
        print_result = print_report(report_data, report_type="Z")

        if isinstance(print_result, str) and print_result.startswith("Printing failed"):
            return Response(
                {
                    "detail": _(
                        "Z Report generated successfully, but printing failed."
                    ),
                    "pdf_path": request.build_absolute_uri(pdf_path),
                    "print_error": print_result,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "detail": _("Z Report generated and printed successfully."),
                "pdf_path": request.build_absolute_uri(pdf_path),
                "new_business_day_id": str(new_business_day.id),
            }
        )


# class SalesReportView(generics.GenericAPIView):
#     """
#     Generate Sales Report, save as PDF, print the report, and return file path.
#     """

#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get_business_day(day):
#         try:
#             return BusinessDay.objects.get(date=day)
#         except BusinessDay.DoesNotExist:
#             return None  # Or handle it differently

#     def get(self, request, *args, **kwargs):

#         day = request.query_params.get("day")
#         if not day:
#             return Response(
#                 {"detail": _("Please provide a day in query params.")},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         try:
#             parsed_day = parse_date(day)
#             if not parsed_day:
#                 raise ValueError
#         except ValueError:
#             return Response(
#                 {"detail": _("Invalid date format. Use YYYY-MM-DD.")},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # Find business day within the given date range
#         business_day = self.get_business_day(day)
#         if not business_day:
#             return Response(
#                 {"detail": _("No business day found for this date.")},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         business_day = (
#             BusinessDay.objects.filter(
#                 Q(start_time__date__lte=parsed_day)
#                 & (Q(end_time__date__gte=parsed_day) | Q(end_time__isnull=True))
#             )
#             .order_by("-start_time")
#             .first()
#         )

#         # If a business day exists, use its start_time date; otherwise, use the raw parsed date
#         report_date = business_day if business_day else parsed_day

#         # Generate sales report data
#         report_data = generate_sales_report(report_date)

#         if "error" in report_data:
#             return Response(report_data, status=400)

#         # Save report as PDF
#         reports_dir = os.path.join(settings.MEDIA_ROOT, "uploads/reports")
#         os.makedirs(reports_dir, exist_ok=True)
#         pdf_path = os.path.join(reports_dir, f"sales_report_{parsed_day}.pdf")
#         # Remove existing file
#         if os.path.exists(pdf_path):
#             os.remove(pdf_path)
#         save_sales_report_as_pdf(report_data, pdf_path)

#         # Print the sales report
#         print_result = print_sales_report(report_data)

#         if isinstance(print_result, str) and print_result.startswith("Printing failed"):
#             return Response(
#                 {
#                     "detail": _("Sales Report generated and printed successfully."),
#                     "pdf_path": request.build_absolute_uri(
#                         settings.MEDIA_URL
#                         + f"uploads/reports/sales_report_{parsed_day}.pdf"
#                     ),
#                     "business_day": (
#                         {
#                             "id": str(business_day.id) if business_day else None,
#                             "start_time": (
#                                 business_day.start_time.isoformat()
#                                 if business_day
#                                 else None
#                             ),
#                             "end_time": (
#                                 business_day.end_time.isoformat()
#                                 if business_day and business_day.end_time
#                                 else None
#                             ),
#                             "is_closed": (
#                                 business_day.is_closed if business_day else None
#                             ),
#                         }
#                         if business_day
#                         else None
#                     ),
#                 }
#             )

#         return Response(
#             {
#                 "detail": _("Sales Report generated and printed successfully."),
#                 "pdf_path": request.build_absolute_uri(
#                     settings.MEDIA_URL
#                     + f"uploads/reports/sales_report_{parsed_day}.pdf"
#                 ),
#             }
#         )


class SalesReportView(generics.GenericAPIView):
    """
    Generate Sales Report, save as PDF, print the report, and return file path.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_business_day(self, day):
        """
        Fetches the latest business day that includes the given date.
        """
        return (
            BusinessDay.objects.filter(
                Q(
                    start_time__date__lte=day
                )  # Business day started before or on the given day
                & (
                    Q(end_time__date__gte=day) | Q(end_time__isnull=True)
                )  # Business day still open or ended after the given day
            )
            .order_by("-start_time")  # Get the most recent matching business day
            .first()
        )

    def get(self, request, *args, **kwargs):
        day = request.query_params.get("day")
        if not day:
            return Response(
                {"detail": _("Please provide a day in query params.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parsed_day = parse_date(day)
            if not parsed_day:
                raise ValueError
        except ValueError:
            return Response(
                {"detail": _("Invalid date format. Use YYYY-MM-DD.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find business day within the given date range
        business_day = self.get_business_day(parsed_day)
        if not business_day:
            return Response(
                {"detail": _("No business day found for this date.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate sales report data
        report_data = generate_sales_report(business_day.start_time.date())

        if "error" in report_data:
            return Response(report_data, status=400)

        # Save report as PDF
        reports_dir = os.path.join(settings.MEDIA_ROOT, "uploads/reports")
        os.makedirs(reports_dir, exist_ok=True)
        pdf_path = os.path.join(reports_dir, f"sales_report_{parsed_day}.pdf")

        # Remove existing file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        save_sales_report_as_pdf(report_data, pdf_path)

        # Print the sales report
        print_result = print_sales_report(report_data)

        response_data = {
            "detail": _("Sales Report generated and printed successfully."),
            "pdf_path": request.build_absolute_uri(
                settings.MEDIA_URL + f"uploads/reports/sales_report_{parsed_day}.pdf"
            ),
            "business_day": {
                "id": str(business_day.id),
                "start_time": business_day.start_time.isoformat(),
                "end_time": (
                    business_day.end_time.isoformat() if business_day.end_time else None
                ),
                "is_closed": business_day.is_closed,
            },
        }

        return Response(response_data)


class BusinessDayCreateView(generics.CreateAPIView):
    serializer_class = BusinessDaySerializer
    authentication_classes = {JWTAuthentication}
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.add_businessday"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        created_object_id = serializer.instance.id

        return Response(
            {"id": created_object_id, "detail": _("Business day created successfully")},
            status=status.HTTP_201_CREATED,
        )
