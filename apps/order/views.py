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

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import HasPermissionOrInGroupWithPermission

# from paypalrestsdk import Payment

import os
import requests
import json
# import paypalrestsdk
from django.http import JsonResponse

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator





@method_decorator(csrf_exempt, name="dispatch")
class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": _("User is not authenticated.")},
                status=status.HTTP_401_UNAUTHORIZED,
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




# Order Views
class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]

    def perform_create(self, serializer):
        user=self.request.user
        order = serializer.save(created_by=user)



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
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    pagination_class = StandardResultsSetPagination


class CustomerOrdersListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]

    def get_queryset(self):
        customer = self.request.user.customer
        return Order.objects.filter(created_by=customer).order_by("-created_at")


class OrderRetrieve(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    lookup_field = "id"

    def get_object(self):
        order_id = self.request.query_params.get("order_id")
        order = get_object_or_404(Order, id=order_id)
        return order


class OrderDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]

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
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    queryset = Order.objects.all()
