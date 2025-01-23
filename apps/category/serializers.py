from apps.category.models import Category, CategoryImages

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


# Category serializers
class ParentCategoryUUIDField(serializers.PrimaryKeyRelatedField):
    queryset = Category.objects.all()


class CategoryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryImages
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    gallery = CategoryImageSerializer(many=True, read_only=True, required=False)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(
            max_length=1000000, allow_empty_file=False, use_url=False
        ),
        write_only=True,
        required=False,
    )
    parent = ParentCategoryUUIDField(
        queryset=Category.objects.all(),
        allow_null=True,
        required=False,
    )
    parent_name = serializers.SerializerMethodField()
    parent_name_ar = serializers.SerializerMethodField()
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
        model = Category
        fields = [
            "id",
            "name",
            "name_ar",
            "parent",
            "parent_name",
            "parent_name_ar",
            "slug",
            "description",
            "created_at",
            "updated_at",
            "is_active",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
            "image",
            "gallery",
            "uploaded_images",
        ]
        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")

    def get_parent_name(self, obj):
        return obj.parent.name if obj.parent else "NA"

    def get_parent_name_ar(self, obj):
        return obj.parent.name_ar if obj.parent else "NA"

    def create(self, validated_data):
        uploaded_images_data = validated_data.pop(
            "uploaded_images", None
        )  # Extract uploaded images data
        category = Category.objects.create(
            **validated_data
        )  # Create the category object

        if uploaded_images_data:
            for image_data in uploaded_images_data:
                category_image = CategoryImages.objects.create(
                    category=category, image=image_data
                )  # Set category field
                category.gallery.add(
                    category_image
                )  # Associate category image with the category

        return category

    def update(self, instance, validated_data):
        uploaded_images_data = validated_data.pop("uploaded_images", None)

        # Update instance attributes with validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # Handle updating images
        if uploaded_images_data:
            # Delete existing images
            # instance.gallery.all().delete()

            # Create new images
            for image_data in uploaded_images_data:
                category_image = CategoryImages.objects.create(
                    category=instance, image=image_data
                )
                instance.gallery.add(category_image)

        return instance


class NestedCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "name_ar", "slug", "image", "children"]

    def get_children(self, obj):
        children = Category.objects.filter(parent=obj)
        serializer = NestedCategorySerializer(children, many=True, context=self.context)
        return serializer.data
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            image_url = request.build_absolute_uri(obj.image.url)
            return image_url
        return None

class ParentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "name_ar", "slug"]


class CategoryDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["is_deleted"]


class CategoryActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["is_active"]


class CategoryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "image"]
        read_only_fields = ["id"]
        extra_kwargs = {"image": {"required": "True"}}


class CategoryDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name", "name_ar"]
