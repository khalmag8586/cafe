from rest_framework import serializers

from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage
from django.conf import settings

from apps.section.models import Section, SectionMediaFiles


class SectionMediaSerializer(serializers.ModelSerializer):
    section = serializers.PrimaryKeyRelatedField(queryset=Section.objects.all())

    class Meta:
        model = SectionMediaFiles
        fields = "__all__"


class SectionSerializer(serializers.ModelSerializer):
    gallery = SectionMediaSerializer(many=True, read_only=True)

    uploaded_media = serializers.ListField(
        child=serializers.FileField(
            max_length=100000, allow_empty_file=False, use_url=False
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

    class Meta:
        model = Section
        fields = [
            "id",
            "name",
            "name_ar",
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
            "video",
            "gallery",
            "uploaded_media",
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

    def create(self, validated_data):
        uploaded_media_data = validated_data.pop("uploaded_media", None)
        section = Section.objects.create(**validated_data)

        if uploaded_media_data:
            media_instances = []
            for media_file in uploaded_media_data:
                media_instance = SectionMediaFiles.objects.create(
                    section=section, media=media_file
                )
                media_instances.append(media_instance)

            section.gallery.set(media_instances)
            section.save()

        return section

    def update(self, instance, validated_data):
        uploaded_media_data = validated_data.pop("uploaded_media", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if uploaded_media_data:
            existing_media_instances = instance.gallery.all()
            existing_media_instance_ids = [
                media.media.id for media in existing_media_instances
            ]
            new_media_instances = [
                SectionMediaFiles(section=instance, media=media_data)
                for media_data in uploaded_media_data
                if media_data.id not in existing_media_instance_ids
            ]
            saved_new_media_instances = [instance for instance in new_media_instances]
            instance.gallery.set(
                list(existing_media_instances) + saved_new_media_instances
            )

        return instance

        """
        def update(self, instance, validated_data):
    uploaded_media_data = validated_data.pop("uploaded_media", None)

    for attr, value in validated_data.items():
        setattr(instance, attr, value)

    instance.save()

    if uploaded_media_data:
        existing_media_instances = instance.gallery.all()
        existing_media_instance_ids = [media.media.id for media in existing_media_instances]
        new_media_instances = []

        for media_data in uploaded_media_data:
            # Check if the media data has an id attribute
            if hasattr(media_data, 'id') and media_data.id not in existing_media_instance_ids:
                new_media_instance = SectionMediaFiles(section=instance, media=media_data)
                new_media_instances.append(new_media_instance)
            # If the media data doesn't have an id attribute, create a new instance
            elif not hasattr(media_data, 'id'):
                new_media_instance = SectionMediaFiles(section=instance, media=media_data)
                new_media_instances.append(new_media_instance)

        # Save the new media instances
        saved_new_media_instances = [instance.save() for instance in new_media_instances]

        # Update the gallery with existing and new media instances
        instance.gallery.set(list(existing_media_instances) + saved_new_media_instances)

    return instance
        """
class ActiveSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model=Section
        fields=['is_active']

class SectionDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "name", "name_ar", "slug"]
