from django.urls import path
from apps.cart.views import (
    CartCreateView,
    CartListView,
    CartItemCreateView,
    CartRetrieveView,
    CartItemsListView,
    CustomerCartRetrieveView,
    CartItemUpdateQuantityView,
    CartItemDeleteView,
    CartDeleteView,
    # wishList
    WishListCreateView,
    WishListListView,
    CustomerWishListRetrieveView,
    WishlistRetrieveView,
    WishlistItemCreateView,
    MoveCartItemToWishlistView,
    MoveWishlistItemToCartView,
    WishlistItemUpdateQuantityView,
    WishlistItemDeleteView,
)

app_name = "cart"

urlpatterns = [
    path("cart_create/", CartCreateView.as_view(), name="cart-create"),
    path("cart_list/", CartListView.as_view(), name="cart-list"),
    path("add_item_to_cart/", CartItemCreateView.as_view(), name="add-cart-item"),
    path(
        "cart_retrieve/",
        CartRetrieveView.as_view(),
        name="retrieve-cart-items",
    ),
    path(
        "cart_items_list/",
        CartItemsListView.as_view(),
        name="list-cart-items",
    ),
    path(
        "cart_by_customer/",
        CustomerCartRetrieveView.as_view(),
        name="retrieve-cart-by-customer",
    ),
    path(
        "cart_item_update_quantity/",
        CartItemUpdateQuantityView.as_view(),
        name="update-cart-item",
    ),
    path(
        "cart_item_delete/",
        CartItemDeleteView.as_view(),
        name="delete-cart-item",
    ),
    path("cart_delete/", CartDeleteView.as_view(), name="delete-cart"),
    # wishlist urls
    path("wishlist_create/", WishListCreateView.as_view(), name="wishlist-create"),
    path("wishlist_list/", WishListListView.as_view(), name="wishlist-list"),
    path(
        "wishlist_retrieve/", WishlistRetrieveView.as_view(), name="wishlist-retrieve"
    ),
    path(
        "wishlist_by_customer/",
        CustomerWishListRetrieveView.as_view(),
        name="retrieve-wishlist-by-customer",
    ),
    path(
        "add_item_to_wishlist/",
        WishlistItemCreateView.as_view(),
        name="add-wishlist-item",
    ),
    path(
        "move_cart_item_to_wishlist/",
        MoveCartItemToWishlistView.as_view(),
        name="move-cart-item-to-wishlist",
    ),
    path(
        "move_wishlist_item_to_cart/",
        MoveWishlistItemToCartView.as_view(),
        name="move-wishlist-item-to-cart",
    ),
    path(
        "wishlist_item_update_quantity/",
        WishlistItemUpdateQuantityView.as_view(),
        name="update-wishlist-item",
    ),
    path(
        "wishlist_item_delete/",
        WishlistItemDeleteView.as_view(),
        name="delete-wishlist-item",
    ),
]
