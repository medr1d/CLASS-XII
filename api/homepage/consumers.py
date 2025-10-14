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
