import re
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from .models import Activity, Notification
from django.apps import apps

User = apps.get_model(settings.AUTH_USER_MODEL)
TaskAssignment = apps.get_model("categories", "TaskAssignment")  # adjust if your app label != 'tasks'
Comment = apps.get_model("activity", "Comment")
Task = apps.get_model("categories", "Task")
Project = apps.get_model("categories", "Project")

from .serializers import NotificationSerializer

channel_layer = get_channel_layer()

def push_notification_ws(notification):
    """
    Serializes notification with DRF serializer and pushes via channels to recipient group.
    """
    if not channel_layer:
        return
    serializer = NotificationSerializer(notification)
    payload = serializer.data
    group = f"user_{notification.recipient.id}"
    async_to_sync(channel_layer.group_send)(
        group,
        {
            "type": "send_notification",
            "data": payload
        }
    )

@receiver(post_save, sender=TaskAssignment)
def on_task_assignment(sender, instance, created, **kwargs):
    if not created:
        return
    # create Activity
    act = Activity.objects.create(
        actor=instance.user,
        verb="assigned",
        target_ct=ContentType.objects.get_for_model(instance.task),
        target_id=instance.task.id,
        project=instance.task.project if getattr(instance.task, 'project', None) else None
    )
    notif = Notification.objects.create(recipient=instance.user, activity=act)
    push_notification_ws(notif)


MENTION_REGEX = re.compile(r'@([\w.@+-]+)')

@receiver(post_save, sender=Comment)
def on_comment_created(sender, instance, created, **kwargs):
    if not created:
        return
    # Activity for comment
    act = Activity.objects.create(
        actor=instance.author,
        verb="commented",
        target_ct=ContentType.objects.get_for_model(instance.task),
        target_id=instance.task.id,
        project=instance.task.project if getattr(instance.task, 'project', None) else None
    )
    # push notification to project manager and optionally members if you want
    # Mentions handling
    mentions = MENTION_REGEX.findall(instance.content or "")
    recipients = set()
    for mention in mentions:
        # try by email first, then by username if exists
        try:
            user = User.objects.filter(email__iexact=mention).first()
            if not user and hasattr(User, 'username'):
                user = User.objects.filter(username=mention).first()
            if user:
                recipients.add(user)
        except Exception:
            continue

    created_notifs = []
    for user in recipients:
        n = Notification(recipient=user, activity=act)
        created_notifs.append(n)
    if created_notifs:
        Notification.objects.bulk_create(created_notifs)
        # push each
        for n in Notification.objects.filter(activity=act, recipient__in=[u.id for u in recipients]):
            push_notification_ws(n)
