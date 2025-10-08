from django.contrib import admin
from .models import PythonCodeSession, UserFiles

@admin.register(PythonCodeSession)
class PythonCodeSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'filename', 'is_auto_save', 'created_at', 'updated_at')
    list_filter = ('is_auto_save', 'created_at')
    search_fields = ('user__username', 'filename')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserFiles)
class UserFilesAdmin(admin.ModelAdmin):
    list_display = ('user', 'filename', 'file_type', 'is_system_file', 'created_at')
    list_filter = ('file_type', 'is_system_file', 'created_at')
    search_fields = ('user__username', 'filename')
    readonly_fields = ('created_at', 'updated_at')
