from django.urls import path
from apps.order.views import (
    OrderCreateView,
    OrderAddMoreItems,OrderRemoveItems,
    SplitBillView,
    CheckoutOrderView,
    GroupBillsView,
    OrderUnpaidListView,OrderPaidListView,
    OrderRetrieve,
    OrderDeleteView,
)

urlpatterns = [
    path("create_order/", OrderCreateView.as_view(), name="create-order"),
    path("add_more_items/", OrderAddMoreItems.as_view(), name="add more items"),
    path("remove_items/", OrderRemoveItems.as_view(), name="remove items"),
    path("split_bill/", SplitBillView.as_view(), name="split bill"),
    path("checkout_order/", CheckoutOrderView.as_view(), name="checkout order"),
    path("group_bills/", GroupBillsView.as_view(), name="group bills"),
    path("order_unpaid_list/", OrderUnpaidListView.as_view(), name="order-list"),
    path("order_paid_list/", OrderPaidListView.as_view(), name="order-paid-list"),
    path("order_retrieve/", OrderRetrieve.as_view(), name="order-retrieve"),
    path("order_delete/", OrderDeleteView.as_view(), name="order-delete"),
]
