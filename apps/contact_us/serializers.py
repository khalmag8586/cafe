from rest_framework import serializers

from apps.contact_us.models import ContactUs


class ContactUsSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = ContactUs
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "job_title",
            "message",
            "is_read",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_read"]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")


class ContactUsReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = ["is_read"]
