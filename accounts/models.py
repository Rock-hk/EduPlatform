from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        USER = 'user', 'User'
        MANAGER = 'manager', 'Manager'
        DEVELOPER = 'developer', 'Developer'
        SYSTEM_ADMIN = 'system_admin', 'System Admin'

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.USER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return self.email

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    timezone = models.CharField(max_length=64, default='UTC')
    preferences = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Profile<{self.user.email}>"

# Proxy models for roles
class _RoleFilteredManager(models.Manager):
    role_value = None
    def get_queryset(self):
        qs = super().get_queryset()
        if self.role_value:
            qs = qs.filter(role=self.role_value)
        return qs

class ManagerUser(User):
    objects = _RoleFilteredManager()
    objects.role_value = User.Roles.MANAGER
    class Meta:
        proxy = True

class DeveloperUser(User):
    objects = _RoleFilteredManager()
    objects.role_value = User.Roles.DEVELOPER
    class Meta:
        proxy = True
