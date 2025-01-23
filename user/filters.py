from django_filters import FilterSet, OrderingFilter
from user.models import User


class UserFilter(FilterSet):
    # Define the ordering filter for the 'name' and 'name_ar' fields
    ordering = OrderingFilter(
        fields=(
            ("name", "name"),  # Ascending order by name
            ("-name", "name_desc"),  # Descending order by name
            ("name_ar", "name_ar"),  # Ascending order by name_ar
            ("-name_ar", "name_ar_desc"),  # Descending order by name_ar
        ),
        field_labels={
            "name": "Name (ascending)",
            "name_desc": "Name (descending)",
            "name_ar": "Name (Arabic ascending)",
            "name_ar_desc": "Name (Arabic descending)",
        },
    )

    class Meta:
        model = User
        fields = [
            "name",
            "name_ar",
        ]  # This can be an empty list or a list of other fields you want to filter by
