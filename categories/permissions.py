from rest_framework import permissions
from teams.models import TeamMembership
from django.shortcuts import get_object_or_404
from .models import Project

class ProjectPermission(permissions.BasePermission):
    """
    Grant access if:
    - user is owner of the project
    - OR user is an active member of the project's team (if project.team is set)
    """

    def has_object_permission(self, request, view, obj: Project):
        # owner always allowed
        if obj.owner_id == request.user.id:
            return True

        # if project assigned to a team, check active membership
        if obj.team_id:
            return TeamMembership.objects.filter(
                team=obj.team,
                user=request.user,
                status=TeamMembership.Status.ACTIVE
            ).exists()

        return False
