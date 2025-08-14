from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Team, TeamMembership
from .serializers import TeamSerializer, TeamMembershipSerializer
from .permissions import IsTeamOwner, IsTeamAdminOrOwner, IsTeamMember

User = get_user_model()

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all().prefetch_related("memberships__user")
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="invite", permission_classes=[permissions.IsAuthenticated, IsTeamAdminOrOwner])
    def invite(self, request, pk=None):
        team = self.get_object()
        email = request.data.get("email")
        role = request.data.get("role", TeamMembership.Role.MEMBER)
        if not email:
            return Response({"detail": "email required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "user not found"}, status=status.HTTP_404_NOT_FOUND)
        membership, created = TeamMembership.objects.get_or_create(
            team=team,
            user=user,
            defaults={"role": role, "status": TeamMembership.Status.PENDING, "invited_by": request.user}
        )
        if not created:
            return Response({"detail": "user already invited or member"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TeamMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="remove-member", permission_classes=[permissions.IsAuthenticated, IsTeamAdminOrOwner])
    def remove_member(self, request, pk=None):
        team = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id required"}, status=status.HTTP_400_BAD_REQUEST)
        membership = get_object_or_404(TeamMembership, team=team, user__id=user_id)
        if membership.role == TeamMembership.Role.OWNER:
            return Response({"detail": "cannot remove owner"}, status=status.HTTP_403_FORBIDDEN)
        membership.status = TeamMembership.Status.REMOVED
        membership.save()
        return Response({"detail": "member removed"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="assign-role", permission_classes=[permissions.IsAuthenticated, IsTeamOwner])
    def assign_role(self, request, pk=None):
        team = self.get_object()
        user_id = request.data.get("user_id")
        role = request.data.get("role")
        if not user_id or not role:
            return Response({"detail": "user_id and role required"}, status=status.HTTP_400_BAD_REQUEST)
        membership = get_object_or_404(TeamMembership, team=team, user__id=user_id)
        membership.role = role
        membership.save()
        return Response(TeamMembershipSerializer(membership).data)

    @action(detail=False, methods=["get"], url_path="my-teams", permission_classes=[permissions.IsAuthenticated])
    def my_teams(self, request):
        qs = Team.objects.filter(memberships__user=request.user, memberships__status=TeamMembership.Status.ACTIVE).distinct().prefetch_related("memberships__user")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="leave", permission_classes=[permissions.IsAuthenticated, IsTeamMember])
    def leave(self, request, pk=None):
        team = self.get_object()
        membership = get_object_or_404(TeamMembership, team=team, user=request.user)
        if membership.role == TeamMembership.Role.OWNER:
            return Response({"detail": "owner cannot leave the team"}, status=status.HTTP_403_FORBIDDEN)
        membership.status = TeamMembership.Status.LEFT
        membership.save()
        return Response({"detail": "left team"})
