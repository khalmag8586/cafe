from rest_framework import serializers

from apps.printer.models import Printer


class PrinterSerializer(serializers.ModelSerializer):
    created_by_user_name = serializers.CharField(
        source="created_by.name", read_only=True
    )
    created_by_user_name_ar = serializers.CharField(
        source="created_by.name_ar", read_only=True
    )
    updated_by_user_name = serializers.CharField(
        source="updated_by.name", read_only=True
    )
    updated_by_user_name_ar = serializers.CharField(
        source="updated_by.name_ar", read_only=True
    )
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Printer
        fields = [
            "id",
            "name",
            "name_ar",
            "printer_type",
            "ip_address",
            "created_at",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "updated_at",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def get_created_at(self, obj):
            return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
            return obj.updated_at.strftime("%Y-%m-%d")


class PrinterDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Printer
        fields = ["id", "name", "name_ar"]


class PrinterTypesDialogSerializer(serializers.Serializer):
    value = serializers.CharField()
    display = serializers.CharField()
