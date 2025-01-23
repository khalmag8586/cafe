from django.urls import path

from apps.category.views import (
    CategoryCreateView,
    CategoryListView,
    CategoryRetrieveView,
    DeletedCategoryListView,
    ChildrenCategoriesView,
    ActiveCategoryListView,
    CategoryChangeActiveView,
    CategoryUpdateView,
    CategoryImagesUpdateView,CategoryImagesDeleteView,
    CategoryDeleteTemporaryView,
    CategoryRestoreView,
    CategoryDeleteView,
    # dialogs
    CategoryDialogView,
    ParentCategoryDialog,
)

app_name = "category"
urlpatterns = [
    path("category_create/", CategoryCreateView.as_view(), name="category-create"),
    path("category_list/", CategoryListView.as_view(), name="category-list"),
    path(
        "deleted_category_list/",
        DeletedCategoryListView.as_view(),
        name="deleted-category-list",
    ),
    path(
        "category_retrieve/", CategoryRetrieveView.as_view(), name="category_retrieve"
    ),
    path(
        "category_children_list/",
        ChildrenCategoriesView.as_view(),
        name="category-children",
    ),
    path(
        "category_active_list/",
        ActiveCategoryListView.as_view(),
        name="active-categories-list",
    ),
    path(
        "change_category_status/",
        CategoryChangeActiveView.as_view(),
        name="change-category-status",
    ),
    path(
        "category_update/",
        CategoryUpdateView.as_view(),
        name="category-update",
    ),
    path('category_image_update/',CategoryImagesUpdateView.as_view(),name='category-images-update'),
    path('category_image_delete/',CategoryImagesDeleteView.as_view(),name='category-images-delete'),
    path(
        "category_temp_delete/",
        CategoryDeleteTemporaryView.as_view(),
        name="category-temp-delete",
    ),
    path("category_restore/", CategoryRestoreView.as_view(), name="category_restore"),
    path("category_delete/", CategoryDeleteView.as_view(), name="category-delete"),
    # dialogs
    path("category_dialog/", CategoryDialogView.as_view(), name="category-dialog"),
    path("parent_dialog/", ParentCategoryDialog.as_view(), name="parent-dialog"),
]
