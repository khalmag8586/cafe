from django.urls import path
from apps.order.views import (
    # create_payment,
    CreatePaymentView,
    OrderCreateView,
    OrderListView,
    CustomerOrdersListView,
    OrderRetrieve,
    OrderDeleteView,
    OrderDialogListView,
)

urlpatterns = [
    path("create_order/", OrderCreateView.as_view(), name="create-order"),
    path("payment_create/", CreatePaymentView.as_view(), name="payment-create"),
    # path("payment_execute/", PaymentExecuteView.as_view(), name="payment_execute"),
    # path("payment_cancel/", PaymentCancelView.as_view(), name="payment_cancel"),
    path("order_list/", OrderListView.as_view(), name="order-list"),
    path("customer_orders/", CustomerOrdersListView.as_view(), name="customer-orders"),
    path("order_retrieve/", OrderRetrieve.as_view(), name="order-retrieve"),
    path("order_delete/", OrderDeleteView.as_view(), name="order-delete"),
    path("order_dialog/", OrderDialogListView.as_view(), name="order-dialog"),
]
