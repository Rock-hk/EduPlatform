from rest_framework import serializers
from .models import Team, TeamMembership
from django.contrib.auth import get_user_model

User = get_user_model()

class TeamMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = TeamMembership
        fields = (
            "id", "user_id", "user_email", "role", "role_display",
            "status", "joined_at", "invited_by", "note"
        )
        read_only_fields = ("invited_by", "joined_at")


class TeamSerializer(serializers.ModelSerializer):
    members = TeamMembershipSerializer(source="memberships", many=True, read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Team
        fields = (
            "id", "name", "slug", "description",
            "created_at", "created_by", "created_by_email", "members"
        )
        read_only_fields = ("created_at", "created_by", "members")
