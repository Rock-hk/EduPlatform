from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProjectViewSet, TaskViewSet 

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')


urlpatterns = router.urls
