from rest_framework import serializers

from apps.table.models import Table


class TableSerializer(serializers.ModelSerializer):
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
    current_order_id = serializers.SerializerMethodField()  # New field

    class Meta:
        model = Table
        fields = [
            "id",
            "table_number",
            "no_of_pax",
            "is_occupied",
            "is_owner",
            "is_active",
            "created_at",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "updated_at",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
            "current_order_id",
        ]
        read_only_fields = ["id",'is_active']

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")

    def get_current_order_id(self, obj):
        if obj.is_occupied:
            # Use the correct related_name 'tables'
            current_order = obj.tables.filter(is_paid=False).first()
            if current_order:
                return current_order.id
        return "N/A"

class TableActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['is_active']