from rest_framework import permissions
from .models import TeamMembership
from accounts.models import User

class IsTeamOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return TeamMembership.objects.filter(
            team=obj,
            user=request.user,
            role=User.Roles.SYSTEM_ADMIN,  
            status=TeamMembership.Status.ACTIVE
        ).exists()


class IsTeamAdminOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return TeamMembership.objects.filter(
            team=obj,
            user=request.user,
            role__in=[User.Roles.MANAGER, User.Roles.SYSTEM_ADMIN],
            status=TeamMembership.Status.ACTIVE
        ).exists()


class IsTeamMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return TeamMembership.objects.filter(
            team=obj,
            user=request.user,
            status=TeamMembership.Status.ACTIVE
        ).exists()
