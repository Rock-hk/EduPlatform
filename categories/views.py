from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Category, Project, Task, TimeEntry
from .serializers import CategoryTreeSerializer, CategoryDetailSerializer, ProjectSerializer, TaskSerializer, TimeEntrySerializer
from .permissions import ProjectPermission
from django.db.models.functions import TruncWeek
from django.db.models import Sum, Count, Q, F
from django.contrib.auth import get_user_model
from rest_framework_csv.renderers import CSVRenderer
from django.db.models.functions import TruncDate
from django.db.models import Window
from django.db.models.functions import Lag
User = get_user_model()



class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategoryDetailSerializer

    def get_serializer_class(self):
        if self.action == 'tree':
            return CategoryTreeSerializer
        return CategoryDetailSerializer

    @action(detail=False, methods=['get'], url_path='tree')
    def tree(self, request):
       
        roots = Category.objects.filter(parent__isnull=True)
        serializer = self.get_serializer(roots, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        
        category = self.get_object()
        parent_id = request.data.get('parent_id', None)
        if parent_id is None:
            category.parent = None
            category.save()
            return Response(self.get_serializer(category).data)
        if parent_id == category.id:
            return Response({"detail": "Cannot set self as parent."}, status=status.HTTP_400_BAD_REQUEST)
        parent = get_object_or_404(Category, id=parent_id)
        if parent.is_descendant_of(category):
            return Response({"detail": "Cannot move category into its own descendant."}, status=status.HTTP_400_BAD_REQUEST)
        category.parent = parent
        category.save()
        return Response(self.get_serializer(category).data)

    @action(detail=True, methods=['get'], url_path='descendants')
    def descendants(self, request, pk=None):
        
        category = self.get_object()
        include_self = request.query_params.get('include_self', 'true').lower() != 'false'
        if include_self:
            qs = category.get_descendants(include_self=True)
        else:
            qs = category.get_descendants()
        serializer = CategoryDetailSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='projects')
    def projects(self, request, pk=None):
      
        category = self.get_object()
        descendant_ids = category.get_descendants(include_self=True).values_list('id', flat=True)
        projects = Project.objects.filter(category_id__in=list(descendant_ids)).select_related('owner', 'category')
        from rest_framework import serializers
        class SimpleProjectSerializer(serializers.ModelSerializer):
            category_name = serializers.CharField(source='category.name', read_only=True)
            owner_email = serializers.CharField(source='owner.email', read_only=True)
            class Meta:
                model = Project
                fields = ('id','title','description','category','category_name','owner','owner_email')
        serializer = SimpleProjectSerializer(projects, many=True)
        return Response(serializer.data)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [ProjectPermission]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='clone')
    def clone(self, request, pk=None):
        project = self.get_object()
        new_title = request.data.get('title', f"{project.title} (Clone)")
        new_team_id = request.data.get('team_id', project.team_id)

        with transaction.atomic():
            cloned_project = Project.objects.create(
                title=new_title,
                description=project.description,
                owner=request.user,
                category=project.category,
                is_template=False,
                config=project.config,
                team_id=new_team_id
            )
            tasks = project.tasks.all()
            new_tasks = [
                Task(project=cloned_project, title=t.title, description=t.description)
                for t in tasks
            ]
            Task.objects.bulk_create(new_tasks)

        serializer = ProjectSerializer(cloned_project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='make-template')
    def make_template(self, request, pk=None):
        project = self.get_object()
        project.is_template = True
        project.save()
        serializer = ProjectSerializer(project)
        return Response(serializer.data)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    

    @action(detail=True, methods=['post'], url_path='start-timer')
    def start_timer(self, request, pk=None):
        task = self.get_object()
        start_time = request.data.get("start_time")
        if not start_time:
            start_time = timezone.now()
        entry = TimeEntry.objects.create(
            task=task, user=request.user, start_time=start_time
        )
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='stop-timer')
    def stop_timer(self, request, pk=None):
        task = self.get_object()
        end_time = request.data.get("end_time") or timezone.now()

        entry = (TimeEntry.objects
                 .filter(task=task, user=request.user, end_time__isnull=True)
                 .order_by('-start_time')
                 .first())
        if not entry:
            return Response({"detail": "No active timer found"}, status=status.HTTP_400_BAD_REQUEST)

        entry.end_time = end_time
        entry.save()
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_200_OK)
    

class TimeEntryViewSet(viewsets.ModelViewSet):
    queryset = TimeEntry.objects.all()
    serializer_class = TimeEntrySerializer

    def get_queryset(self):
        return TimeEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReportViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'])
    def project_summary(self, request):
        projects = Project.objects.all()
        data = []
        for project in projects:
            data.append({
                "project": project.title,
                "total_time": project.total_time_spent(),
                "tasks": project.team_productivity()
            })
        return Response(data)

    @action(detail=False, methods=['get'])
    def user_time(self, request):
        qs = TimeEntry.objects.values("user__username").annotate(
            total_time=Sum("duration")
        )
        return Response(list(qs))

    @action(detail=False, methods=['get'])
    def weekly_time(self, request):
        qs = (TimeEntry.objects.annotate(week=TruncWeek("start_time"))
              .values("user__username", "week")
              .annotate(total_time=Sum("duration"))
              .order_by("week"))
        return Response(list(qs))

    @action(detail=False, methods=['get'])
    def task_progress(self, request):
        qs = (Task.objects.annotate(
                total_time=Sum("time_entries__duration"),
                done=Count("id", filter=Q(status=Task.Status.DONE)),
                in_progress=Count("id", filter=Q(status=Task.Status.IN_PROGRESS)),
            )
            .values("id", "title", "status", "total_time", "done", "in_progress"))
        return Response(list(qs))


class DashboardViewSet(viewsets.ViewSet):

    @action(detail=True, methods=['get'])
    def burndown(self, request, pk=None):
        
        project = Project.objects.get(pk=pk)
        data = (
            Task.objects.filter(project=project)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(total=Count('id'))
            .order_by('day')
        )
        return Response(data)

    @action(detail=True, methods=['get'])
    def team_load(self, request, pk=None):
       
        project = Project.objects.get(pk=pk)
        data = (
            User.objects.filter(taskassignment__task__project=project)
            .annotate(task_count=Count('taskassignment'))
            .annotate(total_time=Sum('taskassignment__task__timeentry__duration'))
            .values('id', 'email', 'task_count', 'total_time')
        )
        return Response(data)
    

    @action(detail=False, methods=['get'])
    def export(self, request):
       
        format = request.query_params.get('format', 'json')
        data = Project.objects.annotate(total_tasks=Count('task')).values('id', 'title', 'total_tasks')

        if format == 'csv':
            
            renderer = CSVRenderer()
            return Response(data, content_type='text/csv')
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def productivity_trends(self, request):
        
        qs = (
            TimeEntry.objects
            .annotate(day=TruncDate('start_time'))
            .annotate(
                prev=Window(
                    expression=Lag('start_time'),
                    partition_by=[F('user_id')],
                    order_by=F('start_time').asc()
                )
            )
            .annotate(diff=F('start_time') - F('prev'))
            .values('user_id', 'day', 'start_time', 'prev', 'diff')
            .order_by('user_id', 'day')
        )
        return Response(list(qs))
