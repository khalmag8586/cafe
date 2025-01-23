from django.http import Http404, HttpResponse  # added by me
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import (
    generics,
    status,
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.decorators import action, api_view
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import JSONParser

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

import logging
import json

import string
import random

from apps.customer.models import Customer
from apps.customer.serializers import CustomerSerializer, CustomerActivationSerializer

from cafe.pagination import StandardResultsSetPagination

from cafe.custom_permissions import CustomerPermission, OnlyCustomer
from django.views.decorators.csrf import csrf_exempt


class CustomerLoginView(APIView):
    # Primary login view
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        identifier = request.data.get("identifier")  # Field for email or phone number
        password = request.data.get("password")

        # Filter using Q objects to match either email or phone_number
        customer = Customer.objects.filter(
            Q(email=identifier) | Q(mobile_number=identifier)
        ).first()

        if customer is None:
            raise AuthenticationFailed(
                _("Email or phone number or password is invalid")
            )

        if not customer.is_active:
            raise AuthenticationFailed(
                _(
                    "Customer account is inactive, please contact with website management"
                )
            )
        if customer.is_deleted == True:
            raise AuthenticationFailed(_("This user is deleted"))
        if not customer.check_password(password):
            raise AuthenticationFailed(
                _("Email or phone number or password is invalid")
            )

        refresh = RefreshToken.for_user(customer)
        response = Response()

        response.data = {
            "identifier": (
                customer.email
                if customer.email == identifier
                else customer.mobile_number
            ),
            "name": customer.name,
            "is_staff": customer.is_staff,
            "is_customer": customer.is_customer,
            "access_token": str(refresh.access_token),
            # "refresh_token": str(refresh),
        }
        return response


class CreateCustomerView(generics.CreateAPIView):
    serializer_class = CustomerSerializer

    def perform_create(self, serializer):
        # Capitalize the user's name before saving
        name = serializer.validated_data.get("name", "")
        capitalized_name = name.title()
        serializer.save(name=capitalized_name)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("Customer created successfully")},
            status=status.HTTP_201_CREATED,
        )


class CustomerListView(generics.ListAPIView):
    queryset = Customer.objects.filter(is_deleted=False, is_customer=True).order_by(
        "-created_at"
    )
    serializer_class = CustomerSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, CustomerPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "name_ar", "mobile_number", "email"]
    ordering_fields = ["name"]


class CustomerRetrieve(generics.RetrieveAPIView):
    queryset = Customer.objects.filter(is_deleted=False, is_customer=True)
    serializer_class = CustomerSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Customer.objects.filter(
            is_deleted=False, is_customer=True, is_staff=False
        )

    def get_object(self):
        customer_id = self.request.query_params.get("customer_id")
        customer = get_object_or_404(self.get_queryset(), id=customer_id)
        return customer


class ManagerCustomerView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def get_object(self):
        return self.request.user.customer

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Your data Updated successfully")}, status=status.HTTP_200_OK
        )


class CustomerActivationStatusView(generics.UpdateAPIView):
    serializer_class = CustomerActivationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        customer_id = self.request.query_params.get("customer_id")
        customer = get_object_or_404(Customer, id=customer_id)
        return customer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        is_active = request.data.get("is_active")

        if is_active is None:
            return Response(
                {"detail": _("'is_active' field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if is_active and not request.user.is_staff:
            return Response(
                {"detail": _("You are not authorized to reactivate this account.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("The Active Status Updated successfully")},
            status=status.HTTP_200_OK,
        )


logger = logging.getLogger(__name__)


@csrf_exempt
def forgot_password(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Parse the JSON request body
            email = data.get("email")
            if not email:
                return JsonResponse(
                    {"detail": _("Email is required.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            customer = get_object_or_404(Customer, email=email)

            # Generate a new password
            def generate_password(length=8):
                lowercase_chars = string.ascii_lowercase
                uppercase_chars = string.ascii_uppercase
                digit_chars = string.digits

                password = [
                    random.choice(lowercase_chars),
                    random.choice(uppercase_chars),
                    random.choice(digit_chars),
                ]

                for _ in range(length - 3):
                    password.append(
                        random.choice(lowercase_chars + uppercase_chars + digit_chars)
                    )

                random.shuffle(password)

                return "".join(password)

            new_password = generate_password(8)

            # Update user's password
            customer.set_password(new_password)
            customer.save()

            # Send email with new password
            send_mail(
                "Password Reset",
                f"Your new password is: {new_password}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            logger.info(f"Password reset for {email} successful.")
            return JsonResponse(
                {"detail": _("Password reset email sent successfully.")}
            )
        except Exception as e:
            logger.error(f"Error during password reset: {str(e)}")
            return JsonResponse(
                {"detail": _("An error occurred. Please try again later.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        return JsonResponse(
            {"detail": _("Method not allowed.")},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
