from django.urls import path
from . import views
from . import migrate_views

urlpatterns = [
    path('', views.home, name='home'),
    path('python/', views.python_environment, name='python_environment'),
    path('python/get-files/', views.get_files, name='get_files'),
    path('migrate/', migrate_views.run_migrations, name='run_migrations'),
]