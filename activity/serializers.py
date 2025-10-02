from rest_framework import serializers
from .models import Activity, Notification
from django.contrib.contenttypes.models import ContentType

class ActivitySerializer(serializers.ModelSerializer):


    class Meta:
        model = Activity
        fields =  "__all__"

    def get_target_type(self, obj):
        return obj.target_ct.model if obj.target_ct else None


class NotificationSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer()

    class Meta:
        model = Notification
        fields = ["id", "activity", "is_read", "created_at"]