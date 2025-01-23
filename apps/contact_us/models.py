from django.db import models
from django.core.validators import RegexValidator

import uuid
from django.utils.translation import gettext_lazy as _


class ContactUs(models.Model):
    mobile_num_regex = RegexValidator(
        regex="^[0-9]{9,20}$",
        message=_("Entered mobile number isn't in a right format!"),
    )
    forbidden_characters_validator = RegexValidator(
            regex="<|>",
            message=_("The value cannot contain < or > characters."),
            inverse_match=True,
        )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=255,validators=[forbidden_characters_validator])
    phone = models.CharField(
        validators=[mobile_num_regex],
        max_length=20,
    )
    email = models.EmailField(max_length=255)
    job_title= models.CharField(max_length=255,validators=[forbidden_characters_validator])
    message= models.TextField(validators=[forbidden_characters_validator],max_length=3000)
    is_read= models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)