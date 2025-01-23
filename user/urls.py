from django.urls import path
from user.views import (
    CreateUserView,
    UploadUserPhotoView,
    UploadUserCoverView,
    UserListView,
    UserRetrieveView,
    ManagerUserView,
    DeletedUserView,
    UserDeleteTemporaryView,
    UserRestoreView,
    UserUpdateView,
    UserDeleteView,
    LoginView,
    UserDialogView,
    UserGenderDialogView,
    forgot_password,
    ExportUsersToCSV,
)

app_name = "user"
urlpatterns = [
    path("create_user/", CreateUserView.as_view(), name="create-user"),
    path("login/", LoginView.as_view(), name="login"),
    path("upload_photo/", UploadUserPhotoView.as_view(), name="upload-photo"),
    path("upload_cover/", UploadUserCoverView.as_view(), name="upload-cover"),
    path("me/", ManagerUserView.as_view(), name="me"),
    path("user_list/", UserListView.as_view(), name="user-list"),
    path("user_deleted_list/", DeletedUserView.as_view(), name="user-deleted-list"),
    path("user_retrieve/", UserRetrieveView.as_view(), name="user-retrieve"),
    path("user_update/", UserUpdateView.as_view(), name="user-update-by-admin"),
    path(
        "user_temp_delete/", UserDeleteTemporaryView.as_view(), name="user-temp-delete"
    ),
    path("user_restore/", UserRestoreView.as_view(), name="user-restore"),
    path("user_delete/", UserDeleteView.as_view(), name="user-delete"),
    path("user_dialog/", UserDialogView.as_view(), name="user-dialog"),
    path(
        "user_gender_dialog/", UserGenderDialogView.as_view(), name="user-gender-dialog"
    ),
    path("forgot_password/", forgot_password, name="forgot_password"),
    path("employee_export_csv/", ExportUsersToCSV.as_view(), name="export-employees"),
]
