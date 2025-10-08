"""
Custom storage backends for handling file uploads with Vercel Blob
"""
import os
import requests
import uuid
import time
import random
from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible


@deconstructible
class VercelBlobStorage(Storage):
    """
    Custom storage backend for Vercel Blob using the correct Vercel Blob API.
    Based on the official Vercel Blob JavaScript SDK implementation.
    """
    
    def __init__(self):
        self.token = getattr(settings, 'BLOB_READ_WRITE_TOKEN', None)
        if not self.token:
            raise ValueError("BLOB_READ_WRITE_TOKEN environment variable is required")
        
        # Extract store ID from token for building URLs
        token_parts = self.token.split('_')
        self.store_id = token_parts[3] if len(token_parts) > 3 else 'default'
        self.api_url = "https://vercel.com/api/blob"
        
    def _save(self, name, content):
        """
        Save file to Vercel Blob storage using the correct API endpoint.
        """
        try:
            # Generate unique filename with UUID to avoid conflicts
            file_extension = os.path.splitext(name)[1]
            unique_name = f"{uuid.uuid4().hex}{file_extension}"
            
            # Read file content
            content.seek(0)
            file_data = content.read()
            
            # Generate request ID (mimicking the official SDK)
            request_id = f"{self.store_id}:{int(time.time() * 1000)}:{hex(random.randint(0, 2**32))[2:]}"
            
            # Prepare API request to Vercel Blob (correct endpoint and headers)
            url = f"{self.api_url}/?pathname={unique_name}"
            headers = {
                'Authorization': f'Bearer {self.token}',
                'x-api-version': '11',
                'x-api-blob-request-id': request_id,
                'x-api-blob-request-attempt': '0',
                'x-add-random-suffix': 'false',  # We're adding our own UUID
                'x-content-type': getattr(content, 'content_type', 'application/octet-stream'),
            }
            
            # Make the upload request using PUT method (as per Vercel Blob API)
            response = requests.put(url, headers=headers, data=file_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                # Return the URL for Django to store in the database
                return result.get('url', f"https://{self.store_id}.public.blob.vercel-storage.com/{unique_name}")
            else:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error uploading to Vercel Blob: {str(e)}")

    def _open(self, name, mode='rb'):
        """
        Open file from Vercel Blob storage (name is the full URL).
        """
        try:
            response = requests.get(name, timeout=30)
            if response.status_code == 200:
                return ContentFile(response.content)
            else:
                raise FileNotFoundError(f"File not found: {name}")
        except Exception as e:
            raise FileNotFoundError(f"Error opening file: {str(e)}")

    def delete(self, name):
        """
        Delete file from Vercel Blob storage using the correct delete API.
        """
        if not self.token or not name:
            return False
            
        try:
            # Use Vercel Blob delete API endpoint
            url = f"{self.api_url}/delete"
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'x-api-version': '11',
            }
            
            # Delete using the file URL
            data = {'urls': [name]}
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            return response.status_code == 200
        except Exception:
            return False

    def exists(self, name):
        """
        Check if file exists (name is the full URL).
        """
        try:
            response = requests.head(name, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def url(self, name):
        """
        Return the URL for the file (name is already the full URL).
        """
        return name

    def size(self, name):
        """
        Get file size from the URL.
        """
        try:
            response = requests.head(name, timeout=10)
            return int(response.headers.get('Content-Length', 0))
        except Exception:
            return 0