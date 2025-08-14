from rest_framework import permissions
from .models import TeamMembership

class IsTeamOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return TeamMembership.objects.filter(
            team=obj,
            user=request.user,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE
        ).exists()

class IsTeamAdminOrOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return TeamMembership.objects.filter(
            team=obj,
            user=request.user,
            role__in=[TeamMembership.Role.ADMIN, TeamMembership.Role.OWNER],
            status=TeamMembership.Status.ACTIVE
        ).exists()

class IsTeamMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return TeamMembership.objects.filter(
            team=obj,
            user=request.user,
            status=TeamMembership.Status.ACTIVE
        ).exists()
