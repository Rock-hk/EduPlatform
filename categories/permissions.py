from rest_framework import permissions


class ProjectPermission(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if obj.owner == request.user:
            return True
        if obj.team:
            return obj.team.memberships.filter(user=request.user, status='active').exists()
        return False