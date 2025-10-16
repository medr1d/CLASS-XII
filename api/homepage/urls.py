from django.urls import path
from . import views
from . import migrate_views
from . import ide_views  # Import IDE views
from . import server_views  # Import Server views

urlpatterns = [
    path('', views.home, name='home'),
    path('python/', views.python_environment, name='python_environment'),
    path('python/get-files/', views.get_files, name='get_files'),
    path('python/delete-file/', views.delete_file, name='delete_file'),
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
    path('community/update-settings/', views.update_community_settings, name='update_community_settings'),
    path('community/send-message/', views.send_direct_message, name='send_direct_message'),
    path('community/messages/<int:user_id>/', views.get_direct_messages, name='get_direct_messages'),
    
    # Profile features
    path('profile/<int:user_id>/', views.get_user_profile, name='get_user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/upload-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    
    # Achievement features
    path('toggle-achievement-display/', views.toggle_achievement_display, name='toggle_achievement_display'),
    
    # ==================== CLOUD IDE ROUTES (Paid Users Only) ====================
    
    # Main IDE interface
    path('ide/', ide_views.ide_environment, name='ide_environment'),
    
    # Project management
    path('api/ide/projects/create/', ide_views.create_project, name='ide_create_project'),
    path('api/ide/projects/create-from-template/', ide_views.create_project_from_template, name='ide_create_from_template'),
    path('api/ide/projects/<uuid:project_id>/', ide_views.get_project, name='ide_get_project'),
    path('api/ide/projects/<uuid:project_id>/delete/', ide_views.delete_project, name='ide_delete_project'),
    
    # File management
    path('api/ide/projects/<uuid:project_id>/files/', ide_views.get_project_files, name='ide_get_files'),
    path('api/ide/projects/<uuid:project_id>/files/<path:file_path>/', ide_views.get_file_content, name='ide_get_file'),
    path('api/ide/projects/<uuid:project_id>/files/save/', ide_views.save_file, name='ide_save_file'),
    path('api/ide/projects/<uuid:project_id>/files/delete/', ide_views.delete_file, name='ide_delete_file'),
    path('api/ide/projects/<uuid:project_id>/files/rename/', ide_views.rename_file, name='ide_rename_file'),
    path('api/ide/projects/<uuid:project_id>/directories/create/', ide_views.create_directory, name='ide_create_directory'),
    
    # File upload/download
    path('api/ide/projects/<uuid:project_id>/upload/', ide_views.upload_files, name='ide_upload_files'),
    path('api/ide/projects/<uuid:project_id>/download/', ide_views.download_project, name='ide_download_project'),
    path('api/ide/projects/<uuid:project_id>/file/download/', ide_views.download_file, name='ide_download_file'),
    
    # Code execution
    path('api/ide/projects/<uuid:project_id>/execute/', ide_views.execute_code, name='ide_execute_code'),
    path('api/ide/projects/<uuid:project_id>/history/', ide_views.get_execution_history, name='ide_execution_history'),
    
    # Terminal session
    path('api/ide/projects/<uuid:project_id>/terminal/', ide_views.get_terminal_session, name='ide_get_terminal'),
    path('api/ide/projects/<uuid:project_id>/terminal/clear/', ide_views.clear_terminal, name='ide_clear_terminal'),
    
    # ==================== SERVER SYSTEM (Discord-like) ====================
    
    # Server management
    path('api/servers/', server_views.list_user_servers, name='list_user_servers'),
    path('api/servers/create/', server_views.create_server, name='create_server'),
    path('api/servers/<uuid:server_id>/', server_views.get_server_details, name='get_server_details'),
    path('api/servers/<uuid:server_id>/delete/', server_views.delete_server, name='delete_server'),
    path('api/servers/<uuid:server_id>/leave/', server_views.leave_server, name='leave_server'),
    path('api/servers/join/', server_views.join_server, name='join_server'),
    path('api/servers/discover/', server_views.discover_servers, name='discover_servers'),
    
    # Channel management
    path('api/servers/<uuid:server_id>/channels/create/', server_views.create_channel, name='create_channel'),
    path('api/channels/<uuid:channel_id>/', server_views.get_channel_messages, name='get_channel_messages'),
    path('api/channels/<uuid:channel_id>/send/', server_views.send_message, name='send_server_message'),
]
