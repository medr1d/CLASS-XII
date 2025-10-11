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
]