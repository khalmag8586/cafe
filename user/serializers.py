from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.contrib.auth.models import Permission, Group
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from user.models import User


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name"]


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["codename", "name"]


class UserSerializer(serializers.ModelSerializer):
    # groups = GroupSerializer(many=True)
    # user_permissions = PermissionSerializer(many=True)
    groups = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=Group.objects.all()
    )
    user_permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "password",
            "name",
            "name_ar",
            "created_at",
            "updated_at",
            "nationality",
            "passport",
            "identification",
            "birthdate",
            "position",
            "gender",
            "education",
            "home_address",
            "mobile_number",
            "photo",
            "avatar",
            "cover",
            "groups",
            "user_permissions",
            "is_staff",
            "is_active",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            # "password": {"write_only": True, "min_length": 8},
            "password": {
                "write_only": True,
                "min_length": 8,
                "validators": [
                    validate_password,
                    RegexValidator(
                        regex="[A-Z]",
                        message=_(
                            "Password must contain at least one uppercase letter."
                        ),
                        code="password_no_upper",
                    ),
                    RegexValidator(
                        regex="[a-z]",
                        message=_(
                            "Password must contain at least one lowercase letter."
                        ),
                        code="password_no_lower",
                    ),
                    RegexValidator(
                        regex="[0-9]",
                        message=_("Password must contain at least one digit."),
                        code="password_no_digit",
                    ),
                    # RegexValidator(
                    #     regex='[!@#$%^&*(),.?":{}|<>]',
                    #     message=_('Password must contain at least one symbol.'),
                    #     code='password_no_symbol',
                    # ),
                ],
            },
            "photo": {"default": "default_photos/default.jpg"},
            "cover": {"default": "default_photos/default_cover.jpg"},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "user_permissions" in self.fields:
            self.fields["user_permissions"] = PermissionSerializer(
                many=True, read_only=True
            )

    # def create(self, validated_data):
    #     """Create and return a user with encrypted password."""
    #     return get_user_model().objects.create_user(**validated_data)
    def create(self, validated_data):
        groups_data = validated_data.pop("groups", [])
        permissions_data = validated_data.pop("user_permissions", [])
        password = validated_data.pop("password", None)
        user = super().create(validated_data)

        for group_data in groups_data:
            group_name = group_data.name
            group = Group.objects.get(name=group_name)
            user.groups.add(group)

        for permission_data in permissions_data:
            permission_codename = permission_data.codename
            permission = Permission.objects.get(codename=permission_codename)
            user.user_permissions.add(permission)
        if password:
            user.set_password(password)
            user.save()
        return user

    # def update(self, instance, validated_data):
    #     """Update and return user."""
    #     password = validated_data.pop("password", None)
    #     user = super().update(instance, validated_data)

    #     if password:
    #         user.set_password(password)
    #         user.save()

    #     return user
    def update(self, instance, validated_data):
        groups_data = validated_data.pop("groups", [])
        permissions_data = validated_data.pop("user_permissions", [])
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)

        user.groups.clear()  # Clear existing groups
        for group_data in groups_data:
            group_name = group_data.name
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
        user.user_permissions.clear()  # Clear existing permissions
        for permission_data in permissions_data:
            permission_codename = permission_data.codename
            permission = Permission.objects.get(codename=permission_codename)
        if password:
            user.set_password(password)
            user.save()

        return user

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")


class UserDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["is_deleted"]


class UserImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "photo"]
        read_only_fields = ["id"]
        extra_kwargs = {"photo": {"required": "True"}}


class UserCoverSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "cover"]
        read_only_fields = ["id"]
        extra_kwargs = {"cover": {"required": "True"}}


class AuthTokenSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(
        style={"input_type": "password"},
        trim_whitespace=False,
    )

    def validate(self, attrs):
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        # Check whether the provided identifier is an email or a mobile number
        is_email = "@" in identifier
        if is_email:
            user = authenticate(
                request=self.context.get("request"),
                username=identifier,
                password=password,
            )
        else:
            # Assuming your user model has a field named 'mobile_number'
            user = authenticate(
                request=self.context.get("request"),
                mobile_number=identifier,
                password=password,
            )

        if not user:
            msg = _("Unable to authenticate with provided credentials")
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


class UserDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "name_ar"]


class UserGenderChoiceSerializer(serializers.Serializer):
    value = serializers.CharField()
    display = serializers.CharField()
