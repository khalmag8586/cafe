import django_filters
from django_filters import FilterSet

from apps.order.models import Order, Payment


class OrderFilter(FilterSet):
    id = django_filters.CharFilter(field_name="id", lookup_expr="icontains")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    created_at = django_filters.CharFilter(
        field_name="created_at", lookup_expr="icontains"
    )

    class Meta:
        model = Order
        fields = ["id", "created_at"]


class PaymentFilter(FilterSet):
    id = django_filters.CharFilter(field_name="id", lookup_expr="icontains")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    created_at = django_filters.CharFilter(
        field_name="created_at", lookup_expr="icontains"
    )
    payment_method = django_filters.CharFilter(
        field_name="payment_method", lookup_expr="icontains"
    )

    class Meta:
        model = Payment
        fields = ["id", "created_at", "payment_method"]
