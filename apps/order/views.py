from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes


from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.order.models import Order, OrderItems, Payment
from apps.product.models import Product
from apps.order.serializers import (
    OrderSerializer,
    OrderItemsSerializer,
    PaymentSerializer,
)
from apps.printer.models import Printer

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import HasPermissionOrInGroupWithPermission
from cafe.util import (
    print_to_printer,
    format_bill,
    format_barista_order,
    format_shisha_order,
)

import os
import requests
from decimal import Decimal
import json
from django.http import JsonResponse

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.utils.timezone import now


# Order Views
class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.add_order"

    def perform_create(self, serializer):
        user = self.request.user
        order = serializer.save(created_by=user)
        self.print_order(order)

    def print_order(self, order):
        # Fetch the printers
        cashier_printer = Printer.objects.filter(printer_type="cashier").first()
        barista_printer = Printer.objects.filter(printer_type="barista").first()
        shisha_printer = Printer.objects.filter(printer_type="shisha").first()

        # # Format the bill and get the logo path
        # bill_text, logo_path = format_bill(order)

        # # Print total for cashier
        # if cashier_printer:
        #     print_to_printer(cashier_printer.ip_address, bill_text, logo_path)

        # Print items for barista
        if barista_printer:
            barista_text = format_barista_order(order)
            if barista_text:
                print_to_printer(barista_printer.ip_address, barista_text)

        # Print items for shisha maker
        if shisha_printer:
            shisha_text = format_shisha_order(order)
            if shisha_text:
                print_to_printer(shisha_printer.ip_address, shisha_text)

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

        items = request.data
        new_items = []  # To store newly added items for printing

        # Calculate the total for new items
        new_items_total = Decimal("0.00")

        for item_data in items:
            product_id = item_data.get("product")
            quantity = int(item_data.get("quantity", 1))  # Default quantity to 1

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
                order_item.remaining_quantity += quantity  # Add to remaining_quantity
                order_item.save()
                new_items_total += order_item.sub_total
            else:
                # Create a new order item with quantity and remaining_quantity
                order_item = OrderItems.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    remaining_quantity=quantity,  # Initialize remaining_quantity
                )
                new_items.append(order_item)
                new_items_total += order_item.sub_total

        # Recalculate final_total and vat for the order
        order.final_total += new_items_total
        order.vat = order.final_total - (
            order.final_total / Decimal("1.05")
        )  # Assuming 5% VAT
        order.save()

        # Send print jobs for new items
        self.print_new_items(order, new_items)

        return Response(
            {"detail": _("Items added to order successfully")},
            status=status.HTTP_201_CREATED,
        )

    def print_new_items(self, order, new_items):
        # Fetch the printers
        barista_printer = Printer.objects.filter(printer_type="barista").first()
        shisha_printer = Printer.objects.filter(printer_type="shisha").first()

        # Group new items by category
        barista_items = [
            item for item in new_items if item.product.category.name == "Drinks"
        ]
        shisha_items = [
            item for item in new_items if item.product.category.name == "Shisha"
        ]

        # Print new items for barista
        if barista_printer and barista_items:
            barista_text = ["New Drinks Order:"]
            barista_text.append(f"Order No: {order.id}")
            barista_text.append("")
            for item in barista_items:
                barista_text.append(f"{item.product.name} - {item.quantity} Nos")
            print_to_printer(barista_printer.ip_address, "\n".join(barista_text))

        # Print new items for shisha maker
        if shisha_printer and shisha_items:
            shisha_text = ["New Shisha Order:"]
            shisha_text.append(f"Order No: {order.id}")
            shisha_text.append("")
            for item in shisha_items:
                shisha_text.append(f"{item.product.name} - {item.quantity} Nos")
            print_to_printer(shisha_printer.ip_address, "\n".join(shisha_text))


class OrderRemoveItems(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = OrderItemsSerializer

    def destroy(self, request, *args, **kwargs):
        # Get the order_id from the URL parameters
        order_id = request.query_params.get("order_id")
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": _("Order does not exist.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        items = request.data
        removed_items = []  # To store removed items for potential use

        # Calculate the total to subtract for removed items
        removed_items_total = Decimal("0.00")

        for item_data in items:
            product_id = item_data.get("product")
            quantity_to_remove = int(item_data.get("quantity", 1))  # Default to 1

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"detail": _("Product not found")},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Find the order item
            order_item = OrderItems.objects.filter(order=order, product=product).first()
            if order_item:
                if quantity_to_remove >= order_item.quantity:
                    # Remove the item completely
                    removed_items_total += order_item.sub_total
                    removed_items.append(order_item)
                    order_item.delete()
                else:
                    # Reduce the quantity and update the remaining total
                    removed_items_total += (
                        order_item.sub_total / order_item.quantity
                    ) * quantity_to_remove
                    order_item.quantity -= quantity_to_remove
                    order_item.remaining_quantity = max(
                        0, order_item.remaining_quantity - quantity_to_remove
                    )
                    order_item.save()
            else:
                return Response(
                    {"detail": _("Product not found in the order.")},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Recalculate final_total and VAT for the order
        order.final_total -= removed_items_total
        if order.final_total < 0:
            order.final_total = 0  # Ensure no negative totals
        order.vat = order.final_total - (order.final_total / Decimal("1.05"))
        order.save()

        return Response(
            {
                "detail": _("Items removed from order successfully."),
                "removed_items": [item.product.name for item in removed_items],
            },
            status=status.HTTP_200_OK,
        )


class SplitBillView(generics.CreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Get the order_id from the URL parameters
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
                {
                    "detail": _(
                        "Can not split an order because it's already paid totally"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Get items from the request body
        items = request.data.get("items")
        payment_method = request.data.get("payment_method")
        if not items:
            return Response(
                {"detail": _("Items are required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            total_payment_amount = Decimal("0.00")
            for item_data in items:
                product_id = item_data.get("product")
                quantity_to_pay = item_data.get("quantity")

                # Ensure product ID and quantity are provided
                if not product_id or quantity_to_pay is None:
                    return Response(
                        {"detail": _("Product ID and quantity are required.")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Get the order item for the specified product and order
                order_item = OrderItems.objects.get(product__id=product_id, order=order)

                # Validate quantity
                if quantity_to_pay > order_item.remaining_quantity:
                    return Response(
                        {"detail": _("Quantity exceeds remaining unpaid quantity.")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Calculate the amount for this item
                item_total = Decimal(quantity_to_pay) * order_item.product.price
                total_payment_amount += item_total

                # Decrease the remaining quantity
                order_item.remaining_quantity -= quantity_to_pay

                # Check if the item is fully paid
                if order_item.remaining_quantity == 0:
                    order_item.is_paid = True

                # Recalculate the sub_total based on the updated remaining_quantity
                order_item.sub_total = (
                    order_item.remaining_quantity * order_item.product.price
                )

                # Save the updated order item
                order_item.save()

            # Calculate VAT based on the total
            vat = total_payment_amount - (total_payment_amount / Decimal("1.05"))

            # Create a payment record
            payment = Payment.objects.create(
                amount=total_payment_amount,
                payment_method=payment_method,
                created_by=request.user,
            )

            # Associate the payment with the order using the M2M relationship
            payment.orders.add(order)

            # Recalculate the order's total and VAT
            self.recalculate_order(order)

            # Generate the formatted bill
            formatted_bill, logo_path = format_bill(
                order, payment, total_payment_amount, vat
            )

            return Response(
                {
                    "detail": _("Bill split successfully."),
                    "formatted_bill": formatted_bill,
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

    def recalculate_order(self, order):
        # Recalculate the final_total
        order_items = OrderItems.objects.filter(order=order)
        final_total = sum(
            (
                Decimal(item.remaining_quantity) * item.product.price
                for item in order_items
            )
        )

        # Calculate VAT as per the given formula
        vat = final_total - (final_total / Decimal("1.05"))  # Assuming VAT is 5%

        # Update the order with the new values
        order.final_total = final_total
        order.vat = vat.quantize(Decimal("0.01"))  # Round to 2 decimal places

        # Check if all items are paid
        if all(item.is_paid for item in order_items):
            order.is_paid = True
            order.check_out_time = now()  # Set checkout time to current timestamp

        order.save()


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

        final_total = order.final_total
        if not final_total:
            return Response(
                {"detail": _("Final total is missing for the order.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method = request.data.get("payment_method")
        if not payment_method:
            return Response(
                {"detail": _("Payment method is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save payment and update order status
        with transaction.atomic():
            payment = Payment.objects.create(
                amount=final_total,
                payment_method=payment_method,
                created_by=request.user,
            )
            payment.orders.add(order)
            # Mark all order items as paid and set remaining_quantity to zero
            order_items = OrderItems.objects.filter(order=order)
            for item in order_items:
                item.is_paid = True
                item.remaining_quantity = 0
                item.save()
            order.is_paid = True
            order.check_out_time = now()  # Set checkout time to current timestamp

            order.save()
        total_payment_amount = order.final_total
        vat = order.vat
        # Generate the bill with Payment ID as Invoice No
        formatted_bill, logo_path = format_bill(
            order, payment.id, total_payment_amount, vat
        )

        response_data = {
            "detail": _("Order checked out and payment recorded successfully."),
            "bill": formatted_bill,
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
            # Fetch unpaid orders
            orders = Order.objects.filter(id__in=order_ids, is_paid=False)
            if not orders.exists():
                return Response({"error": _("No unpaid orders found.")}, status=400)

            # Calculate total payment
            total_payment_amount = sum(
                order.final_total for order in orders if order.final_total
            )
            if total_payment_amount == 0:
                return Response(
                    {"error": _("Orders have missing or zero final totals.")},
                    status=400,
                )

            # Calculate VAT
            vat = sum(order.vat for order in orders if order.vat)

            # Validate payment method
            payment_method = request.data.get("payment_method")
            if not payment_method:
                return Response({"error": _("Payment method is required.")}, status=400)

            with transaction.atomic():
                # Create a single payment record for all orders
                payment = Payment.objects.create(
                    amount=total_payment_amount,
                    payment_method=payment_method,
                    created_by=request.user,
                )

                # ✅ Link all orders to this payment
                payment.orders.set(orders)

                formatted_bills = []
                for order in orders:
                    # Fetch and update all associated OrderItems
                    order_items = OrderItems.objects.filter(order=order)
                    for item in order_items:
                        item.is_paid = True
                        item.remaining_quantity = 0
                        item.save()
                    order.is_paid = True
                    order.check_out_time = now()  # Store checkout time
                    order.save()

                    # Generate the bill
                    formatted_bill, logo_path = format_bill(
                        order, payment, total_payment_amount, vat
                    )
                    formatted_bills.append(formatted_bill)

                combined_bill = "\n\n".join(formatted_bills)

            return Response(
                {
                    "detail": _("Group bills processed successfully."),
                    "combined_bill": combined_bill,
                    "logo": logo_path if logo_path else None,
                },
                status=200,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class OrderUnpaidListView(generics.ListAPIView):
    queryset = Order.objects.filter(is_paid=False).order_by("-created_at")
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.view_order"
    pagination_class = StandardResultsSetPagination


class OrderPaidListView(generics.ListAPIView):
    queryset = Order.objects.filter(is_paid=True).order_by("-created_at")
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "order.view_order"
    pagination_class = StandardResultsSetPagination


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
