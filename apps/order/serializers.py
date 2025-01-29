from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.order.models import Order, OrderItems, Payment

from decimal import Decimal


class OrderItemsSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_name_ar = serializers.CharField(source="product.name_ar", read_only=True)

    class Meta:
        model = OrderItems
        fields = [
            "id",
            "order",
            "product",
            "product_name",
            "product_name_ar",
            "quantity",
            "remaining_quantity",
            "is_paid",
            "paid_by",
            "sub_total",
        ]
        read_only_fields = ["id", "order", "sub_total", "remaining_quantity"]


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemsSerializer(many=True)
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    check_in = serializers.SerializerMethodField()
    table_number = serializers.CharField(source="table.table_number", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    created_by_name_ar = serializers.CharField(
        source="created_by.name_ar", read_only=True
    )
    updated_by_name = serializers.CharField(source="updated_by.name", read_only=True)
    updated_by_name_ar = serializers.CharField(
        source="updated_by.name_ar", read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "table",
            "table_number",
            "number_of_pax",
            "check_in",
            "check_out_time",
            "hall",
            "shift",
            "kot_number",
            "order_items",
            "final_total",
            "vat",
            "is_paid",
            "is_deleted",
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
            "order_number",
            "final_total",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "vat",
            "kot_number",
            "is_deleted",
        ]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d--%H-%M-%S")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d--%H-%M-%S")

    def get_check_in(self, obj):
        return obj.created_at.strftime("%H-%M-%S")

    def validate(self, data):
        table = data.get("table")
        if table and table.is_occupied:
            raise serializers.ValidationError(
                _("The table is already occupied. Please select another table.")
            )
        return data

    def create(self, validated_data):
        # Extract order_items data from validated_data
        order_items_data = validated_data.pop("order_items")

        # Create the Order instance
        order = Order.objects.create(**validated_data)

        # Create OrderItems instances and calculate final_total
        total = Decimal("0.00")
        for item_data in order_items_data:
            order_item = OrderItems.objects.create(order=order, **item_data)
            total += order_item.sub_total  # Accumulate the subtotal for final total

        # Set final_total and vat after all order items are created
        order.final_total = total
        order.vat = total - (total / Decimal("1.05"))  # Assuming 5% VAT
        order.save()  # Save the order to update final_total and vat

        return order

    def update(self, instance, validated_data):
        # Extract order_items data from validated_data
        order_items_data = validated_data.pop("order_items")

        # Update the Order instance
        instance.table = validated_data.get("table", instance.table)
        instance.number_of_pax = validated_data.get(
            "number_of_pax", instance.number_of_pax
        )
        instance.hall = validated_data.get("hall", instance.hall)
        instance.save()

        # Delete existing order_items and create new ones
        instance.order_items.all().delete()
        total = Decimal("0.00")
        for item_data in order_items_data:
            order_item = OrderItems.objects.create(order=instance, **item_data)
            total += order_item.sub_total  # Accumulate the subtotal for final total

        # Set final_total and vat after all order items are created
        instance.final_total = total
        instance.vat = total - (total / Decimal("1.05"))  # Assuming 5% VAT
        instance.save()  # Save the order to update final_total and vat

        return instance


class OrderDeletedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["is_deleted"]


class PaymentSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    created_by_name_ar = serializers.CharField(
        source="created_by.name_ar", read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "orders",
            "amount",
            "payment_method",
            "created_at",
            "created_by",
            "created_by_name",
            "created_by_name_ar",
        ]
        read_only_fields = [
            "id",
        ]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")


class PaymentMethodSerializer(serializers.Serializer):
    value = serializers.CharField()
    display = serializers.CharField()
