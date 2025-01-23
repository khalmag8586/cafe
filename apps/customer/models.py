from user.models import User
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _

import uuid
import os
from PIL import Image
from io import BytesIO


class Customer(User):
    is_customer = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Set is_staff to False by default
        if not self.pk:  # Only if the instance is being created (not updated)
            self.is_staff = False

        super().save(*args, **kwargs)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude)
        if self.user.email and User.objects.filter(email=self.user.email).exists():
            raise models.ValidationError(
                {
                    "user": _(
                        "This email address is already associated with another user."
                    )
                }
            )
