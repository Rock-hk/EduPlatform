from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Team, TeamMembership

@receiver(post_save, sender=Team)
def create_owner_membership(sender, instance, created, **kwargs):
    if created and instance.created_by:
        TeamMembership.objects.create(
            team=instance,
            user=instance.created_by,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE,
            invited_by=instance.created_by
        )
