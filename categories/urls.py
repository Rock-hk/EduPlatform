from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProjectViewSet, TaskViewSet , TimeEntryViewSet, ReportViewSet, DashboardViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'time-entries', TimeEntryViewSet, basename='timeentry')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')


urlpatterns = router.urls
