from rest_framework import serializers

from apps.service.models import Service, ServiceImages


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImages
        fields = "__all__"


class ServiceSerializer(serializers.ModelSerializer):
    gallery = ServiceImageSerializer(many=True, read_only=True, required=False)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(
            max_length=1000000, allow_empty_file=False, use_url=False
        ),
        write_only=True,
        required=False,
    )
    created_at = serializers.SerializerMethodField()
    created_by_user_name = serializers.CharField(
        source="created_by.name", read_only=True
    )
    created_by_user_name_ar = serializers.CharField(
        source="created_by.name_ar", read_only=True
    )
    updated_at = serializers.SerializerMethodField()
    updated_by_user_name = serializers.CharField(
        source="updated_by.name", read_only=True
    )
    updated_by_user_name_ar = serializers.CharField(
        source="updated_by.name_ar", read_only=True
    )
    section_name = serializers.CharField(source="section.name", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "name_ar",
            "section",
            "section_name",
            "description",
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
            "gallery",
            "uploaded_images",
        ]
        read_only_fields = ["id"]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")

    def create(self, validated_data):
        uploaded_images_data = validated_data.pop(
            "uploaded_images", None
        )  # Extract uploaded images data
        service = Service.objects.create(**validated_data)  # Create the service object

        if uploaded_images_data:
            for image_data in uploaded_images_data:
                service_image = ServiceImages.objects.create(
                    service=service, image=image_data
                )  # Set service field
                service.gallery.add(
                    service_image
                )  # Associate service image with the service

        return service

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
                service_image = ServiceImages.objects.create(
                    service=instance, image=image_data
                )
                instance.gallery.add(service_image)

        return instance


class ServiceActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["is_active"]


class ServiceDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["is_deleted"]


# dialog serializers
class ServiceDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        # fields = ["id", "name", "name_ar", "service_symbol"]
        fields = ["id", "name", "name_ar"]


class AvailableSymbolsSerializer(serializers.Serializer):
    available_letters = serializers.ListField(child=serializers.CharField())
