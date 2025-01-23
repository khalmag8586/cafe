from django_filters import FilterSet, BooleanFilter,OrderingFilter
from apps.category.models import Category


class CategoryFilter(FilterSet):
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
        model = Category
        fields = {"name": ["exact"]}
