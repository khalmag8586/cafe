from rest_framework import serializers

from apps.rating.models import Rating


class RatingSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_name_ar = serializers.CharField(source="product.name_ar", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    created_by_name_ar = serializers.CharField(
        source="created_by.name_ar", read_only=True
    )
    updated_by_name = serializers.CharField(source="updated_by.name", read_only=True)
    updated_by_name_ar = serializers.CharField(
        source="updated_by.name_ar", read_only=True
    )

    class Meta:
        model = Rating
        fields = [
            "id",
            "product",
            "product_name",
            "product_name_ar",
            "stars",
            "comment",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
            "created_by_name_ar",
            "updated_by",
            "updated_by_name",
            "updated_by_name_ar",
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


class RatingDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ["id", "stars", "comment"]
