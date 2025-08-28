from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from django.conf import settings
from django.db.models import Sum, Count, DurationField, ExpressionWrapper, F

User = settings.AUTH_USER_MODEL


class Category(MPTTModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def full_path(self, separator=" > "):
        ancestors = list(self.get_ancestors(include_self=True).values_list("name", flat=True))
        return separator.join(ancestors)
    
    
class Project(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_template = models.BooleanField(default=False)
    config = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        type_label = "Template" if self.is_template else "Project"
        return f"{self.title} ({type_label})"

    def total_time_spent(self):
        return self.tasks.aggregate(
            total=Sum('time_entries__duration')
        )['total'] or 0

    def team_productivity(self):
        return self.tasks.aggregate(
            tasks=Count('id'),
            done=Count('id', filter=models.Q(status=Task.Status.DONE)),
            in_progress=Count('id', filter=models.Q(status=Task.Status.IN_PROGRESS)),
        )


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'todo', 'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE = 'done', 'Done'
        BLOCKED = 'blocked', 'Blocked'

    project = models.ForeignKey(Project, related_name="tasks", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='subtasks', on_delete=models.CASCADE)

    dependencies = models.ManyToManyField('self', symmetrical=False, related_name='dependents', blank=True)
    assigned_to = models.ManyToManyField(User, through='TaskAssignment', related_name='tasks')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    def __str__(self):
        return self.title
    
    def is_blocked(self):
        return self.dependencies.exclude(status=Task.Status.DONE).exists()
    
    def has_circular_dependency(self, target_task):
        visited = set()
        def dfs(task):
            if task in visited:
                return False
            visited.add(task)
            if task == self:
                return True
            for dep in task.dependencies.all():
                if dfs(dep):
                    return True
            return False
        return dfs(target_task)
    
    def total_time_spent(self):
        return self.time_entries.aggregate(
            total=Sum('duration')
        )['total'] or 0

    def progress_percentage(self):
        if self.status == Task.Status.DONE:
            return 100
        elif self.status == Task.Status.IN_PROGRESS:
            return 50
        return 0

class TaskAssignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'user')
    

class TimeEntry(models.Model):
    task = models.ForeignKey("Task", related_name="time_entries", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="time_entries", on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    duration = models.DurationField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            self.duration = self.end_time - self.start_time
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.task} ({self.duration})"
