from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import Category

@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name','parent')
    search_fields = ('name','slug')
