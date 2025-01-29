from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from base64 import b64encode


from django.utils.translation import gettext_lazy as _

from apps.product.models import Product, ProductImages
from apps.category.models import Category
from apps.category.serializers import CategorySerializer


class CategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "name_ar", "slug"]


# Product serializers
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImages
        fields = "__all__"
        read_only_fields = ["id"]
        extra_kwargs = {"image": {"required": "True"}}


class ProductSerializer(serializers.ModelSerializer):
    gallery = ProductImageSerializer(
        many=True, read_only=True, required=False, source="product_images"
    )
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(
            max_length=1000000, allow_empty_file=False, use_url=False
        ),
        write_only=True,
        required=False,
    )
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

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_ar",
            "description",
            "price",
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
            "gallery",
            "uploaded_images",
            "photo",
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
        # Create ProductImages instances for uploaded images
        if uploaded_images_data:
            for image_data in uploaded_images_data:
                ProductImages.objects.create(
                    product=product, image=image_data
                )  # Associate product image with the product

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

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_ar",
            "description",
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
