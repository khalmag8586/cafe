from django.urls import path
from apps.permissions_api.views import (
    PermissionListView,
    PermissionDialogView,
    AssignPermissionsToGroupView,
    AssignPermissionsToUserView,
    RemovePermissionsFromGroupView,
    RemovePermissionsFromUserView,
    # Groups Views
    GroupListView,
    GroupCreateView,
    GroupUpdateView,
    GroupDeleteView,
    AssignUserToGroupView,
    AssignManyUsersToGroupView,
    RemoveUserFromGroupView,
    RemoveManyUsersFromGroupView,
    GroupDialogView,
)


app_name = "permissions_api"
urlpatterns = [
    path("permissions_list/", PermissionListView.as_view(), name="permission-list"),
    path(
        "permissions_dialog/", PermissionDialogView.as_view(), name="permission-dialog"
    ),
    path(
        "assign_permissions_to_group/",
        AssignPermissionsToGroupView.as_view(),
        name="assign-permissions-to-group",
    ),
    path(
        "assign_permissions_to_user/",
        AssignPermissionsToUserView.as_view(),
        name="assign-permissions-to-user",
    ),
    path(
        "remove_permissions_from_group/",
        RemovePermissionsFromGroupView.as_view(),
        name="remove-permissions-from-group",
    ),
    path(
        "remove_permissions_from_user/",
        RemovePermissionsFromUserView.as_view(),
        name="remove-permissions-from-user",
    ),
    # group urls
    path("group_create/", GroupCreateView.as_view(), name="group-create"),
    path("group_list/", GroupListView.as_view(), name="groups-list"),
    path("group_update/", GroupUpdateView.as_view(), name="group-update"),
    path("group_delete/", GroupDeleteView.as_view(), name="group-delete"),
    path("group_dialog/", GroupDialogView.as_view(), name="group-dialog"),
    path(
        "assign_user_to_group/",
        AssignUserToGroupView.as_view(),
        name="assign-user-to-group",
    ),
    path(
        "assign_many_users_to_group/",
        AssignManyUsersToGroupView.as_view(),
        name="assign-many-users-to-group",
    ),
    path(
        "remove_user_from_group/",
        RemoveUserFromGroupView.as_view(),
        name="remove-user-from-group",
    ),
    path(
        "remove_many_users_from_group/",
        RemoveManyUsersFromGroupView.as_view(),
        name="remove-many-users-from-group",
    ),
]
