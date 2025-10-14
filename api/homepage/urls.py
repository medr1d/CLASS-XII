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
    
    # Collaborative sessions
    path('python/session/create/', views.create_collaborative_session, name='create_collaborative_session'),
    path('python/code/<uuid:session_id>/', views.join_collaborative_session, name='join_collaborative_session'),
    path('python/session/<uuid:session_id>/members/', views.get_session_members, name='get_session_members'),
    path('python/session/<uuid:session_id>/permission/', views.update_member_permission, name='update_member_permission'),
    path('python/session/<uuid:session_id>/remove-member/', views.remove_member, name='remove_member'),
    path('python/session/<uuid:session_id>/import-files/', views.import_files_to_session, name='import_files_to_session'),
    path('python/session/<uuid:session_id>/export/', views.export_session_to_files, name='export_session_to_files'),
    path('python/session/<uuid:session_id>/end/', views.end_session, name='end_session'),
    
    # Community features
    path('community/', views.community, name='community'),
    path('community/send-friend-request/', views.send_friend_request, name='send_friend_request'),
    path('community/respond-friend-request/', views.respond_friend_request, name='respond_friend_request'),
    path('community/remove-friend/', views.remove_friend, name='remove_friend'),
    path('community/friends/', views.get_friends_list, name='get_friends_list'),
    path('community/update-status/', views.update_status_message, name='update_status_message'),
    path('community/send-message/', views.send_direct_message, name='send_direct_message'),
    path('community/messages/<int:user_id>/', views.get_direct_messages, name='get_direct_messages'),
]

