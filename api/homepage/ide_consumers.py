"""
WebSocket consumers for Cloud IDE real-time features
"""
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import IDEProject, IDETerminalSession


class IDETerminalConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time terminal output in IDE
    """
    
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.user = self.scope['user']
        self.room_group_name = f'ide_terminal_{self.project_id}'
        
        # Check authentication
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verify project ownership
        has_access = await self.check_project_access()
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': 'Terminal connected',
            'timestamp': self.get_timestamp()
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': self.get_timestamp()
                }))
            
            elif message_type == 'output':
                # Broadcast terminal output to all connected clients
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'terminal_output',
                        'output': data.get('output', ''),
                        'error': data.get('error', ''),
                        'user': self.user.username,
                        'timestamp': self.get_timestamp()
                    }
                )
            
            elif message_type == 'command':
                # Handle command execution (future feature)
                command = data.get('command', '')
                await self.send(text_data=json.dumps({
                    'type': 'info',
                    'message': f'Command received: {command}',
                    'timestamp': self.get_timestamp()
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
                'timestamp': self.get_timestamp()
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e),
                'timestamp': self.get_timestamp()
            }))
    
    async def terminal_output(self, event):
        """
        Receive terminal output from room group
        """
        await self.send(text_data=json.dumps({
            'type': 'output',
            'output': event['output'],
            'error': event['error'],
            'user': event['user'],
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def check_project_access(self):
        """
        Check if user has access to the project
        """
        try:
            project = IDEProject.objects.get(
                project_id=self.project_id,
                user=self.user
            )
            return True
        except IDEProject.DoesNotExist:
            return False
    
    def get_timestamp(self):
        """Get current timestamp"""
        from django.utils import timezone
        return timezone.now().isoformat()


class IDECollaborationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time collaborative editing
    Future feature: Multiple users editing same project
    """
    
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.user = self.scope['user']
        self.room_group_name = f'ide_collab_{self.project_id}'
        
        # Check authentication
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verify project access
        has_access = await self.check_project_access()
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others of new user
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'username': self.user.username,
                'timestamp': self.get_timestamp()
            }
        )
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Notify others of user leaving
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'username': self.user.username,
                    'timestamp': self.get_timestamp()
                }
            )
            
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Receive collaborative editing events
        """
        try:
            data = json.loads(text_data)
            event_type = data.get('type', 'change')
            
            if event_type == 'change':
                # Broadcast code changes to other users
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'code_change',
                        'file_path': data.get('file_path', ''),
                        'changes': data.get('changes', []),
                        'user': self.user.username,
                        'timestamp': self.get_timestamp()
                    }
                )
            
            elif event_type == 'cursor':
                # Broadcast cursor position
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'cursor_position',
                        'file_path': data.get('file_path', ''),
                        'position': data.get('position', {}),
                        'user': self.user.username,
                        'timestamp': self.get_timestamp()
                    }
                )
        
        except json.JSONDecodeError:
            pass
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def user_joined(self, event):
        """Handle user joined event"""
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
    
    async def user_left(self, event):
        """Handle user left event"""
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
    
    async def code_change(self, event):
        """Handle code change event"""
        if event['user'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'code_change',
                'file_path': event['file_path'],
                'changes': event['changes'],
                'user': event['user'],
                'timestamp': event['timestamp']
            }))
    
    async def cursor_position(self, event):
        """Handle cursor position event"""
        if event['user'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'cursor_position',
                'file_path': event['file_path'],
                'position': event['position'],
                'user': event['user'],
                'timestamp': event['timestamp']
            }))
    
    @database_sync_to_async
    def check_project_access(self):
        """Check if user has access to the project"""
        try:
            project = IDEProject.objects.get(
                project_id=self.project_id,
                user=self.user
            )
            return True
        except IDEProject.DoesNotExist:
            return False
    
    def get_timestamp(self):
        """Get current timestamp"""
        from django.utils import timezone
        return timezone.now().isoformat()
