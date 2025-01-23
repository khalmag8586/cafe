from rest_framework import serializers

from apps.order.models import Order, OrderItems


from rest_framework import serializers


class OrderItemsSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_name_ar = serializers.CharField(source="product.name_ar", read_only=True)
    product_image = serializers.ImageField(source="product.image")
    file = serializers.SerializerMethodField()

    class Meta:
        model = OrderItems
        fields = [
            "id",
            "order",
            "product",
            "product_name",
            "product_name_ar",
            "product_image",
            "purchase_type",
            "quantity",
            "sub_total",
            "file",
        ]
        read_only_fields = ["id", "order", "sub_total"]

    


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemsSerializer(many=True, read_only=True)
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    created_by_name_ar = serializers.CharField(
        source="created_by.name_ar", read_only=True
    )
    updated_by_name = serializers.CharField(source="updated_by.name", read_only=True)
    updated_by_name_ar = serializers.CharField(
        source="updated_by.name_ar", read_only=True
    )
    customer_phone = serializers.CharField(source="created_by.mobile_number")
    customer_email = serializers.CharField(source="created_by.email")

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "payment_method",
            "payment_status",
            "order_items",
            "final_total",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
            "created_by_name_ar",
            "customer_phone",
            "customer_email",
            "updated_by",
            "updated_by_name",
            "updated_by_name_ar",
            "paypal_payment_id",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "final_total",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "paypal_payment_id",
        ]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d--%H-%M-%S")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d--%H-%M-%S")


class OrderDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "order_number"]
