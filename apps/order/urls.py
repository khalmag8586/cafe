from django.urls import path
from apps.order.views import (
    OrderCreateView,
    OrderAddMoreItems,
    OrderRemoveItems,
    SplitBillView,
    CheckoutOrderView,
    GroupBillsView,
    OrderUnpaidListView,
    OrderPaidListView,
    OrderDeletedListView,
    OrderRetrieve,
    OrderDeleteTemporaryView,
    OrderRestoreView,
    OrderDeleteView,
    PaymentListView,
    PaymentMethodDialogView,
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
    path("order_deleted_list/", OrderDeletedListView.as_view(), name="order-deleted-list"),
    path("order_retrieve/", OrderRetrieve.as_view(), name="order-retrieve"),
    path(
        "order_temp_delete/",
        OrderDeleteTemporaryView.as_view(),
        name="order-delete-temp",
    ),
    path("order_restore/", OrderRestoreView.as_view(), name="order-restore"),
    path("order_delete/", OrderDeleteView.as_view(), name="order-delete"),
    path("payment_list/", PaymentListView.as_view(), name="payment-list"),
    path(
        "payment_method_dialog/",
        PaymentMethodDialogView.as_view(),
        name="payment-method-dialog",
    ),
]
