from django.urls import path
from apps.product.views import (
    ProductCreateView,
    ProductCategoryBulkCreateView,
    ProductCategoryBulkRemoveView,
    ProductCategoryBulkUpdateView,
    ProductListView,
    DeletedProductListView,
    ProductByCategoryView,
    ProductRetrieveView,
    ProductActiveListView,
    ProductActiveRetrieveView,
    ProductChangeActiveView,
    ProductUpdateView,
    ProductDeleteTemporaryView,
    ProductRestoreView,
    ProductDeleteView,
    ProductDialogView,
)


app_name = "products"
urlpatterns = [
    path("product_create/", ProductCreateView.as_view(), name="product-create"),
    path(
        "product_add_to_category/",
        ProductCategoryBulkCreateView.as_view(),
        name="add multi products to multi categories",
    ),
    path(
        "product_remove_from_category/",
        ProductCategoryBulkRemoveView.as_view(),
        name="remove multi products from multi categories",
    ),
    path(
        "product_update_category/",
        ProductCategoryBulkUpdateView.as_view(),
        name="update product category",
    ),
    path("product_list/", ProductListView.as_view(), name="product-list"),
    path(
        "deleted_product_list/",
        DeletedProductListView.as_view(),
        name="deleted-product-list",
    ),
    path(
        "product_by_category/",
        ProductByCategoryView.as_view(),
        name="product-by-category",
    ),
    path("product_retrieve/", ProductRetrieveView.as_view(), name="product-retrieve"),
    path(
        "product_active_list/",
        ProductActiveListView.as_view(),
        name="active-product-list",
    ),
    path(
        "product_active_retrieve/",
        ProductActiveRetrieveView.as_view(),
        name="product_active_retrieve",
    ),
    path(
        "product_change_status/",
        ProductChangeActiveView.as_view(),
        name="change-product-status",
    ),
    path("product_update/", ProductUpdateView.as_view(), name="update-product"),
    path(
        "product_temp_delete/",
        ProductDeleteTemporaryView.as_view(),
        name="product-del-temporary",
    ),
    path(
        "product_restore/",
        ProductRestoreView.as_view(),
        name="product-restore",
    ),
    path("product_delete/", ProductDeleteView.as_view(), name="product-delete"),
    path("product_dialog/", ProductDialogView.as_view(), name="product-dialog"),
]
