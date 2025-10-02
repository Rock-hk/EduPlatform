from rest_framework import viewsets, permissions, mixins
from .models import Activity, Notification
from .serializers import ActivitySerializer, NotificationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ActivitySerializer

    def get_queryset(self):
        user = self.request.user
        return Activity.objects.filter(project__in=user.projects.all()).select_related("actor", "project")[:200]


class NotificationViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related("activity__actor","activity__project")

    @action(detail=False, methods=["post"])
    def mark_read(self, request):
        ids = request.data.get("ids", [])
        qs = self.get_queryset().filter(id__in=ids, is_read=False)
        updated = qs.update(is_read=True)
        return Response({"updated": updated})
