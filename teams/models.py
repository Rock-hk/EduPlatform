from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Team(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_teams")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TeamMembershipQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=TeamMembership.Status.ACTIVE)

    def for_user(self, user):
        return self.filter(user=user)


class TeamMembershipManager(models.Manager):
    def get_queryset(self):
        return TeamMembershipQuerySet(self.model, using=self._db)

    def for_team(self, team):
        return self.get_queryset().filter(team=team)

    def for_user(self, user):
        return self.get_queryset().filter(user=user)


class TeamMembership(models.Model):
    from accounts.models import User 

    class Role(models.TextChoices):
        OWNER = User.Roles.SYSTEM_ADMIN   
        ADMIN = User.Roles.MANAGER
        MEMBER = User.Roles.USER
        DEVELOPER = User.Roles.DEVELOPER
        INVITED = 'invited', 'Invited'  

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PENDING = 'pending', 'Pending'
        LEFT = 'left', 'Left'
        REMOVED = 'removed', 'Removed'

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="team_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_team_invitations")
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    note = models.TextField(blank=True)

    objects = TeamMembershipManager()

    class Meta:
        unique_together = ('team', 'user')
        indexes = [
            models.Index(fields=['team', 'user']),
            models.Index(fields=['user']),
        ]

    def save(self, *args, **kwargs):
        if self.status == self.Status.ACTIVE and not self.joined_at:
            self.joined_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} @ {self.team} ({self.role})"
