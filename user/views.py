from django.http import Http404, HttpResponse  # added by me
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import (
    generics,
    status,
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import JSONParser

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

import uuid
import csv
import logging
import json

import string
import random

from user.models import (
    User,
)
from user.serializers import (
    UserSerializer,
    UserImageSerializer,
    UserCoverSerializer,
    UserDeleteSerializer,
    UserDialogSerializer,
    UserGenderChoiceSerializer,
)

from user.filters import UserFilter

from cafe.pagination import StandardResultsSetPagination

from cafe.custom_permissions import HasPermissionOrInGroupWithPermission


# User login view
class LoginView(APIView):
    # Primary login view
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        identifier = request.data.get("identifier")  # Field for email or phone number
        password = request.data.get("password")

        # Filter using Q objects to match either email or phone_number
        user = User.objects.filter(
            Q(email=identifier) | Q(mobile_number=identifier)
        ).first()

        if user is None:
            raise AuthenticationFailed(
                _("Email or phone number or password is invalid")
            )
        if user.is_staff == False:
            raise AuthenticationFailed(
                _("Email or phone number or password is invalid!!!")
            )
        if not user.is_active:
            raise AuthenticationFailed(_("User account is inactive"))
        if user.is_deleted == True:
            raise AuthenticationFailed(_("This user is deleted"))
        if not user.check_password(password):
            raise AuthenticationFailed(
                _("Email or phone number or password is invalid")
            )

        refresh = RefreshToken.for_user(user)
        response = Response()
        # Extract group names and convert them to a list of strings
        group_names = list(user.groups.values_list("name", flat=True))
        user_permissions_names = list(
            user.user_permissions.values_list("codename", flat=True)
        )

        response.data = {
            "identifier": (
                user.email if user.email == identifier else user.mobile_number
            ),
            "groups": group_names,
            "user_permissions": user_permissions_names,
            "name": user.name,
            "is_staff": user.is_staff,
            "access_token": str(refresh.access_token),
            # "refresh_token": str(refresh),
        }
        return response


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.add_user'

    def perform_create(self, serializer):
        # Capitalize the user's name before saving
        name = serializer.validated_data.get("name", "")
        capitalized_name = name.lower()
        serializer.save(name=capitalized_name)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("User created successfully")}, status=status.HTTP_201_CREATED
        )


class UserListView(generics.ListAPIView):
    queryset = User.objects.filter(
        is_deleted=False, is_superuser=False, is_staff=True
    ).order_by("-created_at")
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.view_user'

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ["name", "name_ar", "mobile_number", "email", "identification"]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


class DeletedUserView(generics.ListAPIView):
    queryset = User.objects.filter(is_deleted=True).order_by("-created_at")
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.view_user'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ["name", "name_ar", "mobile_number", "email", "identification"]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


class UserRetrieveView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.view_user'
    lookup_field = "id"

    def get_queryset(self):
        return User.objects.filter(is_deleted=False)

    def get_object(self):
        user_id = self.request.query_params.get("user_id")
        user = get_object_or_404(self.get_queryset(), id=user_id)
        return user


class UploadUserPhotoView(generics.UpdateAPIView):
    serializer_class = UserImageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.change_user'

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.action = self.request.method.lower()

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        user = self.request.user
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self):
        if self.action == "upload_image":
            return UserImageSerializer
        return self.serializer_class

    def update(self, request, *args, **kwargs):
        user = self.request.user  # Get the user from the JWT token
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            user.resize_and_save_avatar()
            return Response(
                {"detail": _("Your photo changed successfully")},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadUserCoverView(generics.UpdateAPIView):
    serializer_class = UserCoverSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.change_user'

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.action = self.request.method.lower()

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        user = self.request.user
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self):
        if self.action == "upload_image":
            return UserImageSerializer
        return self.serializer_class

    def update(self, request, *args, **kwargs):
        user = self.request.user  # Get the user from the JWT token
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": _("Your cover photo changed successfully")},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManagerUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.change_user'

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Your data Updated successfully")}, status=status.HTTP_200_OK
        )


class UserDeleteTemporaryView(generics.UpdateAPIView):
    serializer_class = UserDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.change_user'

    def update(self, request, *args, **kwargs):
        user_ids = request.data.get("user_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == False:
            return Response(
                {"detail": _("These users are not deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for user_id in user_ids:
            instance = get_object_or_404(User, id=user_id)
            if instance.is_deleted:
                return Response(
                    {
                        "detail": _(
                            "User with ID {} is already temp deleted".format(user_id)
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        return Response(
            {"detail": _("Users temp deleted successfully")}, status=status.HTTP_200_OK
        )


class UserRestoreView(generics.RetrieveUpdateAPIView):

    serializer_class = UserDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.change_user'

    def update(self, request, *args, **kwargs):
        user_ids = request.data.get("user_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == True:
            return Response(
                {"detail": _("users are already deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for user_id in user_ids:
            instance = get_object_or_404(User, id=user_id)
            if instance.is_deleted == False:
                return Response(
                    {"detail": _("User with ID {} is not deleted".format(user_id))},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        return Response(
            {"detail": _("Users restored successfully")}, status=status.HTTP_200_OK
        )


class UserUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.change_user'
    lookup_field = "id"

    def get_object(self):
        user_id = self.request.query_params.get("user_id")
        user = get_object_or_404(User, id=user_id)
        return user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("User Updated successfully")}, status=status.HTTP_200_OK
        )


class UserDeleteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='user.delete_user'

    def delete(self, request, format=None):
        data = JSONParser().parse(request)
        user_id_list = data.get("user_id", [])

        if not user_id_list:
            return Response(
                {"detail": _("No user IDs provided for deletion")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if each UUID is valid
        for uid in user_id_list:
            try:
                uuid.UUID(uid.strip())
            except ValueError:
                raise ValidationError(_("'{}' is not a valid UUID.".format(uid)))

        users = User.objects.filter(id__in=user_id_list)
        if not users.exists():
            return Response(
                {"detail": _("No users found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        users.delete()

        return Response(
            {"detail": _("Users permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


# User Dialogs
class UserDialogView(generics.ListAPIView):
    serializer_class = UserDialogSerializer
    queryset = User.objects.filter(is_deleted=False, is_superuser=False)
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class UserGenderDialogView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Define the gender choices here
        gender_choices = [
            {"value": "male", "display": _("Male")},
            {"value": "female", "display": _("Female")},
        ]

        serializer = UserGenderChoiceSerializer(gender_choices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



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
            customer = get_object_or_404(User, email=email)

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

