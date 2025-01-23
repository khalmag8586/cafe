from django.db import models

# Create your models here.
from django.db import models, IntegrityError
from django.db.models import Q, UniqueConstraint
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission

import uuid
import os
from PIL import Image
from io import BytesIO


from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


def default_photo_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"default{ext}"
    return os.path.join("default_photos", filename)


def user_photo_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    return os.path.join("uploads", "employee", filename)


class UserManager(BaseUserManager):
    def create_user(
        self, email=None, mobile_number=None, password=None, **extra_fields
    ):
        if not email and not mobile_number:
            raise ValueError(
                _("User must have either an email address or a mobile number")
            )

        user = self.model(
            email=self.normalize_email(email),
            mobile_number=mobile_number,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, mobile_number=None, password=None):
        if not email and not mobile_number:
            raise ValueError(
                _("Superuser must have either an email address or a mobile number")
            )

        user = self.create_user(
            email=email,
            mobile_number="01112890867",
            password=password,
            name="KhalMag",
            name_ar="كالماج",  # Set the desired name for superuser
        )

        user.is_staff = True
        user.is_superuser = True
        user.photo = "default_photos/km2.jpg"

        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):

    GENDER_CHOICES = [("male", _("Male")), ("female", _("Female"))]

    mobile_num_regex = RegexValidator(
        regex="^[0-9]{9,20}$",
        message=_("Entered mobile number isn't in a right format!"),
    )
    id_regex = RegexValidator(
        regex="^[0-9]{15}$", message=_("Entered ID number isn't in a right format!")
    )
    # user personal info

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        primary_key=True,
    )
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    nationality = models.CharField(max_length=255, blank=True, null=True)
    passport = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    identification = models.CharField(validators=[id_regex], max_length=15)
    birthdate = models.DateField(blank=True, null=True)
    position = models.CharField(max_length=255)
    gender = models.CharField(
        max_length=6,
        choices=GENDER_CHOICES,
        default="male",
        blank=True,
        null=True,
    )

    education = models.CharField(max_length=255, blank=True, null=True)
    home_address = models.TextField(blank=True, null=True)
    mobile_number = models.CharField(
        validators=[mobile_num_regex],
        unique=True,
        max_length=20,
    )

    photo = models.ImageField(
        blank=True,
        null=True,
        upload_to=user_photo_file_path,
    )
    avatar = models.ImageField(blank=True, null=True, upload_to=user_photo_file_path)
    cover = models.ImageField(blank=True, null=True, upload_to=user_photo_file_path)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Check if the photo exists and its size exceeds the maximum allowed size
        if self.photo:
            photo_size = self.photo.size  # Size in bytes
            max_size_bytes = 1024 * 1024  # 1 MB

            if photo_size > max_size_bytes:
                # Resize the photo
                self.resize_photo()

            # Resize and save the avatar image
            if not self.avatar:
                self.resize_and_save_avatar()

    def resize_photo(self):
        # Set the maximum size in bytes (1 MB = 1024 * 1024 bytes)
        max_size_bytes = 1024 * 1024

        # Open the image using Pillow
        with Image.open(self.photo.path) as img:
            # Check the size of the image in bytes
            img_byte_array = BytesIO()
            img.save(img_byte_array, format=img.format)
            img_size_bytes = img_byte_array.tell()

            # If the image size exceeds the maximum size, resize it
            if img_size_bytes > max_size_bytes:
                # Calculate the scaling factor to resize the image
                scaling_factor = (max_size_bytes / img_size_bytes) ** 0.5
                new_width = int(img.width * scaling_factor)
                new_height = int(img.height * scaling_factor)

                # Resize the image
                resized_img = img.resize((new_width, new_height))

                # Save the resized image back to the photo field
                buffer = BytesIO()
                resized_img.save(buffer, format=img.format)
                self.photo.save(
                    os.path.basename(self.photo.name),
                    ContentFile(buffer.getvalue()),
                    save=True,
                )

    def resize_and_save_avatar(self):
        # Check if the photo field is not empty
        if self.photo:
            photo_path = self.photo.path

            # Check if the avatar field is not already set
            # if not self.avatar:
            # Open the image using Pillow
        with Image.open(photo_path) as img:
            # Resize the image (adjust the size as needed)
            resized_img = img.resize((300, 300))

            # Save the resized image as the avatar
            buffer = BytesIO()
            resized_img.save(buffer, format="PNG")
            self.avatar.save("avatar.png", ContentFile(buffer.getvalue()), save=True)

    class Meta:
        def __str__(self):
            return self.email


