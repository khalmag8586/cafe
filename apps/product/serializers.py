from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from base64 import b64encode


from django.utils.translation import gettext_lazy as _

from apps.product.models import Product
from apps.category.models import Category
from apps.rating.models import Rating
from apps.category.serializers import CategorySerializer


class CategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "name_ar", "slug"]


class RatingSimpleSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.name")
    created_by_name_ar = serializers.CharField(source="created_by.name_ar")
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Rating
        fields = [
            "id",
            "stars",
            "comment",
            "created_at",
            "updated_at",
            "created_by_name",
            "created_by_name_ar",
        ]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")


# Product serializers


class ProductSerializer(serializers.ModelSerializer):
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
    section_name = serializers.CharField(source="section.name", read_only=True)
    category = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    ratings = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_ar",
            "description",
            "price_pdf",
            "price_sib",
            "category",
            "section",
            "section_name",
            "slug",
            "created_at",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "updated_at",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
            "is_active",
            "image",
            "note_image",
            "pdf_file",
            "mp3_file",
            "sib_file",
            "midi_file",
            "views_num",
            "no_of_ratings",
            "avg_ratings",
            "ratings",
        ]
        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "updated_at",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
            "views_num",
        ]

    def create(self, validated_data):
        uploaded_images_data = validated_data.pop(
            "uploaded_images", None
        )  # Extract uploaded images data
        category_ids = validated_data.pop(
            "category", []
        )  # Get category IDs from validated data

        product = Product.objects.create(**validated_data)

        for category_id in category_ids:
            category = Category.objects.get(pk=category_id)
            product.category.add(category)  # Add each category to the product

        return product

    def update(self, instance, validated_data):

        # Update instance attributes with validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Include category data in representation
        categories_data = CategorySimpleSerializer(
            instance.category.all(), many=True
        ).data
        representation["category"] = categories_data
        return representation

    def get_ratings(self, obj):
        ratings = obj.ratings.all().order_by(
            "-created_at"
        )  # This uses the reverse relationship
        return RatingSimpleSerializer(ratings, many=True).data


class ProductImageOnlySerializer(serializers.ModelSerializer):
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
    category = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    ratings = serializers.SerializerMethodField()
    pdf_file = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_ar",
            "description",
            "price_pdf",
            "price_sib",
            "category",
            "slug",
            "created_at",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "updated_at",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
            "is_active",
            "image",
            "note_image",
            "mp3_file",
            "pdf_file",
            "views_num",
            "no_of_ratings",
            "avg_ratings",
            "ratings",
        ]
        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "updated_at",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
            "views_num",
        ]

    def create(self, validated_data):
        uploaded_images_data = validated_data.pop(
            "uploaded_images", None
        )  # Extract uploaded images data
        category_ids = validated_data.pop(
            "category", []
        )  # Get category IDs from validated data

        product = Product.objects.create(**validated_data)

        for category_id in category_ids:
            category = Category.objects.get(pk=category_id)
            product.category.add(category)  # Add each category to the product

        return product

    def update(self, instance, validated_data):

        # Update instance attributes with validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance

    def get_pdf_file(self, obj):
        # Return the pdf_file only if price_pdf is zero
        if obj.price_pdf == 0.00:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.pdf_file.url)
        return None

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Include category data in representation
        categories_data = CategorySimpleSerializer(
            instance.category.all(), many=True
        ).data
        representation["category"] = categories_data
        return representation

    def get_ratings(self, obj):
        ratings = obj.ratings.all().order_by(
            "-created_at"
        )  # This uses the reverse relationship
        return RatingSimpleSerializer(ratings, many=True).data


class ProductActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["is_active"]


class ProductDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["is_deleted"]


class ProductDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "slug", "name", "name_ar"]


class ProductCategoryBulkSerializer(serializers.Serializer):
    product_id = serializers.ListField(child=serializers.UUIDField())
    category_id = serializers.ListField(child=serializers.UUIDField())
