from django.db import models
from django.db.models import Max

from django.conf import settings

import uuid


class AboutUsManager(models.Manager):
    def reorder_indexes(self):
        # Reorder the indexes based on the created_at field
        for i, obj in enumerate(self.all().order_by("created_at")):
            if obj.index != i:
                obj.index = i
                super(AboutUs, obj).save(update_fields=["index"])


class AboutUs(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    index = models.PositiveIntegerField(unique=True)
    our_vision = models.TextField(null=True, blank=True)
    our_vision_ar = models.TextField(null=True, blank=True)
    our_mission = models.TextField(null=True, blank=True)
    our_mission_ar = models.TextField(null=True, blank=True)
    who_we_are = models.TextField(null=True, blank=True)
    who_we_are_ar = models.TextField(null=True, blank=True)
    our_promise = models.TextField(null=True, blank=True)
    our_promise_ar = models.TextField(null=True, blank=True)
    x_account = models.CharField(max_length=255, null=True, blank=True)
    fb_account = models.CharField(max_length=255, null=True, blank=True)
    linkedin_account = models.CharField(max_length=255, null=True, blank=True)
    wa_account = models.CharField(max_length=255, null=True, blank=True)
    inst_account = models.CharField(max_length=255, null=True, blank=True)
    yt_account = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_created_aboutUs",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_updated_aboutUs",
        blank=True,
        null=True,
    )
    objects = AboutUsManager()

    def save(self, *args, **kwargs):
        if self.index is None:
            max_index = AboutUs.objects.aggregate(Max("index"))["index__max"]
            self.index = 0 if max_index is None else max_index + 1
        super().save(*args, **kwargs)
        # Reorder indexes after saving
        AboutUs.objects.reorder_indexes()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Reorder indexes after deletion
        AboutUs.objects.reorder_indexes()

    class Meta:
        ordering = ["created_at"]
