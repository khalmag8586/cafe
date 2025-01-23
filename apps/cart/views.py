from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

from apps.cart.models import (
    Cart,
    CartItems,
    Wishlist,
    WishlistItem,
)
from apps.cart.serializers import (
    CartSerializer,
    CartItemSerializer,
    WishListSerializer,
    WishListItemSerializer,
)

from apps.product.models import Product

from apps.customer.models import Customer
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from cafe.custom_permissions import OnlyCustomer, CustomerPermission
from rest_framework_simplejwt.authentication import JWTAuthentication

from cafe.pagination import StandardResultsSetPagination


class CartCreateView(generics.CreateAPIView):
    serializer_class = CartSerializer
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [OnlyCustomer]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("Cart created successfully")}, status=status.HTTP_201_CREATED
        )


class CartListView(generics.ListAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    pagination_class = StandardResultsSetPagination


class CustomerCartRetrieveView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def get_object(self):
        # customer_id = self.request.query_params.get("customer_id")
        customer_id = self.request.user.customer.id
        customer = get_object_or_404(Customer, id=customer_id)
        cart = get_object_or_404(Cart, customer=customer)
        return cart


# class CartItemCreateView(generics.CreateAPIView):
#     # Add item to cart
#     serializer_class = CartItemSerializer
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [OnlyCustomer]

#     def create(self, request, *args, **kwargs):
#         customer_id = request.user.customer.id

#         try:
#             cart = Cart.objects.get(customer=customer_id)

#         except Cart.DoesNotExist:

#             return Response(
#                 {
#                     "detail": _("Cart not found"),
#                 },
#                 status=status.HTTP_404_NOT_FOUND,
#             )

#         # this approach is to pass cart id in params
#         # cart_id = request.query_params.get("cart_id")
#         # try:
#         #     cart = Cart.objects.get(id=cart_id)
#         # except Cart.DoesNotExist:
#         #     return Response(
#         #         {"detail": _("Cart not found")}, status=status.HTTP_404_NOT_FOUND
#         #     )

#         items = request.data  # Get the list of items from the request data

#         for item_data in items:
#             product_id = item_data.get("product_id", [])
#             quantity = int(item_data.get("quantity", 1))  # Default quantity to 1
#             purchase_type = item_data.get("purchase_type")

#             try:
#                 cart_item = CartItems.objects.filter(
#                     cart=cart, product__id=product_id, purchase_type=purchase_type
#                 ).first()
#                 if cart_item:
#                     # # If the product is already in the cart, update the quantity
#                     # cart_item.quantity += quantity
#                     # cart_item.save()
#                     # cart_item_serializer = self.get_serializer(
#                     #     cart_item
#                     # )  # Use the existing cart item for serialization
#                     return Response(
#                         {"detail": _("Product already exists in the cart")},
#                         status=status.HTTP_400_BAD_REQUEST,
#                     )
#                 else:
#                     try:
#                         product = Product.objects.get(id=product_id)
#                     except Product.DoesNotExist:
#                         return Response(
#                             {"detail": _("Product not found")},
#                             status=status.HTTP_404_NOT_FOUND,
#                         )
#                     # Check if the requested quantity is larger than the available inventory
#                     # if quantity > product.inventory:
#                     #     return Response(
#                     #         {
#                     #             "message": _(
#                     #                 "Requested quantity is larger than available inventory"
#                     #             )
#                     #         },
#                     #         status=status.HTTP_400_BAD_REQUEST,
#                     #     )

#                 # Create a new cart item with the specified quantity
#                 cart_item = CartItems.objects.create(
#                     cart=cart,
#                     product=product,
#                     quantity=quantity,
#                     purchase_type=purchase_type,
#                 )
#             except CartItems.MultipleObjectsReturned:
#                 return Response(
#                     {
#                         "detail": _(
#                             "Multiple cart items found for the same product. Contact support."
#                         )
#                     },
#                     status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 )

#         return Response(
#             {"detail": _("Items added to cart successfully")},
#             status=status.HTTP_201_CREATED,
#         )

class CartItemCreateView(generics.CreateAPIView):
    # Add item to cart
    serializer_class = CartItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def create(self, request, *args, **kwargs):
        customer_id = request.user.customer.id

        try:
            cart = Cart.objects.get(customer=customer_id)

        except Cart.DoesNotExist:

            return Response(
                {
                    "detail": _("Cart not found"),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        items = request.data  # Get the list of items from the request data

        for item_data in items:
            product_id = item_data.get("product_id", [])
            quantity = int(item_data.get("quantity", 1))  # Default quantity to 1
            purchase_type = item_data.get("purchase_type")

            try:
                cart_item = CartItems.objects.filter(
                    cart=cart, product__id=product_id, purchase_type=purchase_type
                ).first()
                if cart_item:
                    # # If the product is already in the cart, update the quantity
                    # cart_item.quantity += quantity
                    # cart_item.save()
                    # cart_item_serializer = self.get_serializer(
                    #     cart_item
                    # )  # Use the existing cart item for serialization
                    return Response(
                        {"detail": _("Product already exists in the cart")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    try:
                        product = Product.objects.get(id=product_id)
                    except Product.DoesNotExist:
                        return Response(
                            {"detail": _("Product not found")},
                            status=status.HTTP_404_NOT_FOUND,
                        )

                    # Check if the product has the required files based on the purchase type
                    if purchase_type == "pdf":
                        if not product.pdf_file:
                            return Response(
                                {"detail": _("PDF file is not available for this product")},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    elif purchase_type == "sib":
                        if not product.sib_file:
                            return Response(
                                {"detail": _("SIB file is not available for this product")},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                    # Check if the requested quantity is larger than the available inventory
                    # if quantity > product.inventory:
                    #     return Response(
                    #         {
                    #             "message": _(
                    #                 "Requested quantity is larger than available inventory"
                    #             )
                    #         },
                    #         status=status.HTTP_400_BAD_REQUEST,
                    #     )

                # Create a new cart item with the specified quantity
                cart_item = CartItems.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity,
                    purchase_type=purchase_type,
                )
            except CartItems.MultipleObjectsReturned:
                return Response(
                    {
                        "detail": _(
                            "Multiple cart items found for the same product. Contact support."
                        )
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {"detail": _("Items added to cart successfully")},
            status=status.HTTP_201_CREATED,
        )
class CartRetrieveView(generics.RetrieveAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def get_object(self):
        cart_id = self.request.query_params.get("cart_id")
        cart = get_object_or_404(Cart, id=cart_id)
        return cart


class CartDeleteView(generics.DestroyAPIView):
    serializer_class = CartSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def get_object(self):
        cart_id = self.request.query_params.get("cart_id")
        cart = get_object_or_404(Cart, id=cart_id)
        return cart

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": _("Cart deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class CartItemsListView(generics.ListAPIView):
    queryset = CartItems.objects.all()
    serializer_class = CartItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]
    pagination_class = StandardResultsSetPagination

    def get_object(self):
        cart_id = self.request.query_params.get("cart_id")
        cart = get_object_or_404(Cart, id=cart_id)
        return cart

    def get_queryset(self):
        # Assuming the cart is identified by a cart_id in the URL
        cart_id = self.kwargs.get("pk")
        try:
            cart = self.get_object()
            return cart.items.all()  # Return all items related to the cart
        except Cart.DoesNotExist:
            return CartItems.objects.none()


# class CartItemRetrieveView(generics.RetrieveAPIView):
#     # queryset = CartItems.objects.all()
#     serializer_class = CartItemSerializer
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get_object(self):
#         cart_id = self.request.query_params.get("cart_id")
#         product_id = self.request.query_params.get("product_id")

#         try:
#             cart_item = CartItems.objects.get(cart__id=cart_id, product__id=product_id)
#             return cart_item  # Return the specific cart item
#         except CartItems.DoesNotExist:
#             return CartItems.objects.none()


class CartItemUpdateQuantityView(generics.UpdateAPIView):
    queryset = CartItems.objects.all()
    serializer_class = CartItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def update(self, request, *args, **kwargs):
        cart_id = request.query_params.get("cart_id")
        product_id = request.query_params.get("product_id")
        new_quantity = request.data.get("quantity")

        try:
            cart_item = CartItems.objects.get(cart__id=cart_id, product__id=product_id)
        except CartItems.DoesNotExist:
            return Response(
                {"detail": _("Cart item not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        if new_quantity is not None:
            try:
                new_quantity = int(new_quantity)
                if new_quantity <= 0:
                    raise ValueError("Quantity must be a positive integer.")
            except ValueError:
                return Response(
                    {"detail": _("Invalid quantity value.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the quantity of each cart item individually
            # for cart_item in cart_items:
            cart_item.quantity = new_quantity
            cart_item.save()

            serializer = self.get_serializer(cart_item)

            return Response(
                {"detail": _("Quantity updated successfully")},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"detail": _("Quantity is required for update.")},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CartItemDeleteView(generics.DestroyAPIView):
    serializer_class = CartItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def destroy(self, request, *args, **kwargs):
        # cart_id = request.query_params.get("cart_id")
        customer_id = request.user.customer.id
        product_id = request.data.get("product_id")
        purchase_type = request.data.get("purchase_type")

        try:
            cart = Cart.objects.get(customer=customer_id)

        except Cart.DoesNotExist:

            return Response(
                {
                    "detail": _("Cart not found"),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            cart_item = CartItems.objects.get(
                cart=cart, product__id=product_id, purchase_type=purchase_type
            )
            cart_item.delete()
            return Response(
                {"detail": _("Cart item deleted.")}, status=status.HTTP_204_NO_CONTENT
            )
        except CartItems.DoesNotExist:
            return Response(
                {"detail": _("Cart item not found.")}, status=status.HTTP_404_NOT_FOUND
            )


# wish list views


class WishListCreateView(generics.CreateAPIView):
    serializer_class = WishListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("Wishlist created successfully")},
            status=status.HTTP_201_CREATED,
        )


class WishListListView(generics.ListAPIView):
    queryset = Wishlist.objects.all()
    serializer_class = WishListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]
    pagination_class = StandardResultsSetPagination


class CustomerWishListRetrieveView(generics.RetrieveAPIView):
    serializer_class = WishListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def get_object(self):
        # customer_id = self.request.query_params.get("customer_id")
        customer_id = self.request.user.customer.id
        customer = get_object_or_404(Customer, id=customer_id)
        wishlist = get_object_or_404(Wishlist, customer=customer)
        return wishlist


class WishlistRetrieveView(generics.RetrieveAPIView):
    queryset = Wishlist.objects.all()
    serializer_class = WishListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def get_object(self):
        wishlist_id = self.request.query_params.get("wishlist_id")
        wishlist = get_object_or_404(Wishlist, id=wishlist_id)
        return wishlist


class WishlistItemCreateView(generics.CreateAPIView):
    # Add item to wishlist
    serializer_class = WishListItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def create(self, request, *args, **kwargs):
        customer_id = request.user.customer.id

        try:
            wishlist = Wishlist.objects.get(customer=customer_id)

        except Wishlist.DoesNotExist:

            return Response(
                {
                    "detail": _("Wishlist not found"),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        items = request.data  # Get the list of items from the request data

        for item_data in items:
            product_id = item_data.get("product_id")
            quantity = int(item_data.get("quantity", 1))  # Default quantity to 1
            purchase_type = item_data.get("purchase_type")

            try:
                wishlist_item = WishlistItem.objects.filter(
                    wishlist=wishlist,
                    product__id=product_id,
                    purchase_type=purchase_type,
                ).first()
                cart_item = CartItems.objects.filter(
                    cart__customer=wishlist.customer,
                    product__id=product_id,
                ).first()

                if wishlist_item:
                    return Response(
                        {"detail": _("Product already exists in the wishlist")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                elif cart_item:
                    return Response(
                        {"detail": _("Product already exists in the cart")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                else:
                    try:
                        product = Product.objects.get(id=product_id)
                    except Product.DoesNotExist:
                        return Response(
                            {"detail": _("Product not found")},
                            status=status.HTTP_404_NOT_FOUND,
                        )

                    # Create a new wishlist item with the specified quantity
                    wishlist_item = WishlistItem.objects.create(
                        wishlist=wishlist,
                        product=product,
                        quantity=quantity,
                        purchase_type=purchase_type,
                    )
            except WishlistItem.MultipleObjectsReturned:
                return Response(
                    {
                        "detail": _(
                            "Multiple wishlist items found for the same product. Contact support."
                        )
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {"detail": _("Items added to wishlist successfully")},
            status=status.HTTP_201_CREATED,
        )


# class MoveCartItemToWishlistView(generics.CreateAPIView):
##this class can move all items from cart to wishlist
#     serializer_class = WishListItemSerializer
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]  # Add your custom permission class if needed

#     def create(self, request, *args, **kwargs):
#         customer = request.user.customer

#         # Retrieve the cart associated with the logged-in customer
#         try:
#             cart = Cart.objects.get(customer=customer)
#         except Cart.DoesNotExist:
#             return Response(
#                 {"detail": _("Cart not found for customer")},
#                 status=status.HTTP_404_NOT_FOUND,
#             )

#         # Retrieve the wishlist associated with the logged-in customer, or create one if it doesn't exist
#         wishlist, created = Wishlist.objects.get_or_create(customer=customer)

#         # Move all items from cart to wishlist
#         cart_items = CartItems.objects.filter(cart=cart)

#         if not cart_items.exists():
#             return Response(
#                 {"detail": _("No items found in cart to move")},
#                 status=status.HTTP_404_NOT_FOUND,
#             )

#         for cart_item in cart_items:
#             # Check if the product is already in the wishlist
#             if WishlistItem.objects.filter(
#                 wishlist=wishlist, product=cart_item.product
#             ).exists():
#                 return Response(
#                     {"detail": _("Product already exists in the wishlist")},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             # Create a new WishlistItem instance
#             WishlistItem.objects.create(
#                 wishlist=wishlist,
#                 product=cart_item.product,
#                 quantity=cart_item.quantity,
#                 purchase_type=cart_item.purchase_type
#             )

#             # Delete the CartItem instance
#             cart_item.delete()


#         return Response(
#             {"detail": _("Items moved from cart to wishlist")},
#             status=status.HTTP_201_CREATED,
#         )
class MoveCartItemToWishlistView(generics.CreateAPIView):
    serializer_class = WishListItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]  # Add your custom permission class if needed

    def create(self, request, *args, **kwargs):
        customer = request.user.customer

        # Retrieve the cart associated with the logged-in customer
        try:
            cart = Cart.objects.get(customer=customer)
        except Cart.DoesNotExist:
            return Response(
                {"detail": _("Cart not found for customer")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Retrieve the wishlist associated with the logged-in customer, or create one if it doesn't exist
        wishlist, created = Wishlist.objects.get_or_create(customer=customer)

        # Retrieve the items to be moved from the request data
        items_to_move = request.data

        if not items_to_move:
            return Response(
                {"detail": _("No items specified to move")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        moved_items = []

        for item_data in items_to_move:
            product_id = item_data.get("product_id")
            quantity = item_data.get("quantity", 1)
            purchase_type = item_data.get("purchase_type")

            try:
                cart_item = CartItems.objects.get(
                    cart=cart, product__id=product_id, purchase_type=purchase_type
                )
            except CartItems.DoesNotExist:
                return Response(
                    {
                        "detail": _("Cart item with product ID {0} not found").format(
                            product_id
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if the product is already in the wishlist
            if WishlistItem.objects.filter(
                wishlist=wishlist,
                product=cart_item.product,
                purchase_type=purchase_type,
            ).exists():
                return Response(
                    {
                        "detail": _(
                            "Product {0} already exists in the wishlist"
                        ).format(cart_item.product.name)
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create a new WishlistItem instance
            WishlistItem.objects.create(
                wishlist=wishlist,
                product=cart_item.product,
                quantity=cart_item.quantity,
                purchase_type=cart_item.purchase_type,
            )

            # Delete the CartItem instance
            cart_item.delete()

            moved_items.append(cart_item.product.name)

        return Response(
            {
                "detail": _("Items moved from cart to wishlist: {0}").format(
                    ", ".join(moved_items)
                )
            },
            status=status.HTTP_201_CREATED,
        )


# class MoveWishlistItemToCartView(generics.CreateAPIView):
#     #this view moves all the items from wishlist to cart
#     serializer_class = CartItemSerializer
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]  # Add your custom permission class if needed

#     def create(self, request, *args, **kwargs):
#         customer = request.user.customer

#         # Retrieve the cart associated with the logged-in customer, or create one if it doesn't exist
#         cart, created = Cart.objects.get_or_create(customer=customer)

#         # Retrieve the wishlist associated with the logged-in customer
#         try:
#             wishlist = Wishlist.objects.get(customer=customer)
#         except Wishlist.DoesNotExist:
#             return Response(
#                 {"detail": _("Wishlist not found for customer")},
#                 status=status.HTTP_404_NOT_FOUND,
#             )

#         # Move all items from wishlist to cart
#         wishlist_items = WishlistItem.objects.filter(wishlist=wishlist)

#         if not wishlist_items.exists():
#             return Response(
#                 {"detail": _("No items found in wishlist to move")},
#                 status=status.HTTP_404_NOT_FOUND,
#             )

#         for wishlist_item in wishlist_items:
#             # Check if the product is already in the cart
#             if CartItems.objects.filter(cart=cart, product=wishlist_item.product).exists():
#                 return Response(
#                     {"detail": _("Product already exists in the cart")},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             # Create a new CartItem instance
#             CartItems.objects.create(
#                 cart=cart,
#                 product=wishlist_item.product,
#                 quantity=wishlist_item.quantity,
#             )

#             # Delete the WishlistItem instance
#             wishlist_item.delete()


#         return Response(
#             {"detail": _("Items moved from wishlist to cart")},
#             status=status.HTTP_201_CREATED,
#         )
class MoveWishlistItemToCartView(generics.CreateAPIView):
    serializer_class = CartItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]  # Add your custom permission class if needed

    def create(self, request, *args, **kwargs):
        customer = request.user.customer

        # Retrieve the wishlist associated with the logged-in customer
        try:
            wishlist = Wishlist.objects.get(customer=customer)
        except Wishlist.DoesNotExist:
            return Response(
                {"detail": _("Wishlist not found for customer")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Retrieve the cart associated with the logged-in customer, or create one if it doesn't exist
        cart, created = Cart.objects.get_or_create(customer=customer)

        # Retrieve the items to be moved from the request data
        items_to_move = request.data

        if not items_to_move:
            return Response(
                {"detail": _("No items specified to move")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        moved_items = []

        for item_data in items_to_move:
            product_id = item_data.get("product_id")
            quantity = item_data.get("quantity", 1)
            purchase_type = item_data.get("purchase_type")

            try:
                wishlist_item = WishlistItem.objects.get(
                    wishlist=wishlist,
                    product__id=product_id,
                    quantity=quantity,
                    purchase_type=purchase_type,
                )
            except WishlistItem.DoesNotExist:
                return Response(
                    {
                        "detail": _(
                            "Wishlist item with product ID {0} not found"
                        ).format(product_id)
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if the product is already in the cart
            if CartItems.objects.filter(
                cart=cart, product=wishlist_item.product, purchase_type=purchase_type
            ).exists():
                return Response(
                    {
                        "detail": _("Product {0} already exists in the cart").format(
                            wishlist_item.product.name
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create a new CartItem instance
            CartItems.objects.create(
                cart=cart,
                product=wishlist_item.product,
                quantity=wishlist_item.quantity,
                purchase_type=wishlist_item.purchase_type,
            )

            # Delete the WishlistItem instance
            wishlist_item.delete()

            moved_items.append(wishlist_item.product.name)

        return Response(
            {
                "detail": _("Items moved from wishlist to cart: {0}").format(
                    ", ".join(moved_items)
                )
            },
            status=status.HTTP_201_CREATED,
        )


class WishlistItemUpdateQuantityView(generics.UpdateAPIView):
    queryset = WishlistItem.objects.all()
    serializer_class = WishListItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def update(self, request, *args, **kwargs):
        wishlist_id = request.query_params.get("wishlist_id")
        product_id = request.query_params.get("product_id")
        new_quantity = request.data.get("quantity")

        try:
            wishlist_item = WishlistItem.objects.get(
                wishlist__id=wishlist_id, product__id=product_id
            )
        except WishlistItem.DoesNotExist:
            return Response(
                {"detail": _("Wishlist item not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if new_quantity is not None:
            try:
                new_quantity = int(new_quantity)
                if new_quantity <= 0:
                    raise ValueError("Quantity must be a positive integer.")
            except ValueError:
                return Response(
                    {"detail": _("Invalid quantity value.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the quantity of each wishlist item individually
            wishlist_item.quantity = new_quantity
            wishlist_item.save()

            serializer = self.get_serializer(wishlist_item)

            return Response(
                {"detail": _("Quantity updated successfully")},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"detail": _("Quantity is required for update.")},
                status=status.HTTP_400_BAD_REQUEST,
            )


class WishlistItemDeleteView(generics.DestroyAPIView):
    serializer_class = WishListItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def destroy(self, request, *args, **kwargs):
        # wishlist_id = request.query_params.get("wishlist_id")
        customer = request.user.customer
        product_id = request.data.get("product_id")
        purchase_type = request.data.get("purchase_type")
        # Retrieve the wishlist associated with the logged-in customer
        """
        try:
            cart = Cart.objects.get(customer=customer_id)

        except Cart.DoesNotExist:

            return Response(
                {
                    "detail": _("Cart not found"),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            cart_item = CartItems.objects.get(
                cart=cart, product__id=product_id, purchase_type=purchase_type
            )
            cart_item.delete()
            return Response(
                {"detail": _("Cart item deleted.")}, status=status.HTTP_204_NO_CONTENT
            )
        except CartItems.DoesNotExist:
            return Response(
                {"detail": _("Cart item not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        """
        try:
            wishlist = Wishlist.objects.get(customer=customer)
        except Wishlist.DoesNotExist:
            return Response(
                {"detail": _("Wishlist not found for customer")},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            wishlist_item = WishlistItem.objects.get(
                wishlist=wishlist,
                product__id=product_id,
                purchase_type=purchase_type,
            )
            wishlist_item.delete()
            return Response(
                {"detail": _("Wishlist item deleted.")},
                status=status.HTTP_204_NO_CONTENT,
            )
        except WishlistItem.DoesNotExist:
            return Response(
                {"detail": _("Wishlist item not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )
