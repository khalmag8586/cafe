from rest_framework.permissions import BasePermission


class CustomerPermission(BasePermission):
    """
    Custom permission class to restrict access to most APIs for customers.
    """

    def has_permission(self, request, view):

        user=request.user
        if user.is_staff:
            return True
        elif not user.is_staff:
            return False

        return False

class OnlyCustomer(BasePermission):
    """
    Custom permission class to restrict access to APIs for only customers.
    """

    def has_permission(self, request, view):

        user=request.user
        if not user.is_staff:
            return True
        elif  user.is_staff:
            return False

        return False
