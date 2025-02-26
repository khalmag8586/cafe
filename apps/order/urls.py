from django.urls import path
from apps.order.views import (
    # creating views
    OrderCreateView,
    OrderChangeTableView,
    OrderAddMoreItems,
    OrderRemoveItems,
    OrderItemNote,
    OrderPrintNewItems,
    # paying views
    ApplyDiscountToOrderView,
    RemoveDiscountFromOrderView,
    SplitBillView,
    GenerateBillView,
    FetchInvoiceView,
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
    PaymentDeleteView,
    PaymentMethodDialogView,
    # discount views
    DiscountCreateView,
    DiscountListView,
    DiscountInactiveListView,
    DiscountRetrieveView,
    DiscountUpdateView,
    DiscountChangeStatusView,
    DiscountDeleteView,
    # close day
    BusinessDayCreateView,
    CloseDayAPIView,
    CloseDayListView,
    CloseDayDeleteView,
    # reports
    ZReportView,
    XReportView,
    XReportViewWithoutPrint,
    XReportForPeriodView,
    SalesReportView,
)

urlpatterns = [
    path("create_order/", OrderCreateView.as_view(), name="create-order"),
    path("change_table/", OrderChangeTableView.as_view(), name="change-table"),
    path("add_more_items/", OrderAddMoreItems.as_view(), name="add more items"),
    path("add_note/", OrderItemNote.as_view(), name="add note to items"),
    path(
        "send_items_to_printers/", OrderPrintNewItems.as_view(), name="print new items"
    ),
    path("remove_items/", OrderRemoveItems.as_view(), name="remove items"),
    # order paying urls
    path("apply_discount/", ApplyDiscountToOrderView.as_view(), name="apply discount"),
    path(
        "remove_discount/",
        RemoveDiscountFromOrderView.as_view(),
        name="remove discount",
    ),
    path("split_bill/", SplitBillView.as_view(), name="split bill"),
    path("generate_bill/", GenerateBillView.as_view(), name="generate bill"),
    path("fetch_invoice/", FetchInvoiceView.as_view(), name="fetch invoice"),
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
    path("payment_delete/", PaymentDeleteView.as_view(), name="payment-delete"),
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
    path("close_day/", CloseDayAPIView.as_view(), name="close day"),
    path("close_day_list/", CloseDayListView.as_view(), name="close day list"),
    path("close_day_delete/", CloseDayDeleteView.as_view(), name="closeday delete"),
    path("z_report/", ZReportView.as_view(), name="z report"),
    path("x_report/", XReportView.as_view(), name="x report"),
    path("x_report_no_print/", XReportViewWithoutPrint.as_view(), name="x report without print"),
    path("x_report_period/", XReportForPeriodView.as_view(), name="x report period"),
    path("sales_report/", SalesReportView.as_view(), name="sales report"),
    path(
        "businessday_create/",
        BusinessDayCreateView.as_view(),
        name="create business day",
    ),
]
