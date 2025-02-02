from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
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
)
from apps.order.filters import OrderFilter, PaymentFilter
from apps.printer.models import Printer

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import HasPermissionOrInGroupWithPermission
from cafe.util import (
    print_to_printer,
    format_bill,
)

from decimal import Decimal

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
                order_item.quantity_to_print += quantity  # Add to quantity_to_print
                order_item.is_printed = False
                order_item.save()
                new_items_total += order_item.sub_total
            else:
                # Create a new order item with quantity and remaining_quantity
                order_item = OrderItems.objects.create(
                    order=order,
                    product=product,
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


class OrderPrintNewItems(generics.GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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
        for item in new_items:
            print(
                f"Product: {item.product.name}, Category Type: {type(item.product.category)}"
            )
            print(f"Category Data: {item.product.category}")

        if not new_items.exists():
            return Response(
                {"detail": _("No new items to print.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch the printers
        barista_printer = Printer.objects.filter(printer_type="barista").first()
        shisha_printer = Printer.objects.filter(printer_type="shisha").first()
        kitchen_printer = Printer.objects.filter(printer_type="kitchen").first()
        # Group items by category
        barista_items = [
            item
            for item in new_items
            if item.product.category.all()
            and any(c.name.lower() == "drinks" for c in item.product.category.all())
        ]
        shisha_items = [
            item
            for item in new_items
            if item.product.category.all()
            and any(c.name.lower() == "shisha" for c in item.product.category.all())
        ]
        kitchen_items = [
            item
            for item in new_items
            if item.product.category.all()
            and any(c.name.lower() == "food" for c in item.product.category.all())
        ]

        # Initialize barista_text and shisha_text to avoid UnboundLocalError
        barista_text = []
        shisha_text = []
        kitchen_text = []
        # Print for barista
        if barista_printer and barista_items:
            barista_text.append("New Drinks Order:")
            barista_text.append(f"Order No: {order.id}")
            barista_text.append("")
            for item in barista_items:
                barista_text.append(
                    f"{item.product.name} - {item.quantity_to_print} Nos"
                )
            print_to_printer(barista_printer.ip_address, "\n".join(barista_text))

        # Print for shisha
        if shisha_printer and shisha_items:
            shisha_text.append("New Shisha Order:")
            shisha_text.append(f"Order No: {order.id}")
            shisha_text.append("")
            for item in shisha_items:
                shisha_text.append(
                    f"{item.product.name} - {item.quantity_to_print} Nos"
                )
            print_to_printer(shisha_printer.ip_address, "\n".join(shisha_text))
        # print for food
        if kitchen_printer and kitchen_items:
            kitchen_text.append("New Food Order:")
            kitchen_text.append(f"Order No: {order.id}")
            kitchen_text.append("")
            for item in kitchen_items:
                kitchen_text.append(
                    f"{item.product.name} - {item.quantity_to_print} Nos"
                )
                print_to_printer(kitchen_printer.ip_address, "\n".join(kitchen_text))
        # Mark items as printed and increment quantity_to_print by the difference
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
                "shisha_text": (
                    shisha_text if shisha_text else _("No shisha to print.")
                ),
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
        removed_items = []  # Store removed product names

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

            order_item = OrderItems.objects.filter(order=order, product=product).first()
            if order_item:
                if quantity_to_remove >= order_item.quantity:
                    removed_items.append(
                        order_item.product.name
                    )  # Store product name before deleting
                    removed_items_total += order_item.sub_total
                    order_item.delete()
                else:
                    removed_items.append(order_item.product.name)  # Store product name
                    removed_items_total += (
                        order_item.sub_total / order_item.quantity
                    ) * quantity_to_remove
                    order_item.quantity -= quantity_to_remove
                    order_item.remaining_quantity = max(
                        0, order_item.remaining_quantity - quantity_to_remove
                    )
                    order_item.quantity_to_print = max(
                        0, order_item.quantity_to_print - quantity_to_remove
                    )
                    order_item.save()
            else:
                return Response(
                    {"detail": _("Product not found in the order.")},
                    status=status.HTTP_404_NOT_FOUND,
                )

        order.final_total -= removed_items_total
        order.final_total = max(0, order.final_total)  # Ensure no negative totals
        order.vat = order.final_total - (order.final_total / Decimal("1.05"))
        discount_value = order.discount.value if order.discount else Decimal("0.00")
        order.grand_total = max(Decimal("0.00"), order.final_total - discount_value)
        order.save()

        return Response(
            {
                "detail": _("Items removed from order successfully."),
                "removed_items": removed_items,  # Now this should contain product names
            },
            status=status.HTTP_200_OK,
        )


# class ApplyDiscountToOrderView(generics.UpdateAPIView):
#     serializer_class = OrderSerializer
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
#     permission_codename = "discount.add_discount"
#     lookup_field = "id"

#     def get_object(self):
#         order_id = self.request.query_params.get("order_id")
#         order = get_object_or_404(Order, id=order_id)
#         return order

#     def update(self, request, *args, **kwargs):
#         order = self.get_object()
#         discount_id = request.data.get(
#             "discount_id"
#         )  # Get discount ID from request data

#         # Check if the order is already paid
#         if order.is_paid:
#             return Response(
#                 {"detail": _("Cannot apply discount to a paid order")},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         # Retrieve discount instance
#         try:
#             discount = Discount.objects.get(id=discount_id)
#         except Discount.DoesNotExist:
#             return Response(
#                 {"detail": _("Discount not found")}, status=status.HTTP_404_NOT_FOUND
#             )
#         if discount:
#             return Response(
#                 {"detail": _("Discount already applied to this order")},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         # Apply discount to the order
#         order.discount = discount
#         discount_value = discount.value if discount else Decimal("0.00")
#         order.grand_total -= discount_value
#         # Ensure total is not negative
#         if order.grand_total < Decimal("0.00"):
#             order.grand_total = Decimal("0.00")
#         # Save updated order
#         order.save()

#         return Response(
#             {"detail": _("Discount applied successfully")}, status=status.HTTP_200_OK
#         )



class ApplyDiscountToOrderView(generics.UpdateAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "discount.add_discount"
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
                {"detail": _("Cannot split an order because it's already fully paid.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get items and payment method from request
        items = request.data.get("items")
        payment_method = request.data.get("payment_method")

        if not items:
            return Response(
                {"detail": _("Items are required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            total_payment_amount = Decimal("0.00")
            with transaction.atomic():
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
                    order_item = OrderItems.objects.get(
                        product__id=product_id, order=order
                    )

                    # Validate quantity
                    if quantity_to_pay > order_item.remaining_quantity:
                        return Response(
                            {
                                "detail": _(
                                    "Quantity exceeds remaining unpaid quantity."
                                )
                            },
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

                # Calculate VAT (assuming 5%)
                vat = total_payment_amount - (total_payment_amount / Decimal("1.05"))

                # ✅ Create a payment record
                payment = Payment.objects.create(
                    amount=total_payment_amount,
                    payment_method=payment_method,
                    created_by=request.user,
                )

                # ✅ Associate the payment with the order using the M2M relationship
                payment.orders.add(order)

                # ✅ Recalculate order totals
                self.recalculate_order(order)

                # ✅ Generate the formatted bill and save as PDF
                formatted_bill, logo_path, pdf_path = format_bill(
                    order, payment.id, total_payment_amount, vat, save_as_pdf=True
                )

                # ✅ Print the bill
                cashier_printer = Printer.objects.filter(printer_type="cashier").first()
                if cashier_printer:
                    try:
                        print_to_printer(
                            cashier_printer.ip_address, formatted_bill, logo_path
                        )
                    except Exception as e:
                        print(f"⚠️ Printing failed for order {order.id}: {e}")

            return Response(
                {
                    "detail": _("Bill split successfully."),
                    "formatted_bill": formatted_bill,
                    "pdf_path": request.build_absolute_uri(pdf_path),  # ✅ Include PDF path for record-keeping
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
        """Recalculates order totals after splitting a bill."""
        order_items = OrderItems.objects.filter(order=order)

        final_total = sum(
            (
                Decimal(item.remaining_quantity) * item.product.price
                for item in order_items
            )
        )

        # ✅ Calculate VAT (assuming 5%)
        vat = final_total - (final_total / Decimal("1.05"))

        # ✅ Apply discount if applicable
        discount_value = order.discount.value if order.discount else Decimal("0.00")

        # ✅ Update order totals
        order.final_total = final_total
        order.vat = vat.quantize(Decimal("0.01"))  # Round to 2 decimal places
        order.grand_total = max(
            order.final_total - discount_value, Decimal("0.00")
        )  # Ensure non-negative

        # ✅ Mark order as fully paid if all items are paid
        if all(item.is_paid for item in order_items):
            order.is_paid = True
            order.check_out_time = now()  # Store checkout time

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

        grand_total = order.grand_total
        if not grand_total:
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

        # ✅ Save payment and update order status
        with transaction.atomic():
            payment = Payment.objects.create(
                amount=grand_total,
                payment_method=payment_method,
                created_by=request.user,
            )
            payment.orders.add(order)

            # ✅ Mark all order items as paid and set remaining_quantity to zero
            order_items = OrderItems.objects.filter(order=order)
            for item in order_items:
                item.is_paid = True
                item.remaining_quantity = 0
                item.save()

            order.is_paid = True
            order.check_out_time = now()  # Set checkout time to current timestamp
            order.save()

        total_payment_amount = order.grand_total
        vat = order.vat

        # ✅ Generate the bill and save as PDF
        formatted_bill, logo_path, pdf_path = format_bill(
            order, payment.id, total_payment_amount, vat, save_as_pdf=True
        )

        # ✅ Get cashier printer
        cashier_printer = Printer.objects.filter(printer_type="cashier").first()
        if cashier_printer:
            try:
                print_to_printer(cashier_printer.ip_address, formatted_bill, logo_path)
            except Exception as e:
                print(f" Failed to print order {order.id}: {e}")

        # ✅ Prepare API response
        response_data = {
            "detail": _("Order checked out and payment recorded successfully."),
            "bill": formatted_bill,
            "pdf_path": request.build_absolute_uri(pdf_path),  # ✅ Include PDF path in response
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
                order.grand_total for order in orders if order.grand_total
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
                pdf_paths = []

                # ✅ Get cashier printer
                cashier_printer = Printer.objects.filter(printer_type="cashier").first()
                if not cashier_printer:
                    return Response(
                        {"error": _("No cashier printer found.")}, status=400
                    )

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

                    # ✅ Generate the bill and save as PDF
                    formatted_bill, logo_path, pdf_path = format_bill(
                        order, payment.id, total_payment_amount, vat, save_as_pdf=True
                    )
                    formatted_bills.append(formatted_bill)
                    pdf_paths.append(pdf_path)

                    # ✅ Print each bill (wrapped in a try-except block)
                    try:
                        print_to_printer(
                            cashier_printer.ip_address, formatted_bill, logo_path
                        )
                    except Exception as e:
                        print(f"Failed to print order {order.id}: {e}")

                combined_bill = "\n\n".join(formatted_bills)

            return Response(
                {
                    "detail": _("Group bills processed successfully."),
                    "combined_bill": combined_bill,
                    "pdf_paths": request.build_absolute_uri(pdf_path),  # ✅ Return list of generated PDFs
                    "logo": logo_path if logo_path else None,
                },
                status=200,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


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


class PaymentMethodDialogView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        payment_method_choices = [
            {"value": "cash", "display": _("Cash")},
            {"value": "card", "display": _("Visa Card")},
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
