from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.core.files.base import ContentFile

import uuid
import os
from PIL import Image
from io import BytesIO
from cafe.util import unique_slug_generator


def category_image_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    return os.path.join("uploads", "category", filename)


class Category(models.Model):

    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        primary_key=True,
    )
    name = models.CharField(max_length=255, unique=True)
    name_ar = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, allow_unicode=True, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_created_category",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_updated_category",
        blank=True,
        null=True,
    )
    image = models.ImageField(
        blank=True,
        null=True,
        upload_to=category_image_file_path,
    )


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            image_size = self.image.size  # Size in bytes
            max_size_bytes = 500 * 500  # .5 MB
            if image_size > max_size_bytes:
                # Resize the photo
                self.resize_photo()

    def resize_photo(self):
        # Set the maximum size in bytes (1 MB = 1024 * 1024 bytes)
        max_size_bytes = 500 * 500

        # Open the image using Pillow
        with Image.open(self.image.path) as img:
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
                self.image.save(
                    os.path.basename(self.image.name),
                    ContentFile(buffer.getvalue()),
                    save=True,
                )


class CategoryImages(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to=category_image_file_path,
    )


@receiver(pre_save, sender=Category)
def pre_save_receiver(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)
    # Update slug if name is changed
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.name != instance.name:
                instance.slug = unique_slug_generator(instance)
        except sender.DoesNotExist:
            return "can not make a slug for category "
