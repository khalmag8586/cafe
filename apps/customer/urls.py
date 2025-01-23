from django.urls import path
from apps.customer.views import (
    CustomerLoginView,
    CreateCustomerView,
    CustomerListView,
    CustomerRetrieve,
    ManagerCustomerView,
    CustomerActivationStatusView,
    forgot_password,
)

app_name = "customer"
urlpatterns = [
    path("customer_registration/", CreateCustomerView.as_view(), name="registration"),
    path("customer_login/", CustomerLoginView.as_view(), name="customer-login"),
    path("customer_list/", CustomerListView.as_view(), name="all-customers"),
    path("customer_retrieve/", CustomerRetrieve.as_view(), name="customer-retrieve"),
    path(
        "customer_me/", ManagerCustomerView.as_view(), name="customer update his data"
    ),
    path(
        "customer_change_active/",
        CustomerActivationStatusView.as_view(),
        name="customer_change_active",
    ),
    path("forgot_password/", forgot_password, name="forgot_password"),
]
