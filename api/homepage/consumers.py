import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import uuid


class CollaborativeSessionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'code_session_{self.session_id}'
        self.user = self.scope['user']
        
        # Validate session exists and is collaborative
        session = await self.get_session()
        if not session or session['session_type'] != 'collaborative':
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Add user as session member
        await self.add_session_member()
        
        # Broadcast user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
        
        # Send current session state to new user
        session_state = await self.get_session_state()
        await self.send(text_data=json.dumps({
            'type': 'session_state',
            'state': session_state,
        }))
        
        # Send members list
        members = await self.get_members_list()
        await self.send(text_data=json.dumps({
            'type': 'members_update',
            'members': members,
        }))
    
    async def disconnect(self, close_code):
        # Mark user as offline
        await self.update_member_status(False)
        
        # Broadcast user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        # Update session activity timestamp
        await self.update_session_activity()
        
        if message_type == 'code_change':
            # Check if user has edit permission
            has_permission = await self.check_edit_permission()
            if not has_permission:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You do not have permission to edit'
                }))
                return
            
            # Broadcast code change to all members
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'code_change_broadcast',
                    'code': data.get('code'),
                    'user_id': self.user.id,
                    'username': self.user.username,
                }
            )
            
            # Save to session state
            await self.update_session_state({'code': data.get('code')})
        
        elif message_type == 'cursor_position':
            # Broadcast cursor position
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'cursor_position_broadcast',
                    'position': data.get('position'),
                    'user_id': self.user.id,
                    'username': self.user.username,
                }
            )
        
        elif message_type == 'terminal_output':
            # Broadcast terminal output
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'terminal_output_broadcast',
                    'output': data.get('output'),
                    'user_id': self.user.id,
                }
            )
            
            # Save to session state
            await self.append_terminal_output(data.get('output'))
    
    # WebSocket event handlers
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_id': event['user_id'],
            'username': event['username'],
        }))
    
    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id'],
            'username': event['username'],
        }))
    
    async def code_change_broadcast(self, event):
        # Don't send back to the user who made the change
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'code_change',
                'code': event['code'],
                'user_id': event['user_id'],
                'username': event['username'],
            }))
    
    async def cursor_position_broadcast(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'cursor_position',
                'position': event['position'],
                'user_id': event['user_id'],
                'username': event['username'],
            }))
    
    async def terminal_output_broadcast(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'terminal_output',
                'output': event['output'],
            }))
    
    async def permission_changed(self, event):
        if event['user_id'] == self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'permission_changed',
                'permission': event['permission'],
            }))
    
    async def member_removed(self, event):
        if event['user_id'] == self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'removed_from_session',
                'message': 'You have been removed from this session',
            }))
            await self.close()
    
    # Database operations
    @database_sync_to_async
    def get_session(self):
        from .models import SharedCode
        try:
            session = SharedCode.objects.get(share_id=self.session_id, is_active=True)
            return {
                'session_type': session.session_type,
                'owner_id': session.user.id,
                'is_expired': session.is_expired(),
            }
        except SharedCode.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_session_state(self):
        from .models import SharedCode
        try:
            session = SharedCode.objects.get(share_id=self.session_id)
            return session.session_state
        except SharedCode.DoesNotExist:
            return {}
    
    @database_sync_to_async
    def update_session_state(self, updates):
        from .models import SharedCode
        try:
            session = SharedCode.objects.get(share_id=self.session_id)
            session.session_state.update(updates)
            session.save(update_fields=['session_state', 'updated_at'])
        except SharedCode.DoesNotExist:
            pass
    
    @database_sync_to_async
    def append_terminal_output(self, output):
        from .models import SharedCode
        try:
            session = SharedCode.objects.get(share_id=self.session_id)
            if 'terminal_output' not in session.session_state:
                session.session_state['terminal_output'] = []
            session.session_state['terminal_output'].append(output)
            # Keep only last 1000 lines
            if len(session.session_state['terminal_output']) > 1000:
                session.session_state['terminal_output'] = session.session_state['terminal_output'][-1000:]
            session.save(update_fields=['session_state', 'updated_at'])
        except SharedCode.DoesNotExist:
            pass
    
    @database_sync_to_async
    def add_session_member(self):
        from .models import SharedCode, SessionMember
        try:
            session = SharedCode.objects.get(share_id=self.session_id)
            member, created = SessionMember.objects.get_or_create(
                session=session,
                user=self.user,
                defaults={'permission': 'view', 'is_online': True}
            )
            if not created:
                member.is_online = True
                member.last_active = timezone.now()
                member.save(update_fields=['is_online', 'last_active'])
        except SharedCode.DoesNotExist:
            pass
    
    @database_sync_to_async
    def update_member_status(self, is_online):
        from .models import SessionMember
        try:
            member = SessionMember.objects.get(
                session__share_id=self.session_id,
                user=self.user
            )
            member.is_online = is_online
            member.last_active = timezone.now()
            member.save(update_fields=['is_online', 'last_active'])
        except SessionMember.DoesNotExist:
            pass
    
    @database_sync_to_async
    def check_edit_permission(self):
        from .models import SessionMember, SharedCode
        try:
            session = SharedCode.objects.get(share_id=self.session_id)
            # Owner always has edit permission
            if session.user == self.user:
                return True
            
            member = SessionMember.objects.get(
                session=session,
                user=self.user
            )
            return member.permission == 'edit'
        except (SharedCode.DoesNotExist, SessionMember.DoesNotExist):
            return False
    
    @database_sync_to_async
    def get_members_list(self):
        from .models import SessionMember, SharedCode
        try:
            session = SharedCode.objects.get(share_id=self.session_id)
            members = SessionMember.objects.filter(session=session, is_online=True)
            return [{
                'user_id': m.user.id,
                'username': m.user.username,
                'permission': m.permission,
                'is_owner': m.user == session.user,
                'last_active': m.last_active.isoformat(),
            } for m in members]
        except SharedCode.DoesNotExist:
            return []
    
    @database_sync_to_async
    def update_session_activity(self):
        """Update the last_activity timestamp for the session"""
        from .models import SharedCode
        try:
            session = SharedCode.objects.get(share_id=self.session_id)
            session.update_activity()
        except SharedCode.DoesNotExist:
            pass


class ServerChannelConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for server channels (Discord-like real-time messaging)"""
    
    async def connect(self):
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.room_group_name = f'server_channel_{self.channel_id}'
        self.user = self.scope['user']
        
        # Validate user is a member of the server
        is_member = await self.check_server_membership()
        if not is_member:
            await self.close()
            return
        
        # Join channel group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that user is online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online'
            }
        )
    
    async def disconnect(self, close_code):
        # Notify others that user is offline
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'offline'
            }
        )
        
        # Leave channel group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'new_message':
            # Check if user is muted
            is_muted = await self.check_if_muted()
            if is_muted:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You are muted in this server'
                }))
                return
            
            # Save message to database
            message = await self.save_message(data.get('content'), data.get('reply_to'))
            
            # Broadcast message to all channel members
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_broadcast',
                    'message': message
                }
            )
        
        elif message_type == 'typing_start':
            # User started typing
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_typing': True
                }
            )
        
        elif message_type == 'typing_end':
            # User stopped typing
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_typing': False
                }
            )
        
        elif message_type == 'react':
            # Add reaction to message
            reaction = await self.add_reaction(
                data.get('message_id'),
                data.get('emoji')
            )
            
            if reaction:
                # Broadcast reaction
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'reaction_added',
                        'message_id': data.get('message_id'),
                        'user_id': self.user.id,
                        'username': self.user.username,
                        'emoji': data.get('emoji')
                    }
                )
    
    # WebSocket event handlers
    async def message_broadcast(self, event):
        """Broadcast new message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))
    
    async def user_status(self, event):
        """Broadcast user status change"""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))
    
    async def typing_indicator(self, event):
        """Broadcast typing indicator"""
        # Don't send to self
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def reaction_added(self, event):
        """Broadcast reaction"""
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'username': event['username'],
            'emoji': event['emoji']
        }))
    
    # Database operations
    @database_sync_to_async
    def check_server_membership(self):
        """Check if user is a member of the server containing this channel"""
        from .models import ServerChannel, ServerMember
        try:
            channel = ServerChannel.objects.get(channel_id=self.channel_id)
            return ServerMember.objects.filter(
                server=channel.server,
                user=self.user
            ).exists()
        except ServerChannel.DoesNotExist:
            return False
    
    @database_sync_to_async
    def check_if_muted(self):
        """Check if user is muted in the server"""
        from .models import ServerChannel, ServerMember
        try:
            channel = ServerChannel.objects.get(channel_id=self.channel_id)
            member = ServerMember.objects.get(server=channel.server, user=self.user)
            return member.is_muted
        except (ServerChannel.DoesNotExist, ServerMember.DoesNotExist):
            return False
    
    @database_sync_to_async
    def save_message(self, content, reply_to_id=None):
        """Save message to database"""
        from .models import ServerChannel, ServerMessage
        try:
            channel = ServerChannel.objects.get(channel_id=self.channel_id)
            
            reply_to = None
            if reply_to_id:
                reply_to = ServerMessage.objects.filter(message_id=reply_to_id).first()
            
            message = ServerMessage.objects.create(
                channel=channel,
                sender=self.user,
                content=content,
                reply_to=reply_to
            )
            
            # Get profile picture
            profile_pic = None
            if hasattr(self.user, 'profile'):
                profile_pic = self.user.profile.get_profile_picture_url()
            
            return {
                'message_id': str(message.message_id),
                'sender': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'profile_picture': profile_pic
                },
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'reply_to': {
                    'message_id': str(reply_to.message_id),
                    'sender_username': reply_to.sender.username,
                    'content': reply_to.content[:100]
                } if reply_to else None
            }
        except Exception as e:
            print(f"Error saving message: {e}")
            return None
    
    @database_sync_to_async
    def add_reaction(self, message_id, emoji):
        """Add reaction to a message"""
        from .models import ServerMessage, ServerMessageReaction
        try:
            message = ServerMessage.objects.get(message_id=message_id)
            
            # Check if user already reacted with this emoji
            reaction, created = ServerMessageReaction.objects.get_or_create(
                message=message,
                user=self.user,
                emoji=emoji
            )
            
            return True
        except ServerMessage.DoesNotExist:
            return False
