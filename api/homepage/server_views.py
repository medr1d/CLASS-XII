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
def create_server(request):
    """Create a new server (paid users only)"""
    try:
        # Check if user is paid
        profile = UserProfile.objects.get(user=request.user)
        if not profile.paidUser:
            return JsonResponse({
                'success': False,
                'error': 'Only premium users can create servers. Please upgrade your account.'
            }, status=403)
        
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        icon_url = data.get('icon_url', '').strip()
        is_public = data.get('is_public', True)
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Server name is required'
            }, status=400)
        
        if len(name) > 100:
            return JsonResponse({
                'success': False,
                'error': 'Server name must be 100 characters or less'
            }, status=400)
        
        # Create server
        server = Server.objects.create(
            name=name,
            description=description,
            owner=request.user,
            icon_url=icon_url if icon_url else None,
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
            'success': True,
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
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
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
        
        # Create channel
        channel = ServerChannel.objects.create(
            server=server,
            name=name,
            description=description,
            channel_type=channel_type,
            position=max_position + 1
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
