from rest_framework.permissions import BasePermission

class HasPermissionOrInGroupWithPermission(BasePermission):
    """
    Custom permission to check if the user has the required permission or
    if the user is in a group that has the required permission.
    """

    def has_permission(self, request, view):
        # Get the required permission codename from the view
        permission_codename = getattr(view, 'permission_codename', None)

        if permission_codename is None:
            # If no permission_codename is set on the view, deny permission
            return False

        # 1. Check if the user has the permission directly
        if request.user.has_perm(permission_codename):
            return True

        # 2. Check if the user belongs to a group with the required permission
        for group in request.user.groups.all():
            if group.permissions.filter(codename=permission_codename).exists():
                return True

        # If neither condition is met, deny permission
        return False
