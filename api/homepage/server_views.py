"""
Server System Views - Discord-like servers for community
"""
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from .models import (
    Server, ServerMember, ServerChannel, ServerMessage, 
    ServerMessageReaction, ServerInvite, UserProfile
)
import json
import uuid


@login_required
def list_user_servers(request):
    """Get all servers user is a member of"""
    try:
        servers = Server.objects.filter(
            members__user=request.user
        ).annotate(
            member_count=Count('members'),
            channel_count=Count('channels')
        ).select_related('owner').order_by('-updated_at')
        
        server_list = []
        for server in servers:
            # Get user's role in this server
            membership = ServerMember.objects.get(server=server, user=request.user)
            
            server_list.append({
                'server_id': str(server.server_id),
                'name': server.name,
                'description': server.description,
                'icon_url': server.get_icon_url(),
                'owner': {
                    'id': server.owner.id,
                    'username': server.owner.username
                },
                'member_count': server.member_count,
                'channel_count': server.channel_count,
                'user_role': membership.role,
                'created_at': server.created_at.isoformat(),
            })
        
        return JsonResponse({
            'status': 'success',
            'servers': server_list
        })
    except Exception as e:
        import traceback
        print(f"Error listing servers: {traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_POST
def create_server(request):
    """Create a new server (paid users only)"""
    try:
        # Check if user is paid
        profile = UserProfile.objects.get(user=request.user)
        if not profile.paidUser:
            return JsonResponse({
                'status': 'error',
                'message': 'Only premium users can create servers. Please upgrade your account.'
            }, status=403)
        
        # Handle FormData (for file uploads)
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_public = request.POST.get('is_public') == 'on'  # Checkbox value
        icon_file = request.FILES.get('icon')  # File upload
        
        if not name:
            return JsonResponse({
                'status': 'error',
                'message': 'Server name is required'
            }, status=400)
        
        if len(name) > 100:
            return JsonResponse({
                'status': 'error',
                'message': 'Server name must be 100 characters or less'
            }, status=400)
        
        # Handle icon upload (if provided)
        icon_url = None
        if icon_file:
            try:
                import vercel_blob
                import os
                
                # Validate file
                if not icon_file.content_type.startswith('image/'):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Icon must be an image file'
                    }, status=400)
                
                # Max 2MB for server icons
                if icon_file.size > 2 * 1024 * 1024:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Icon too large (max 2MB)'
                    }, status=400)
                
                # Get Vercel Blob token
                blob_token = os.getenv('BLOB_READ_WRITE_TOKEN')
                if blob_token:
                    # Upload to Vercel Blob
                    filename = f"server_icon_{request.user.id}_{int(timezone.now().timestamp())}.{icon_file.name.split('.')[-1]}"
                    file_content = icon_file.read()
                    response = vercel_blob.put(filename, file_content, {})
                    
                    if response and 'url' in response:
                        icon_url = response['url']
                else:
                    print("Warning: BLOB_READ_WRITE_TOKEN not configured, skipping icon upload")
            except Exception as upload_error:
                print(f"Icon upload error: {upload_error}")
                # Continue without icon if upload fails
                pass
        
        # Create server
        server = Server.objects.create(
            name=name,
            description=description,
            owner=request.user,
            icon_url=icon_url,
            is_public=is_public
        )
        
        # Generate invite code
        server.generate_invite_code()
        
        # Add owner as member with owner role
        ServerMember.objects.create(
            server=server,
            user=request.user,
            role='owner',
            can_manage_channels=True,
            can_kick_members=True,
            can_ban_members=True,
            can_manage_messages=True
        )
        
        # Create default channels
        ServerChannel.objects.create(
            server=server,
            name='general',
            description='General discussion',
            channel_type='text',
            position=0
        )
        
        ServerChannel.objects.create(
            server=server,
            name='announcements',
            description='Server announcements',
            channel_type='announcements',
            position=1
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Server created successfully',
            'server': {
                'server_id': str(server.server_id),
                'name': server.name,
                'description': server.description,
                'icon_url': server.get_icon_url(),
                'invite_code': server.invite_code,
                'created_at': server.created_at.isoformat()
            }
        })
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'User profile not found'
        }, status=404)
    except Exception as e:
        import traceback
        print(f"Error creating server: {traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def get_server_details(request, server_id):
    """Get detailed information about a server"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check if user is a member
        membership = ServerMember.objects.filter(server=server, user=request.user).first()
        if not membership:
            return JsonResponse({
                'success': False,
                'error': 'You are not a member of this server'
            }, status=403)
        
        # Get channels
        channels = ServerChannel.objects.filter(server=server).order_by('position', 'created_at')
        channel_list = [{
            'channel_id': str(channel.channel_id),
            'name': channel.name,
            'description': channel.description,
            'channel_type': channel.channel_type,
            'message_count': channel.get_message_count()
        } for channel in channels]
        
        # Get members
        members = ServerMember.objects.filter(server=server).select_related('user', 'user__profile')
        member_list = [{
            'user_id': member.user.id,
            'username': member.user.username,
            'display_name': member.display_name(),
            'role': member.role,
            'profile_picture': member.user.profile.get_profile_picture_url() if hasattr(member.user, 'profile') else None,
            'joined_at': member.joined_at.isoformat()
        } for member in members]
        
        return JsonResponse({
            'success': True,
            'server': {
                'server_id': str(server.server_id),
                'name': server.name,
                'description': server.description,
                'icon_url': server.get_icon_url(),
                'owner_id': server.owner.id,
                'invite_code': server.invite_code if membership.role in ['owner', 'admin'] else None,
                'is_public': server.is_public,
                'member_count': server.get_member_count(),
                'created_at': server.created_at.isoformat()
            },
            'channels': channel_list,
            'members': member_list,
            'user_role': membership.role,
            'user_permissions': {
                'can_manage_channels': membership.can_manage_channels,
                'can_kick_members': membership.can_kick_members,
                'can_ban_members': membership.can_ban_members,
                'can_manage_messages': membership.can_manage_messages,
                'is_muted': membership.is_muted
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def create_channel(request, server_id):
    """Create a new channel in a server"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check permissions
        membership = get_object_or_404(ServerMember, server=server, user=request.user)
        if not membership.can_manage_channels and membership.role not in ['owner', 'admin']:
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to create channels'
            }, status=403)
        
        data = json.loads(request.body)
        name = data.get('name', '').strip().lower().replace(' ', '-')
        description = data.get('description', '').strip()
        channel_type = data.get('channel_type', 'text')
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Channel name is required'
            }, status=400)
        
        # Check if channel already exists
        if ServerChannel.objects.filter(server=server, name=name).exists():
            return JsonResponse({
                'success': False,
                'error': 'A channel with this name already exists'
            }, status=400)
        
        # Get max position
        max_position = ServerChannel.objects.filter(server=server).aggregate(
            max_pos=Count('position')
        )['max_pos'] or 0
        
        # Get additional voice channel settings if applicable
        user_limit = data.get('user_limit')
        if channel_type == 'voice' and user_limit:
            user_limit = int(user_limit) if user_limit else None
        else:
            user_limit = None
        
        # Create channel with proper channel_type
        channel = ServerChannel.objects.create(
            server=server,
            name=name,
            description=description,
            channel_type=channel_type,  # This will now correctly be 'voice' or 'text' or 'announcements'
            position=max_position + 1,
            user_limit=user_limit if channel_type == 'voice' else None
        )
        
        return JsonResponse({
            'success': True,
            'channel': {
                'channel_id': str(channel.channel_id),
                'name': channel.name,
                'description': channel.description,
                'channel_type': channel.channel_type,
                'created_at': channel.created_at.isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_channel_messages(request, channel_id):
    """Get messages from a channel"""
    try:
        channel = get_object_or_404(ServerChannel, channel_id=channel_id)
        
        # Check if user is a member of the server
        membership = ServerMember.objects.filter(
            server=channel.server,
            user=request.user
        ).first()
        
        if not membership:
            return JsonResponse({
                'success': False,
                'error': 'You are not a member of this server'
            }, status=403)
        
        # Get pagination parameters
        limit = min(int(request.GET.get('limit', 50)), 100)
        offset = int(request.GET.get('offset', 0))
        
        # Get messages
        messages = ServerMessage.objects.filter(
            channel=channel
        ).select_related(
            'sender', 'sender__profile', 'reply_to', 'reply_to__sender'
        ).prefetch_related('reactions')[offset:offset+limit]
        
        message_list = []
        for msg in messages:
            # Get reactions grouped by emoji
            reactions_dict = {}
            for reaction in msg.reactions.all():
                if reaction.emoji not in reactions_dict:
                    reactions_dict[reaction.emoji] = []
                reactions_dict[reaction.emoji].append(reaction.user.username)
            
            reactions = [
                {'emoji': emoji, 'count': len(users), 'users': users}
                for emoji, users in reactions_dict.items()
            ]
            
            message_data = {
                'message_id': str(msg.message_id),
                'sender': {
                    'id': msg.sender.id,
                    'username': msg.sender.username,
                    'profile_picture': msg.sender.profile.get_profile_picture_url() if hasattr(msg.sender, 'profile') else None
                },
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'is_edited': msg.is_edited,
                'is_pinned': msg.is_pinned,
                'reactions': reactions,
                'reply_to': None
            }
            
            if msg.reply_to:
                message_data['reply_to'] = {
                    'message_id': str(msg.reply_to.message_id),
                    'sender_username': msg.reply_to.sender.username,
                    'content': msg.reply_to.content[:100]
                }
            
            message_list.append(message_data)
        
        return JsonResponse({
            'success': True,
            'messages': message_list,
            'channel': {
                'channel_id': str(channel.channel_id),
                'name': channel.name,
                'description': channel.description
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def send_message(request, channel_id):
    """Send a message to a channel"""
    try:
        channel = get_object_or_404(ServerChannel, channel_id=channel_id)
        
        # Check membership and mute status
        membership = get_object_or_404(
            ServerMember,
            server=channel.server,
            user=request.user
        )
        
        if membership.is_muted:
            return JsonResponse({
                'success': False,
                'error': 'You are muted in this server'
            }, status=403)
        
        # Check permissions for announcements channel
        if channel.channel_type == 'announcements':
            # Only owners and admins can post in announcements
            if membership.role not in ['owner', 'admin']:
                return JsonResponse({
                    'success': False,
                    'error': 'Only server owners and administrators can post in announcements'
                }, status=403)
        
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to')
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Message content cannot be empty'
            }, status=400)
        
        if len(content) > 2000:
            return JsonResponse({
                'success': False,
                'error': 'Message too long (max 2000 characters)'
            }, status=400)
        
        # Handle reply
        reply_to = None
        if reply_to_id:
            reply_to = ServerMessage.objects.filter(
                message_id=reply_to_id,
                channel=channel
            ).first()
        
        # Create message
        message = ServerMessage.objects.create(
            channel=channel,
            sender=request.user,
            content=content,
            reply_to=reply_to
        )
        
        # Update server's updated_at for sorting
        channel.server.save(update_fields=['updated_at'])
        
        return JsonResponse({
            'success': True,
            'message': {
                'message_id': str(message.message_id),
                'sender': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'profile_picture': request.user.profile.get_profile_picture_url() if hasattr(request.user, 'profile') else None
                },
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'is_edited': message.is_edited,
                'reply_to': {
                    'message_id': str(reply_to.message_id),
                    'sender_username': reply_to.sender.username,
                    'content': reply_to.content[:100]
                } if reply_to else None
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def join_server(request):
    """Join a server using invite code"""
    try:
        data = json.loads(request.body)
        invite_code = data.get('invite_code', '').strip().upper()
        
        if not invite_code:
            return JsonResponse({
                'success': False,
                'error': 'Invite code is required'
            }, status=400)
        
        # Find server by invite code
        server = Server.objects.filter(invite_code=invite_code).first()
        if not server:
            return JsonResponse({
                'success': False,
                'error': 'Invalid invite code'
            }, status=404)
        
        # Check if already a member
        if ServerMember.objects.filter(server=server, user=request.user).exists():
            return JsonResponse({
                'success': False,
                'error': 'You are already a member of this server'
            }, status=400)
        
        # Add user as member
        ServerMember.objects.create(
            server=server,
            user=request.user,
            role='member'
        )
        
        return JsonResponse({
            'success': True,
            'server': {
                'server_id': str(server.server_id),
                'name': server.name,
                'description': server.description,
                'icon_url': server.get_icon_url()
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def leave_server(request, server_id):
    """Leave a server"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check if user is owner
        if server.owner == request.user:
            return JsonResponse({
                'success': False,
                'error': 'Server owner cannot leave. Transfer ownership or delete the server.'
            }, status=400)
        
        # Remove membership
        membership = get_object_or_404(ServerMember, server=server, user=request.user)
        membership.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'You have left {server.name}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def delete_server(request, server_id):
    """Delete a server (owner only)"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check if user is owner
        if server.owner != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Only the server owner can delete the server'
            }, status=403)
        
        server_name = server.name
        server.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Server "{server_name}" has been deleted'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def discover_servers(request):
    """Discover public servers"""
    try:
        # Get public servers the user is NOT a member of
        user_server_ids = ServerMember.objects.filter(
            user=request.user
        ).values_list('server_id', flat=True)
        
        servers = Server.objects.filter(
            is_public=True
        ).exclude(
            id__in=user_server_ids
        ).annotate(
            member_count=Count('members')
        ).select_related('owner').order_by('-member_count', '-created_at')[:20]
        
        server_list = [{
            'server_id': str(server.server_id),
            'name': server.name,
            'description': server.description,
            'icon_url': server.get_icon_url(),
            'owner_username': server.owner.username,
            'member_count': server.member_count,
            'created_at': server.created_at.isoformat()
        } for server in servers]
        
        return JsonResponse({
            'success': True,
            'servers': server_list
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def update_server_settings(request, server_id):
    """Update server settings (name, description, icon)"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check if user is owner or admin
        membership = get_object_or_404(ServerMember, server=server, user=request.user)
        if membership.role not in ['owner', 'admin']:
            return JsonResponse({
                'status': 'error',
                'message': 'Only owners and admins can update server settings'
            }, status=403)
        
        # Handle both JSON and FormData
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description')
            is_public = data.get('is_public')
            icon_file = None
        else:
            # FormData
            name = request.POST.get('name')
            description = request.POST.get('description')
            is_public = request.POST.get('is_public') == 'true'
            icon_file = request.FILES.get('icon')
        
        # Update fields if provided
        if name:
            name = name.strip()
            if len(name) > 100:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Server name must be 100 characters or less'
                }, status=400)
            server.name = name
        
        if description is not None:
            server.description = description.strip()
        
        if is_public is not None:
            server.is_public = is_public
        
        # Handle icon upload
        if icon_file:
            try:
                import vercel_blob
                import os
                
                # Validate file
                if not icon_file.content_type.startswith('image/'):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Icon must be an image file'
                    }, status=400)
                
                if icon_file.size > 2 * 1024 * 1024:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Icon too large (max 2MB)'
                    }, status=400)
                
                blob_token = os.getenv('BLOB_READ_WRITE_TOKEN')
                if blob_token:
                    filename = f"server_icon_{server.id}_{int(timezone.now().timestamp())}.{icon_file.name.split('.')[-1]}"
                    file_content = icon_file.read()
                    response = vercel_blob.put(filename, file_content, {})
                    
                    if response and 'url' in response:
                        server.icon_url = response['url']
            except Exception as upload_error:
                print(f"Icon upload error: {upload_error}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Failed to upload icon: {str(upload_error)}'
                }, status=500)
        
        server.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Server settings updated successfully',
            'server': {
                'server_id': str(server.server_id),
                'name': server.name,
                'description': server.description,
                'icon_url': server.get_icon_url(),
                'is_public': server.is_public
            }
        })
    except Exception as e:
        import traceback
        print(f"Error updating server: {traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@require_POST
@login_required
def create_invite(request, server_id):
    """Create an invite link for a server"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check if user is a member
        membership = ServerMember.objects.filter(server=server, user=request.user).first()
        if not membership:
            return JsonResponse({'success': False, 'message': 'Not a member of this server'}, status=403)
        
        # Check permissions (only owner, admin, or members with permission can invite)
        if membership.role not in ['owner', 'admin']:
            return JsonResponse({'success': False, 'message': 'No permission to create invites'}, status=403)
        
        data = json.loads(request.body)
        max_uses = data.get('max_uses')  # None = unlimited
        expires_in_hours = data.get('expires_in_hours', 24)  # Default 24 hours
        
        # Generate unique invite code
        import random
        import string
        invite_code = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        # Calculate expiry
        expires_at = None
        if expires_in_hours:
            from datetime import timedelta
            expires_at = timezone.now() + timedelta(hours=expires_in_hours)
        
        # Create invite
        invite = ServerInvite.objects.create(
            invite_code=invite_code,
            server=server,
            created_by=request.user,
            max_uses=max_uses,
            expires_at=expires_at
        )
        
        return JsonResponse({
            'success': True,
            'invite': {
                'code': invite.invite_code,
                'url': f'/community/?invite={invite.invite_code}',
                'full_url': request.build_absolute_uri(f'/community/?invite={invite.invite_code}'),
                'max_uses': invite.max_uses,
                'uses': invite.uses,
                'expires_at': invite.expires_at.isoformat() if invite.expires_at else None,
                'created_at': invite.created_at.isoformat()
            }
        })
    except Exception as e:
        import traceback
        print(f"Error creating invite: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_GET
@login_required
def get_server_invites(request, server_id):
    """Get all active invites for a server"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check if user is a member
        membership = ServerMember.objects.filter(server=server, user=request.user).first()
        if not membership:
            return JsonResponse({'success': False, 'message': 'Not a member of this server'}, status=403)
        
        # Only owner and admin can view invites
        if membership.role not in ['owner', 'admin']:
            return JsonResponse({'success': False, 'message': 'No permission to view invites'}, status=403)
        
        invites = ServerInvite.objects.filter(server=server).select_related('created_by').order_by('-created_at')
        
        invite_list = []
        for invite in invites:
            invite_list.append({
                'code': invite.invite_code,
                'url': f'/community/?invite={invite.invite_code}',
                'full_url': request.build_absolute_uri(f'/community/?invite={invite.invite_code}'),
                'max_uses': invite.max_uses,
                'uses': invite.uses,
                'expires_at': invite.expires_at.isoformat() if invite.expires_at else None,
                'is_valid': invite.is_valid(),
                'created_by': invite.created_by.username,
                'created_at': invite.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'invites': invite_list
        })
    except Exception as e:
        import traceback
        print(f"Error getting invites: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_POST
@login_required
def join_server_by_invite(request):
    """Join a server using an invite code"""
    try:
        data = json.loads(request.body)
        invite_code = data.get('invite_code')
        
        if not invite_code:
            return JsonResponse({'success': False, 'message': 'Invite code required'}, status=400)
        
        # Get invite
        invite = ServerInvite.objects.filter(invite_code=invite_code).select_related('server').first()
        if not invite:
            return JsonResponse({'success': False, 'message': 'Invalid invite code'}, status=404)
        
        # Check if valid
        if not invite.is_valid():
            return JsonResponse({'success': False, 'message': 'Invite has expired or reached max uses'}, status=400)
        
        server = invite.server
        
        # Check if already a member
        existing = ServerMember.objects.filter(server=server, user=request.user).first()
        if existing:
            return JsonResponse({
                'success': True,
                'message': 'Already a member',
                'server_id': str(server.server_id),
                'already_member': True
            })
        
        # Join server
        ServerMember.objects.create(
            server=server,
            user=request.user,
            role='member'
        )
        
        # Increment uses
        invite.uses += 1
        invite.save()
        
        # Update server member count
        server.updated_at = timezone.now()
        server.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully joined {server.name}',
            'server': {
                'server_id': str(server.server_id),
                'name': server.name,
                'description': server.description,
                'icon_url': server.get_icon_url()
            }
        })
    except Exception as e:
        import traceback
        print(f"Error joining server: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def send_invite_to_friend(request):
    """Send server invite link to a friend via DM"""
    try:
        data = json.loads(request.body)
        server_id = data.get('server_id')
        friend_id = data.get('friend_id')
        
        if not server_id or not friend_id:
            return JsonResponse({
                'success': False,
                'error': 'Server ID and friend ID required'
            }, status=400)
        
        server = get_object_or_404(Server, server_id=server_id)
        friend = get_object_or_404(User, id=friend_id)
        
        # Check if user is member of server
        if not ServerMember.objects.filter(server=server, user=request.user).exists():
            return JsonResponse({
                'success': False,
                'error': 'You are not a member of this server'
            }, status=403)
        
        # Check if they're friends
        from .models import Friendship
        if not Friendship.are_friends(request.user, friend):
            return JsonResponse({
                'success': False,
                'error': 'You can only send invites to friends'
            }, status=403)
        
        # Create invite message with embed data
        invite_code = server.invite_code
        invite_url = f"/api/servers/join/?code={invite_code}"
        
        # Send DM with special invite format
        from .models import DirectMessage
        message_content = f"[SERVER_INVITE:{server.server_id}:{invite_code}]"
        
        DirectMessage.objects.create(
            sender=request.user,
            recipient=friend,
            message=message_content
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Invite sent to {friend.username}'
        })
        
    except Exception as e:
        import traceback
        print(f"Error sending invite: {traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_invite_embed_data(request, server_id):
    """Get server data for invite embed"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        
        return JsonResponse({
            'success': True,
            'server': {
                'server_id': str(server.server_id),
                'name': server.name,
                'description': server.description,
                'icon_url': server.get_icon_url(),
                'member_count': server.get_member_count(),
                'invite_code': server.invite_code,
                'is_public': server.is_public
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_member_profile(request, server_id, user_id):
    """Get mini profile data for a server member"""
    try:
        server = get_object_or_404(Server, server_id=server_id)
        member = get_object_or_404(ServerMember, server=server, user_id=user_id)
        user = member.user
        
        # Check if requesting user is a member
        if not ServerMember.objects.filter(server=server, user=request.user).exists():
            return JsonResponse({
                'success': False,
                'error': 'You must be a member to view profiles'
            }, status=403)
        
        # Get user profile
        profile_data = {
            'user_id': user.id,
            'username': user.username,
            'display_name': member.display_name(),
            'profile_picture': user.profile.get_profile_picture_url() if hasattr(user, 'profile') else None,
            'role': member.role,
            'joined_at': member.joined_at.isoformat(),
            'is_online': hasattr(user, 'online_status') and user.online_status.is_online,
        }
        
        # Add profile info if available
        if hasattr(user, 'profile'):
            profile_data.update({
                'bio': user.profile.bio,
                'location': user.profile.location,
                'github_username': user.profile.github_username,
                'twitter_username': user.profile.twitter_username,
                'website': user.profile.website,
            })
        
        return JsonResponse({
            'success': True,
            'member': profile_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def send_invite_to_friend(request, server_id):
    """Send server invite directly to a friend via DM"""
    try:
        data = json.loads(request.body)
        friend_user_id = data.get('friend_user_id')
        custom_message = data.get('message', '')
        
        if not friend_user_id:
            return JsonResponse({'status': 'error', 'message': 'Friend ID required'}, status=400)
        
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check if user is a member
        membership = ServerMember.objects.filter(server=server, user=request.user).first()
        if not membership:
            return JsonResponse({'status': 'error', 'message': 'Not a member of this server'}, status=403)
        
        # Check if friend exists and is friends with user
        friend = get_object_or_404(User, id=friend_user_id)
        from .models import Friendship
        if not Friendship.are_friends(request.user, friend):
            return JsonResponse({'status': 'error', 'message': 'Can only send invites to friends'}, status=403)
        
        # Get or create invite for this server
        invite = ServerInvite.objects.filter(
            server=server,
            created_by=request.user,
            max_uses=0  # Unlimited
        ).first()
        
        if not invite:
            import random
            import string
            invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            invite = ServerInvite.objects.create(
                server=server,
                invite_code=invite_code,
                created_by=request.user,
                max_uses=0
            )
        
        # Create DM with server invite embed
        from .models import DirectMessage
        invite_url = request.build_absolute_uri(f'/community/?invite={invite.invite_code}')
        
        # Format message with server invite embed marker
        message_content = f"""[SERVER_INVITE:{invite.invite_code}]
{custom_message if custom_message else f'{request.user.username} invited you to join {server.name}!'}"""
        
        DirectMessage.objects.create(
            sender=request.user,
            recipient=friend,
            message=message_content
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Invite sent to {friend.username}',
            'invite_code': invite.invite_code
        })
        
    except Exception as e:
        import traceback
        print(f"Error sending invite: {traceback.format_exc()}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def get_invite_info(request, invite_code):
    """Get server information from invite code for embed preview"""
    try:
        invite = ServerInvite.objects.filter(invite_code=invite_code).select_related('server').first()
        
        if not invite:
            return JsonResponse({'status': 'error', 'message': 'Invalid invite'}, status=404)
        
        if not invite.is_valid():
            return JsonResponse({'status': 'error', 'message': 'Invite expired'}, status=400)
        
        server = invite.server
        member_count = ServerMember.objects.filter(server=server).count()
        
        # Check if user is already a member
        is_member = ServerMember.objects.filter(server=server, user=request.user).exists()
        
        return JsonResponse({
            'status': 'success',
            'server': {
                'server_id': str(server.server_id),
                'name': server.name,
                'description': server.description,
                'icon_url': server.get_icon_url(),
                'member_count': member_count,
                'is_public': server.is_public,
                'invite_code': invite_code,
                'is_member': is_member
            }
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def create_category(request, server_id):
    """Create a new category for organizing channels"""
    try:
        from .models import ServerCategory
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check permissions
        membership = get_object_or_404(ServerMember, server=server, user=request.user)
        if not membership.can_manage_channels and membership.role not in ['owner', 'admin']:
            return JsonResponse({'success': False, 'error': 'No permission'}, status=403)
        
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name required'}, status=400)
        
        # Get max position
        max_pos = ServerCategory.objects.filter(server=server).count()
        
        category = ServerCategory.objects.create(
            server=server,
            name=name,
            position=max_pos
        )
        
        return JsonResponse({
            'success': True,
            'category': {
                'category_id': str(category.category_id),
                'name': category.name,
                'position': category.position
            }
        })
    except Exception as e:
        import traceback
        print(f"Error creating category: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def create_role(request, server_id):
    """Create a custom role in the server"""
    try:
        from .models import ServerRole
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check permissions (owner or admin only)
        membership = get_object_or_404(ServerMember, server=server, user=request.user)
        if membership.role not in ['owner', 'admin']:
            return JsonResponse({'success': False, 'error': 'No permission'}, status=403)
        
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        color = data.get('color', '#99AAB5')
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Role name required'}, status=400)
        
        # Check if role name exists
        if ServerRole.objects.filter(server=server, name=name).exists():
            return JsonResponse({'success': False, 'error': 'Role name already exists'}, status=400)
        
        role = ServerRole.objects.create(
            server=server,
            name=name,
            color=color,
            position=ServerRole.objects.filter(server=server).count()
        )
        
        return JsonResponse({
            'success': True,
            'role': {
                'role_id': str(role.role_id),
                'name': role.name,
                'color': role.color,
                'position': role.position
            }
        })
    except Exception as e:
        import traceback
        print(f"Error creating role: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def get_server_categories(request, server_id):
    """Get all categories in a server"""
    try:
        from .models import ServerCategory
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check membership
        if not ServerMember.objects.filter(server=server, user=request.user).exists():
            return JsonResponse({'success': False, 'error': 'Not a member'}, status=403)
        
        categories = ServerCategory.objects.filter(server=server).order_by('position')
        
        category_list = [{
            'category_id': str(cat.category_id),
            'name': cat.name,
            'position': cat.position,
            'is_collapsed': cat.is_collapsed
        } for cat in categories]
        
        return JsonResponse({'success': True, 'categories': category_list})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def get_server_roles(request, server_id):
    """Get all roles in a server"""
    try:
        from .models import ServerRole
        server = get_object_or_404(Server, server_id=server_id)
        
        # Check membership
        if not ServerMember.objects.filter(server=server, user=request.user).exists():
            return JsonResponse({'success': False, 'error': 'Not a member'}, status=403)
        
        roles = ServerRole.objects.filter(server=server).order_by('-position')
        
        role_list = [{
            'role_id': str(role.role_id),
            'name': role.name,
            'color': role.color,
            'position': role.position,
            'permissions': {
                'can_manage_channels': role.can_manage_channels,
                'can_manage_roles': role.can_manage_roles,
                'can_kick_members': role.can_kick_members,
                'can_ban_members': role.can_ban_members,
                'can_manage_messages': role.can_manage_messages,
                'can_mention_everyone': role.can_mention_everyone
            }
        } for role in roles]
        
        return JsonResponse({'success': True, 'roles': role_list})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def join_voice_channel(request, channel_id):
    """Join a voice channel"""
    try:
        channel = get_object_or_404(ServerChannel, channel_id=channel_id)
        
        if channel.channel_type != 'voice':
            return JsonResponse({'success': False, 'error': 'Not a voice channel'}, status=400)
        
        # Check membership
        membership = get_object_or_404(ServerMember, server=channel.server, user=request.user)
        
        # Check user limit
        if channel.user_limit:
            current_members = ServerMember.objects.filter(current_voice_channel=channel).count()
            if current_members >= channel.user_limit:
                return JsonResponse({'success': False, 'error': 'Channel is full'}, status=400)
        
        # Update user's voice channel
        membership.current_voice_channel = channel
        membership.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Joined voice channel: {channel.name}'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def leave_voice_channel(request):
    """Leave current voice channel"""
    try:
        data = json.loads(request.body)
        server_id = data.get('server_id')
        
        server = get_object_or_404(Server, server_id=server_id)
        membership = get_object_or_404(ServerMember, server=server, user=request.user)
        
        if not membership.current_voice_channel:
            return JsonResponse({'success': False, 'error': 'Not in a voice channel'}, status=400)
        
        membership.current_voice_channel = None
        membership.save()
        
        return JsonResponse({'success': True, 'message': 'Left voice channel'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def get_voice_channel_members(request, channel_id):
    """Get all members currently in a voice channel"""
    try:
        channel = get_object_or_404(ServerChannel, channel_id=channel_id)
        
        # Check membership
        if not ServerMember.objects.filter(server=channel.server, user=request.user).exists():
            return JsonResponse({'success': False, 'error': 'Not a member'}, status=403)
        
        members = ServerMember.objects.filter(current_voice_channel=channel).select_related('user', 'user__profile')
        
        member_list = [{
            'user_id': m.user.id,
            'username': m.user.username,
            'display_name': m.display_name(),
            'profile_picture': m.user.profile.get_profile_picture_url() if hasattr(m.user, 'profile') else None
        } for m in members]
        
        return JsonResponse({'success': True, 'members': member_list})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
