import uuid
import os

from django.db import models
from django.db.models.signals import pre_save
from django.core.files.base import ContentFile
from django.dispatch import receiver
from django.conf import settings
from django.utils.translation import gettext_lazy as _


from PIL import Image
from io import BytesIO

from cafe.util import unique_slug_generator

from apps.category.models import Category
from apps.customer.models import Customer
from apps.section.models import Section
from apps.rating.models import Rating
from django.core.exceptions import ValidationError


def validate_file_extension(value, allowed_extensions):
    ext = value.name.split(".")[-1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            _(
                "Unsupported file extension: %(ext)s. Allowed extensions are: %(allowed_extensions)s"
            ),
            params={"ext": ext, "allowed_extensions": ", ".join(allowed_extensions)},
        )


def validate_pdf(value):
    validate_file_extension(value, ["pdf"])


def validate_mp3(value):
    validate_file_extension(value, ["mp3"])


def validate_sib(value):
    validate_file_extension(value, ["sib"])


def validate_midi(value):
    validate_file_extension(value, ["mid"])


def product_image_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{uuid.uuid4()}{ext}"

    return os.path.join("uploads", "product", "images", filename)


def product_pdf_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    return os.path.join("uploads", "product", "pdfs", filename)


def product_mp3_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    return os.path.join("uploads", "product", "mp3s", filename)


def product_sib_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    return os.path.join("uploads", "product", "sibs", filename)


def product_midi_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    return os.path.join("uploads", "product", "midis", filename)


class Product(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )
    category = models.ManyToManyField(Category, related_name="products", blank=True)
    section = models.ForeignKey(
        Section,
        related_name="products_section",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=255, unique=True)
    name_ar = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, allow_unicode=True, unique=True)
    description = models.TextField(blank=True, null=True)
    price_pdf = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    price_sib = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_created_product",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_updated_product",
        blank=True,
        null=True,
    )
    image = models.ImageField(blank=True, null=True, upload_to=product_image_file_path)
    note_image = models.ImageField(blank=True, null=True, upload_to=product_image_file_path)
    pdf_file = models.FileField(
        blank=True,
        null=True,
        upload_to=product_pdf_file_path,
        validators=[validate_pdf],
    )
    mp3_file = models.FileField(
        blank=True,
        null=True,
        upload_to=product_mp3_file_path,
        validators=[validate_mp3],
    )
    sib_file = models.FileField(
        blank=True,
        null=True,
        upload_to=product_sib_file_path,
        validators=[validate_sib],
    )
    midi_file = models.FileField(
        blank=True,
        null=True,
        upload_to=product_midi_file_path,
        validators=[validate_midi],
    )
    views_num = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        # # Set the price based on the purchase type
        # if self.purchase_type == 'pdf':
        #     self.price = self.price_pdf
        # elif self.purchase_type == 'sib':
        #     self.price = self.price_sib
        super().save(*args, **kwargs)
        if self.image:
            image_size = self.image.size  # Size in bytes
            max_size_bytes = 500 * 500  # .5 MB
            if image_size > max_size_bytes:
                # Resize the photo
                self.resize_photo()

    def resize_photo(self):
        # Set the maximum size in bytes (.5 MB = 500 * 500 bytes)
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

    def increment_views_num(self, customer):
        from .models import ProductView  # Avoid circular import

        if not ProductView.objects.filter(product=self, customer=customer).exists():
            ProductView.objects.create(product=self, customer=customer)
            self.views_num += 1
            self.save(update_fields=["views_num"])

    def no_of_ratings(self):
        ratings = Rating.objects.filter(product=self)
        return len(ratings)

    def avg_ratings(self):
        sum = 0
        ratings = Rating.objects.filter(product=self)
        for i in ratings:
            sum += i.stars
        if len(ratings) > 0:
            return sum / len(ratings)
        else:
            return 0


class ProductView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, related_name="views", on_delete=models.CASCADE)
    customer = models.ForeignKey(
        Customer, related_name="product_views", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "customer")


@receiver(pre_save, sender=Product)
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
            return "can not make a slug for product "
