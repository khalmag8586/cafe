from apps.about_us.models import AboutUs

from rest_framework import serializers


class AboutUsSerializer(serializers.ModelSerializer):
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
        model = AboutUs
        fields = [
            "id",
            "index",
            "our_vision",
            "our_vision_ar",
            "our_mission",
            "our_mission_ar",
            "who_we_are",
            "who_we_are_ar",
            "our_promise",
            "our_promise_ar",
            "x_account",
            "fb_account",
            "wa_account",
            "inst_account",
            "linkedin_account",
            "yt_account",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
        ]
        read_only_fields = [
            "id",
            "index",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")
