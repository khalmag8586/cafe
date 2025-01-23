from rest_framework import serializers
from apps.customer.models import Customer
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class CustomerSerializer(serializers.ModelSerializer):

    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "is_customer",
            "is_staff",
            "is_active",
            "email",
            "password",
            "name",
            "name_ar",
            "mobile_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "is_staff",
            "is_customer",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
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
                ],
            },
        }

    def create(self, validated_data):
        password = validated_data.pop("password", None)

        customer = super().create(validated_data)

        if password:
            customer.set_password(password)
            customer.save()
        return customer

    def update(self, instance, validated_data):

        password = validated_data.pop("password", None)
        customer = super().update(instance, validated_data)

        if password:
            customer.set_password(password)
            customer.save()

        return customer

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")


class CustomerActivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["is_active"]
