from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Category, Project, Task
from .serializers import CategoryTreeSerializer, CategoryDetailSerializer, ProjectSerializer, TaskSerializer
from .permissions import ProjectPermission



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

    @action(detail=False, methods=['get'], url_path='blocked')
    def blocked_tasks(self, request):
        project_id = request.query_params.get('project')
        if not project_id:
            return Response({"detail": "project query param required"}, status=status.HTTP_400_BAD_REQUEST)
        tasks = Task.objects.filter(project_id=project_id).filter(dependencies__status__in=['todo', 'in_progress']).distinct()
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
