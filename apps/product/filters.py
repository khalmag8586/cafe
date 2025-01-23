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
            ('price_pdf',"price_pdf"),
            ('-price_pdf',"price_pdf_desc"),
            ('price_sib',"price_sib"),
            ('-price_sib',"price_sib_desc"),
            ('avg_ratings',"avg_ratings"),
            ('-avg_ratings',"avg_ratings_desc"),
        ),
        field_labels={
            "name": "Name (ascending)",
            "name_desc": "Name (descending)",
            "avg_ratings": "Average Ratings (ascending)",
            "avg_ratings_desc": "Average Ratings (descending)",
        },
    )
    class Meta:
        model = Product
        fields = {"name": ["exact"]}
