from django_filters import FilterSet, BooleanFilter,OrderingFilter
from apps.product.models import Product

class ProductFilter(FilterSet):
    ordering = OrderingFilter(
        fields=(
            ("name", "name"),  # Ascending order by name
            ("-name", "name_desc"),  # Descending order by name
            ('name_ar','name_ar'),
            ('-name_ar',"name_ar_desc"),
            ('created_at',"created_at"),
            ('-created_at',"created_at_desc"),
        ),
        field_labels={
            "name": "Name (ascending)",
            "name_desc": "Name (descending)",
        },
    )
    class Meta:
        model = Product
        fields = {"name": ["exact"]}
