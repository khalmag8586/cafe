import django_filters
from django_filters import FilterSet

from apps.table.models import Table


class TableFilter(FilterSet):
    table_number = django_filters.CharFilter(
        field_name="table_number", lookup_expr="icontains"
    )
    hall = django_filters.CharFilter(field_name="hall", lookup_expr="icontains")

    class Meta:
        model = Table
        fields = ["table_number", "hall"]
