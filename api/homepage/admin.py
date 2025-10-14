from django.contrib import admin
from .models import PythonCodeSession, UserFiles, ExecutionHistory, SharedCode

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

@admin.register(ExecutionHistory)
class ExecutionHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'filename', 'was_successful', 'execution_time', 'executed_at')
    list_filter = ('was_successful', 'executed_at')
    search_fields = ('user__username', 'filename')
    readonly_fields = ('executed_at',)
    ordering = ('-executed_at',)

@admin.register(SharedCode)
class SharedCodeAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_public', 'view_count', 'fork_count', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('title', 'user__username', 'share_id')
    readonly_fields = ('share_id', 'created_at', 'updated_at', 'view_count', 'fork_count')
    ordering = ('-created_at',)
