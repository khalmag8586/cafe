from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

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

from apps.category.models import Category, CategoryImages
from apps.category.serializers import (
    NestedCategorySerializer,
    CategorySerializer,
    CategoryActiveSerializer,
    CategoryDeleteSerializer,
    CategoryDialogSerializer,
    ParentCategorySerializer,
    CategoryImageSerializer,
)
from apps.category.filters import CategoryFilter

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import HasPermissionOrInGroupWithPermission


# category Views
class CategoryCreateView(generics.CreateAPIView):
    serializer_class = CategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.add_category"

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.action = self.request.method.lower()

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {"detail": _("Category created successfully")},
            status=status.HTTP_201_CREATED,
        )

    def get_serializer_class(self):
        if self.action == "list":
            return CategorySerializer
        elif self.action == "upload_image":
            return CategoryImageSerializer
        return self.serializer_class

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = CategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.view_category"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CategoryFilter
    search_fields = ["name", "name_ar", "slug", "parent"]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


class DeletedCategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_deleted=True).order_by("-created_at")
    serializer_class = CategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.view_category"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CategoryFilter
    search_fields = ["name", "name_ar", "slug", "parent"]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


class CategoryRetrieveView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "id"  # Use 'id' as the lookup field
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.view_category"

    def get_object(self):
        category_id = self.request.query_params.get("category_id")
        category = get_object_or_404(Category, id=category_id)
        return category


class ChildrenCategoriesView(generics.ListAPIView):
    serializer_class = NestedCategorySerializer  # Use your Category serializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.view_category"
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        category_id = self.request.query_params.get("category_id")
        parent_category = Category.objects.filter(id=category_id).first()

        if parent_category:
            return Category.objects.filter(parent=parent_category)
        else:
            return Category.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        # serializer = self.serializer_class(queryset, many=True)
        serializer = self.serializer_class(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class ActiveCategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_deleted=False, is_active=True).order_by(
        "-created_at"
    )
    serializer_class = CategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.view_category"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CategoryFilter
    search_fields = ["name", "name_ar", "slug", "parent"]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


class CategoryChangeActiveView(generics.UpdateAPIView):
    serializer_class = CategoryActiveSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.change_category"

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        category_ids = request.data.get("category_id", [])
        partial = kwargs.pop("partial", False)
        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {"detail": _("'is_active' field is required")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for category_id in category_ids:
            instance = get_object_or_404(Category, id=category_id)
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
        return Response(
            {"detail": _("Category status changed successfully")},
            status=status.HTTP_200_OK,
        )


class CategoryUpdateView(generics.UpdateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "category_id"
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.change_category"

    def get_object(self):
        category_id = self.request.query_params.get("category_id")
        category = get_object_or_404(Category, id=category_id)
        return category

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Category updated successfully")}, status=status.HTTP_200_OK
        )


class CategoryImagesUpdateView(generics.UpdateAPIView):
    serializer_class = CategoryImageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.change_category"
    queryset = CategoryImages.objects.all()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def patch(self, request, *args, **kwargs):
        image_id = request.data.get(
            "image_id"
        )  # Get the image ID from the request body
        if not image_id:
            return Response(
                {"detail": _("Image ID is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            instance = self.get_queryset().get(id=image_id)
        except CategoryImages.DoesNotExist:
            return Response(
                {"detail": _("Image not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # return Response(serializer.data)
        return Response(
            {"detail": _("Category Image updated successfully")},
            status=status.HTTP_200_OK,
        )


class CategoryImagesDeleteView(generics.DestroyAPIView):
    serializer_class = CategoryImageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.delete_categoryimage"
    queryset = CategoryImages.objects.all()

    def delete(self, request, *args, **kwargs):
        image_ids = request.data.get("image_id", [])
        for image_id in image_ids:
            instance = get_object_or_404(CategoryImages, id=image_id)
            instance.delete()
        return Response(
            {"detail": _("Category image deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class CategoryDeleteTemporaryView(generics.UpdateAPIView):
    serializer_class = CategoryDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.change_category"

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        category_ids = request.data.get("category_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == False:
            return Response(
                {"detail": _("These Categories are not deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for category_id in category_ids:
            instance = get_object_or_404(Category, id=category_id)
            if instance.is_deleted:
                return Response(
                    {
                        "detail": _(
                            "Category with ID {} is already temp deleted".format(
                                category_id
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
            {"detail": _("Categories temp deleted successfully")},
            status=status.HTTP_200_OK,
        )


class CategoryRestoreView(generics.RetrieveUpdateAPIView):

    serializer_class = CategoryDeleteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "category.change_category"

    def update(self, request, *args, **kwargs):
        category_ids = request.data.get("category_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == True:
            return Response(
                {"detail": _("Categories are already deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for category_id in category_ids:
            instance = get_object_or_404(Category, id=category_id)
            if instance.is_deleted == False:
                return Response(
                    {
                        "detail": _(
                            "Category with ID {} is not deleted".format(category_id)
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
            {"detail": _("Categories restored successfully")}, status=status.HTTP_200_OK
        )


class CategoryDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename='category.delete_category'

    def delete(self, request, *args, **kwargs):
        category_ids = request.data.get("category_id", [])
        for category_id in category_ids:
            instance = get_object_or_404(Category, id=category_id)
            instance.delete()

        return Response(
            {"detail": _("Category permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


# dialog views
class CategoryDialogView(generics.ListAPIView):
    queryset = Category.objects.filter(is_deleted=False)
    serializer_class = CategoryDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ParentCategoryDialog(generics.ListAPIView):
    queryset = Category.objects.filter(parent__isnull=True, is_deleted=False).order_by(
        "-created_at"
    )
    serializer_class = NestedCategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
