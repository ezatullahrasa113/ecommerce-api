from rest_framework.permissions import BasePermission


class IsStaffOrAdmin(BasePermission):
    """
    Allows access only to staff users or superusers.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_staff
                or request.user.is_superuser
            )
        )



class ReadOnlyOrStaff(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_staff
                or request.user.is_superuser
            )
        )



class IsOwnerOrStaff(BasePermission):
    """
    Allows access to an object if:
    - the user is the owner, OR
    - the user is staff/admin.
    """

    def has_object_permission(self, request, view, obj):

        if request.user.is_staff or request.user.is_superuser:
            return True

        return obj.user == request.user

