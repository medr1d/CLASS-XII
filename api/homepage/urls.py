from django.urls import path
from . import views
from . import migrate_views

urlpatterns = [
    path('', views.home, name='home'),
    path('python/', views.python_environment, name='python_environment'),
    path('python/get-files/', views.get_files, name='get_files'),
    path('save_user_data/', views.save_user_data, name='save_user_data'),
    path('load_user_data/', views.load_user_data, name='load_user_data'),
    path('migrate/', migrate_views.run_migrations, name='run_migrations'),
    
    # New features
    path('python/save-execution/', views.save_execution_history, name='save_execution_history'),
    path('python/get-history/', views.get_execution_history, name='get_execution_history'),
    path('python/share/', views.share_code, name='share_code'),
    path('share/<uuid:share_id>/', views.view_shared_code, name='view_shared_code'),
    path('python/fork/<uuid:share_id>/', views.fork_shared_code, name='fork_shared_code'),
    path('python/update-plot-theme/', views.update_plot_theme, name='update_plot_theme'),
    path('python/get-settings/', views.get_user_settings, name='get_user_settings'),
]
