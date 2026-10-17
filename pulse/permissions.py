from rest_framework.permissions import BasePermission
from .models import UserProfile


class IsAdminUser(BasePermission):
    """Allows access only to users with role == ADMIN."""
    message = "Admin access required."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role == UserProfile.Role.ADMIN
        )
