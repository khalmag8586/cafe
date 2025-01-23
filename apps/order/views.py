from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes


from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.order.models import Order, OrderItems
from apps.order.serializers import (
    OrderSerializer,
    OrderItemsSerializer,
    OrderDialogSerializer,
)

from apps.cart.models import Cart, CartItems
from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import OnlyCustomer, CustomerPermission

from paypalrestsdk import Payment

import os
import requests
import json
import paypalrestsdk
from django.http import JsonResponse

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


def order_pdf_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    order_id = instance.id
    filename = f"{order_id}{ext}"

    return os.path.join("uploads", "order_pdf_downloads", filename)


paypalrestsdk.configure(
    {
        "mode": "sandbox",  # يمكن تعيين القيمة إلى 'live' في الإنتاج
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)


@method_decorator(csrf_exempt, name="dispatch")
class CreatePaymentView(APIView):
    permission_classes = [OnlyCustomer]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": _("User is not authenticated.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        customer = request.user.customer

        # Fetch the grand_total from the cart
        try:
            cart = Cart.objects.get(customer=customer)
            amount = (
                cart.grand_total
            )  # Assuming you have a grand_total field in your Cart model
        except Cart.DoesNotExist:
            return JsonResponse(
                {"detail": _("Cart not found for the customer.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create PayPal payment
        payment = paypalrestsdk.Payment(
            {
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal",
                },
                "redirect_urls": {
                    "return_url": "https://music-score-pi.vercel.app/execute-payment/",
                    "cancel_url": "https://music-score-pi.vercel.app/cancel-payment/",
                },
                "transactions": [
                    {
                        "amount": {
                            "total": str(
                                amount
                            ),  # Convert amount to string as required by PayPal SDK
                            "currency": "USD",
                        },
                        "description": "Payment for an item",
                        "soft_descriptor": "Score",  # Set your custom soft descriptor here
                    }
                ],
            }
        )

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    return JsonResponse({"approval_url": approval_url})
        else:
            return JsonResponse(
                {"error": payment.error}, status=status.HTTP_400_BAD_REQUEST
            )


# @csrf_exempt
# def execute_payment(request):

#     try:
#         data = json.loads(request.body)
#         payment_id = data.get("paymentId")
#         payer_id = data.get("PayerID")
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON data"}, status=400)
#     payment = paypalrestsdk.Payment.find(payment_id)

#     if payment.execute({"payer_id": payer_id}):
#         return JsonResponse(
#             {
#                 "status": "Payment executed successfully",
#                 "payment": payment.to_dict(),  # Serialize the payment object
#             }
#         )
#     else:
#         return JsonResponse({"error": payment.error})


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def execute_payment(request):
    try:
        data = json.loads(request.body)
        payment_id = data.get("paymentId")
        payer_id = data.get("PayerID")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)

    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        customer = request.user.customer

        # Create the order
        order = Order.objects.create(
            created_by=customer,
            paypal_payment_id=payment_id,
            payment_status="Complete",
            payment_method="PayPal",
        )

        # Add items from cart to order
        try:
            cart = Cart.objects.get(customer=customer)
        except Cart.DoesNotExist:
            return JsonResponse(
                {"error": "Cart not found for the customer."}, status=404
            )

        total = 0
        for cart_item in cart.items.all():
            order_item = OrderItems.objects.create(
                order=order,
                cart=cart,
                quantity=cart_item.quantity,
                sub_total=cart_item.sub_total,
                product=cart_item.product,
                purchase_type=cart_item.purchase_type,
            )
            total += order_item.sub_total * order_item.quantity
        cart.items.all().delete()  # Clear the cart

        order.final_total = total
        order.save()

        # Return the full payment object
        return JsonResponse(
            {
                "status": "Payment executed successfully",
                "payment": payment.to_dict(),  # Serialize the payment object
                "order_id": order.id,
            }
        )
    else:
        return JsonResponse({"error": payment.error}, status=400)


# Order Views
class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def perform_create(self, serializer):
        customer = self.request.user.customer

        order = serializer.save(created_by=customer)

        # Add items from cart to order
        cart = Cart.objects.get(customer=customer)
        total = 0
        for cart_item in cart.items.all():
            order_item = OrderItems.objects.create(
                order=order,
                cart=cart,
                quantity=cart_item.quantity,
                sub_total=cart_item.sub_total,
            )
            total += order_item.sub_total * order_item.quantity
        cart.items.all().delete()  # Clear the cart

        order.final_total = total
        order.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("Order created successfully")}, status=status.HTTP_201_CREATED
        )


class OrderListView(generics.ListAPIView):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    pagination_class = StandardResultsSetPagination


class CustomerOrdersListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def get_queryset(self):
        customer = self.request.user.customer
        return Order.objects.filter(created_by=customer).order_by("-created_at")


class OrderRetrieve(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]
    lookup_field = "id"

    def get_object(self):
        order_id = self.request.query_params.get("order_id")
        order = get_object_or_404(Order, id=order_id)
        return order


class OrderDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def delete(self, request, *args, **kwargs):
        order_ids = request.data.get("order_id", [])
        for order_id in order_ids:
            instance = get_object_or_404(Order, id=order_id)
            instance.delete()
        return Response(
            {"detail": _("Order permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class OrderDialogListView(generics.ListAPIView):
    serializer_class = OrderDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    queryset = Order.objects.all()
