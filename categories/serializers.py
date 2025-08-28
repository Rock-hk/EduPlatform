from rest_framework import serializers
from .models import Category, Project, Task, TaskAssignment, TimeEntry
from teams.models import Team

class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class CategoryTreeSerializer(serializers.ModelSerializer):
    children = RecursiveField(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "children")


class CategoryDetailSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    full_path = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "parent", "full_path")

    def get_full_path(self, obj):
        return obj.full_path()
    


class TaskSerializer(serializers.ModelSerializer):
    subtasks = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'order', 'parent', 'subtasks']

    def get_subtasks(self, obj):
        return TaskSerializer(obj.subtasks.all(), many=True).data

class ProjectSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'owner', 'category', 'category_name',
            'is_template', 'config', 'team', 'team_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']


class TaskAssignmentSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = TaskAssignment
        fields = ['id', 'user', 'user_email', 'assigned_at']

class TaskSerializer(serializers.ModelSerializer):
    assigned_to = TaskAssignmentSerializer(source='taskassignment_set', many=True, read_only=True)
    dependencies_ids = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), many=True, source='dependencies', write_only=True, required=False
    )
    is_blocked = serializers.SerializerMethodField()
    total_time = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()  

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'assigned_to', 'dependencies_ids', 'is_blocked', 'project', 'created_at', 'updated_at', 'total_time', 'progress']

    def get_is_blocked(self, obj):
        return obj.is_blocked()

    def validate_dependencies(self, value):
        task = self.instance if self.instance else Task()
        for dep in value:
            if task.has_circular_dependency(dep):
                raise serializers.ValidationError(f"Circular dependency detected with task {dep.id}")
        return value
    
    def get_total_time(self, obj):
        return obj.total_time_spent()

    def get_progress(self, obj):
        return obj.progress_percentage()


class TimeEntrySerializer(serializers.ModelSerializer):
    duration = serializers.DurationField(read_only=True)

    class Meta:
        model = TimeEntry
        fields = ['id', 'task', 'user', 'description', 'start_time', 'end_time', 'duration']

    