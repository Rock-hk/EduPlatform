from rest_framework import permissions
from .models import User

class IsManager(permissions.BasePermission):
   
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Roles.MANAGER


class IsDeveloper(permissions.BasePermission):
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Roles.DEVELOPER