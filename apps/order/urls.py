from django.urls import path
from apps.order.views import (
    # creating views
    OrderCreateView,
    OrderAddMoreItems,
    OrderRemoveItems,
    OrderPrintNewItems,
    # paying views
    ApplyDiscountToOrderView,
    SplitBillView,
    CheckoutOrderView,
    GroupBillsView,
    # order views
    OrderUnpaidListView,
    OrderPaidListView,
    OrderDeletedListView,
    OrderRetrieve,
    OrderDeleteTemporaryView,
    OrderRestoreView,
    OrderDeleteView,
    # payment views
    PaymentListView,
    PaymentRetrieveView,
    PaymentMethodDialogView,
    DiscountCreateView,
    DiscountListView,
    DiscountInactiveListView,
    DiscountRetrieveView,
    DiscountUpdateView,
    DiscountChangeStatusView,
    DiscountDeleteView,
)

urlpatterns = [
    path("create_order/", OrderCreateView.as_view(), name="create-order"),
    path("add_more_items/", OrderAddMoreItems.as_view(), name="add more items"),
    path(
        "send_items_to_printers/", OrderPrintNewItems.as_view(), name="print new items"
    ),
    path("remove_items/", OrderRemoveItems.as_view(), name="remove items"),
    # order paying urls
    path("apply_discount/", ApplyDiscountToOrderView.as_view(), name="apply discount"),
    path("split_bill/", SplitBillView.as_view(), name="split bill"),
    path("checkout_order/", CheckoutOrderView.as_view(), name="checkout order"),
    path("group_bills/", GroupBillsView.as_view(), name="group bills"),
    # order urls
    path("order_unpaid_list/", OrderUnpaidListView.as_view(), name="order-list"),
    path("order_paid_list/", OrderPaidListView.as_view(), name="order-paid-list"),
    path(
        "order_deleted_list/", OrderDeletedListView.as_view(), name="order-deleted-list"
    ),
    path("order_retrieve/", OrderRetrieve.as_view(), name="order-retrieve"),
    path(
        "order_temp_delete/",
        OrderDeleteTemporaryView.as_view(),
        name="order-delete-temp",
    ),
    path("order_restore/", OrderRestoreView.as_view(), name="order-restore"),
    path("order_delete/", OrderDeleteView.as_view(), name="order-delete"),
    # payment urls
    path("payment_list/", PaymentListView.as_view(), name="payment-list"),
    path("payment_retrieve/", PaymentRetrieveView.as_view(), name="payment-retrieve"),
    path(
        "payment_method_dialog/",
        PaymentMethodDialogView.as_view(),
        name="payment-method-dialog",
    ),
    # discount urls
    path("discount_create/", DiscountCreateView.as_view(), name="discount-create"),
    path("discount_list/", DiscountListView.as_view(), name="discount-list"),
    path(
        "discount_inactive_list/",
        DiscountInactiveListView.as_view(),
        name="discount inactive list",
    ),
    path(
        "discount_retrieve/", DiscountRetrieveView.as_view(), name="discount-retrieve"
    ),
    path("discount_update/", DiscountUpdateView.as_view(), name="discount-update"),
    path(
        "discount_change_status/",
        DiscountChangeStatusView.as_view(),
        name="discount change status",
    ),
    path("discount_delete/", DiscountDeleteView.as_view(), name="discount-delete"),
]
