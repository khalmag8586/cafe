from django.contrib.auth.models import Permission, Group
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.permissions_api.serializers import (
    PermissionSerializer,
    GroupSerializer,
    PermissionDialogSerializer,
    GroupDialogSerializer,
)
from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import HasPermissionOrInGroupWithPermission

from user.models import User
from user.serializers import UserSerializer


class PermissionListView(generics.ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "view_permission"

    pagination_class = StandardResultsSetPagination


class PermissionDialogView(generics.ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "view_permission"



class AssignPermissionsToGroupView(generics.CreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "add_permission"


    def create(self, request, *args, **kwargs):
        group_id = request.query_params.get("group_id")
        permission_codenames = request.data.get("codename", [])

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {"detail": _("Group not found")}, status=status.HTTP_404_NOT_FOUND
            )

        permissions = Permission.objects.filter(codename__in=permission_codenames)
        group.permissions.set(permissions)

        return Response(
            {"detail": _("Permission(s) assigned to group successfully")},
            status=status.HTTP_201_CREATED,
        )


class AssignPermissionsToUserView(generics.CreateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "add_permission"


    def create(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        permission_codenames = request.data.get("codename", [])

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": _("User not found")}, status=status.HTTP_404_NOT_FOUND
            )

        permissions = Permission.objects.filter(codename__in=permission_codenames)
        user.user_permissions.add(*permissions)

        return Response(
            {"detail": _("Permission(s) assigned to user successfully")},
            status=status.HTTP_201_CREATED,
        )


class RemovePermissionsFromGroupView(generics.UpdateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "change_group"


    def update(self, request, *args, **kwargs):
        group_id = request.query_params.get("group_id")
        permission_codenames = request.data.get("codename", [])

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {"detail": _("Group not found")}, status=status.HTTP_404_NOT_FOUND
            )

        permissions = Permission.objects.filter(codename__in=permission_codenames)
        group.permissions.remove(*permissions)

        return Response(
            {"detail": _("Permission(s) removed from group successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class RemovePermissionsFromUserView(generics.UpdateAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "change_permission"


    def update(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        permission_codenames = request.data.get("codename", [])

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": _("User not found")}, status=status.HTTP_404_NOT_FOUND
            )

        permissions = Permission.objects.filter(codename__in=permission_codenames)
        user.user_permissions.remove(*permissions)

        return Response(
            {"detail": _("Permission(s) removed from user successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


# Groups Views
class GroupListView(generics.ListAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    # permission_codename = "view_group"
    permission_codename = "view_group"

    pagination_class = StandardResultsSetPagination

class GroupRetrieveView(generics.RetrieveAPIView):
    serializer_class=GroupSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "view_group"
    lookup_field = "id"
    def get_object(self):
        group_id = self.request.query_params.get("group_id")
        group = get_object_or_404(Group, id=group_id)
        return group

class GroupCreateView(generics.CreateAPIView):
    serializer_class = GroupSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "add_group"


    def create(self, request, *args, **kwargs):
        group_serializer = self.get_serializer(data=request.data)
        group_serializer.is_valid(raise_exception=True)
        group = group_serializer.save()

        permission_codenames = request.data.get("permissions", [])
        if permission_codenames:
            permissions = Permission.objects.filter(codename__in=permission_codenames)

            # Assign permissions to the group
            group.permissions.add(*permissions)

        return Response(
            {"detail": _("Group created successfully")}, status=status.HTTP_201_CREATED
        )


class GroupUpdateView(generics.UpdateAPIView):
    serializer_class = GroupSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "change_group"

    lookup_field = "group_id"

    def get_object(self):
        group_id = self.request.query_params.get("group_id")
        group = get_object_or_404(Group, id=group_id)
        return group

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Group Updated successfully")}, status=status.HTTP_200_OK
        )
class GroupUpdatePermissionsView(generics.UpdateAPIView):
    serializer_class = GroupSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "change_group"

    def get_object(self):
        group_id = self.request.query_params.get("group_id")
        group = get_object_or_404(Group, id=group_id)
        return group

    def update(self, request, *args, **kwargs):
        # Get the group object using get_object
        group = self.get_object()

        # Get the permissions from the request body
        permission_codenames = request.data.get("permissions", [])
        if permission_codenames:
            permissions = Permission.objects.filter(codename__in=permission_codenames)

            # Clear existing permissions and assign new ones
            group.permissions.set(permissions)

        return Response(
            {"detail": _("Group permissions updated successfully.")},
            status=status.HTTP_200_OK,
        )

class GroupDeleteView(generics.DestroyAPIView):
    serializer_class = GroupSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "delete_group"


    def delete(self, request, *args, **kwargs):

        group_ids = request.data.get("group_id", [])

        if not group_ids:
            return Response(
                {"detail": _("No group IDs provided")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for group_id in group_ids:
            group = get_object_or_404(Group, id=group_id)
            group.delete()

        return Response(
            {"detail": _("Groups permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class GroupDialogView(generics.ListAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "view_group"



class AssignUserToGroupView(generics.UpdateAPIView):
    serializer_class = UserSerializer  # Replace with your User serializer
    authentication_classes = [JWTAuthentication]  # Add your authentication classes
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "change_group"


  # Add your permission classes

    def update(self, request, *args, **kwargs):
        user_id = self.request.query_params.get("user_id")
        group_id = request.data.get("group_id")

        try:
            user = User.objects.get(id=user_id)
            group = Group.objects.get(id=group_id)
        except User.DoesNotExist:
            return Response(
                {"detail": _("User not found")}, status=status.HTTP_404_NOT_FOUND
            )
        except Group.DoesNotExist:
            return Response(
                {"detail": _("Group not found")}, status=status.HTTP_404_NOT_FOUND
            )

        user.groups.add(group)
        user.save()

        return Response(
            {"detail": _("User assigned to group successfully")},
            status=status.HTTP_200_OK,
        )


class AssignManyUsersToGroupView(generics.UpdateAPIView):
    serializer_class = UserSerializer  # Use your User serializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "change_group"


    def update(self, request, *args, **kwargs):
        group_id = request.data.get("group_id")
        user_ids = request.data.get("user_id", [])

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {"detail": _("Group not found")}, status=status.HTTP_404_NOT_FOUND
            )

        users = User.objects.filter(id__in=user_ids)
        users_count = users.count()

        if users_count != len(user_ids):
            return Response(
                {"detail": _("One or more users not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        for user in users:
            user.groups.add(group)
            user.save()

        return Response(
            {"detail": _("Users assigned to group successfully")},
            status=status.HTTP_200_OK,
        )


class RemoveUserFromGroupView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()  # This queryset can be customized based on your needs
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "change_group"


    def update(self, request, *args, **kwargs):
        user_id = self.request.query_params.get("user_id")
        group_id = request.data.get("group_id")

        try:
            user = User.objects.get(id=user_id)
            group = Group.objects.get(id=group_id)
        except User.DoesNotExist:
            return Response(
                {"detail": _("User not found")}, status=status.HTTP_404_NOT_FOUND
            )
        except Group.DoesNotExist:
            return Response(
                {"detail": _("Group not found")}, status=status.HTTP_404_NOT_FOUND
            )
        user.groups.remove(group)
        user.save()

        return Response(
            {"detail": _("User removed from group successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class RemoveManyUsersFromGroupView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "change_group"


    def update(self, request, *args, **kwargs):
        group_id = request.data.get("group_id")
        user_ids = request.data.get("user_id", [])

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {"detail": _("Group not found")}, status=status.HTTP_404_NOT_FOUND
            )

        users = User.objects.filter(id__in=user_ids)
        users_count = users.count()

        if users_count != len(user_ids):
            return Response(
                {"detail": _("One or more users not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        for user in users:
            user.groups.remove(group)
            user.save()

        return Response(
            {"detail": _("Users removed from group successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )
