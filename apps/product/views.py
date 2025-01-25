from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import AnonymousUser
from django.db.models import Avg

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import (
    generics,
    status,
)
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.product.models import Product
from apps.product.serializers import (
    ProductSerializer,
    ProductImageOnlySerializer,
    ProductActiveSerializer,
    ProductDeleteSerializer,
    ProductDialogSerializer,
    ProductCategoryBulkSerializer,
)
from apps.product.filters import ProductFilter
from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import  HasPermissionOrInGroupWithPermission

from apps.category.models import Category


# Product views
class ProductCreateView(generics.CreateAPIView):
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.add_product'


    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.action = self.request.method.lower()

    def perform_create(self, serializer):
        category_id = self.request.data.get("category")
        if category_id:
            category_ids = [category_id]  # Convert single value to list
        else:
            category_ids = []  # Empty list if no category ID is provided

        product = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        product.category.set(category_ids)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Get the ID of the created object
        created_object_id = serializer.instance.id

        return Response(
            {"id": created_object_id, "detail": _("Product created successfully")},
            status=status.HTTP_201_CREATED,
        )

    # def get_serializer_class(self):
    #     """Return the serializer class for request."""
    #     if self.action == "list":
    #         return ProductSerializer

    #     return self.serializer_class

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductCategoryBulkCreateView(generics.CreateAPIView):
    serializer_class = ProductCategoryBulkSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.add_product'


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_ids = serializer.validated_data.get("product_id", [])
            category_ids = serializer.validated_data.get("category_id", [])

            for product_id in product_ids:
                product = Product.objects.get(id=product_id)
                for category_id in category_ids:
                    category = Category.objects.get(id=category_id)
                    product.category.add(category)

            return Response(
                {"detail": _("Products added to categories successfully.")},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductCategoryBulkRemoveView(generics.CreateAPIView):
    serializer_class = ProductCategoryBulkSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.add_product'


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_ids = serializer.validated_data.get("product_id", [])
            category_ids = serializer.validated_data.get("category_id", [])
            for product_id in product_ids:
                product = Product.objects.get(id=product_id)
                for category_id in category_ids:
                    category = Category.objects.get(id=category_id)
                    product.category.remove(category)
            return Response(
                {"detail": _("Products removed from categories successfully.")},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductCategoryBulkUpdateView(generics.UpdateAPIView):
    serializer_class = ProductCategoryBulkSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.change_product'

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_ids = serializer.validated_data.get("product_id", [])
            category_ids = serializer.validated_data.get("category_id", [])

            for product_id in product_ids:
                product = get_object_or_404(Product, id=product_id)
                product.category.clear()  # Clear existing categories
                for category_id in category_ids:
                    category = get_object_or_404(Category, id=category_id)
                    product.category.add(category)

            return Response(
                {"detail": _("Product-category relationship updated successfully.")},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.view_product'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "name_ar", "description", "slug"]
    ordering_fields = [
        "name",
        "-name",
    ]




class DeletedProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_deleted=True).order_by("-created_at")
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.view_product'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "name_ar", "description", "slug"]
    ordering_fields = [
        "price_pdf",
        "-price_pdf",
        "price_sib",
        "-price_sib",
        "name",
        "-name",
    ]


class ProductByCategoryView(generics.ListAPIView):
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.view_product'
    def get_queryset(self):
        category_id = self.request.query_params.get("category_id")
        try:
            queryset = Product.objects.filter(category=category_id)
        except Product.DoesNotExist:
            return Response(
                {"detail": _("Category is not found")}, status=status.HTTP_404_NOT_FOUND
            )
        return queryset


class ProductRetrieveView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.view_product'
    lookup_field = "id"

    def get_object(self):
        product_id = self.request.query_params.get("product_id")
        product = get_object_or_404(Product, id=product_id)
        return product


class ProductActiveListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True, is_deleted=False).order_by(
        "-created_at"
    )
    serializer_class = ProductImageOnlySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.view_product'
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description", "slug", "name_ar"]
    ordering_fields = [

        "name",
        "-name",
    ]

    


class ProductActiveRetrieveView(generics.RetrieveAPIView):
    serializer_class = ProductImageOnlySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.view_product'
    lookup_field = "id"

    def get_object(self):
        product_id = self.request.query_params.get("product_id")
        product = get_object_or_404(Product, id=product_id)
        return product




class ProductChangeActiveView(generics.UpdateAPIView):
    serializer_class = ProductActiveSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.change_product'

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        product_ids = request.data.get("product_id", [])
        partial = kwargs.pop("partial", False)
        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {"detail": _("'is_active' field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for product_id in product_ids:
            instance = get_object_or_404(Product, id=product_id)
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
        return Response(
            {"detail": _("Product status changed successfully")},
            status=status.HTTP_200_OK,
        )


class ProductUpdateView(generics.UpdateAPIView):
    serializer_class = ProductSerializer
    lookup_field = "id"
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.change_product'

    def get_object(self):
        product_id = self.request.query_params.get("product_id")
        product = get_object_or_404(Product, id=product_id)
        return product

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Product updated successfully")}, status=status.HTTP_200_OK
        )


class ProductDeleteTemporaryView(generics.UpdateAPIView):
    serializer_class = ProductDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.change_product'

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        product_ids = request.data.get("product_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == False:
            return Response(
                {"detail": _("These products are not deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for product_id in product_ids:
            instance = get_object_or_404(Product, id=product_id)
            if instance.is_deleted:
                return Response(
                    {
                        "detail": _(
                            "Product with ID {} is already temp deleted".format(
                                product_id
                            )
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            instance.is_active = False
            instance.save()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        return Response(
            {"detail": _("Products temp deleted successfully")},
            status=status.HTTP_200_OK,
        )


class ProductRestoreView(generics.RetrieveUpdateAPIView):

    serializer_class = ProductDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.change_product'

    def update(self, request, *args, **kwargs):
        product_ids = request.data.get("product_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == True:
            return Response(
                {"detail": _("Products are already deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for product_id in product_ids:
            instance = get_object_or_404(Product, id=product_id)
            if instance.is_deleted == False:
                return Response(
                    {
                        "detail": _(
                            "Product with ID {} is not deleted".format(product_id)
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            instance.is_active = True

            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        return Response(
            {"detail": _("Products restored successfully")}, status=status.HTTP_200_OK
        )


class ProductDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='product.delete_product'

    def delete(self, request, *args, **kwargs):
        product_ids = request.data.get("product_id", [])
        for product_id in product_ids:
            instance = get_object_or_404(Product, id=product_id)
            instance.delete()

        return Response(
            {"detail": _("Product permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


# dialog views
class ProductDialogView(generics.ListAPIView):
    queryset = Product.objects.filter(is_deleted=False)
    serializer_class = ProductDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
