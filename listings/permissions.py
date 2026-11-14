from rest_framework import permissions


def is_staff_user(user):
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def is_super_admin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


class IsStaffOrAdmin(permissions.BasePermission):
    """Staff (moderators) and the main admin."""

    def has_permission(self, request, view):
        return is_staff_user(request.user)


class IsSuperAdmin(permissions.BasePermission):
    """Only the main admin account (Django superuser)."""

    def has_permission(self, request, view):
        return is_super_admin(request.user)


class ReadOnlyOrSuperAdmin(permissions.BasePermission):
    """Anyone can read; only the main admin can create / edit / delete."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_super_admin(request.user)


class ReadOnlyOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_staff_user(request.user)


class IsOwnerOrStaff(permissions.BasePermission):
    """Logged-in users may edit/delete only their own object; staff may edit any."""

    owner_field = 'owner'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if is_staff_user(request.user):
            return True
        owner = getattr(obj, 'owner', None) or getattr(obj, 'user', None)
        return owner == request.user
