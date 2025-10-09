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
    
    def __init__(self):
        self.token = getattr(settings, 'BLOB_READ_WRITE_TOKEN', None)
        if not self.token:
            raise ValueError("BLOB_READ_WRITE_TOKEN environment variable is required")
        
        token_parts = self.token.split('_')
        self.store_id = token_parts[3] if len(token_parts) > 3 else 'default'
        self.api_url = "https://vercel.com/api/blob"
        
    def _save(self, name, content):
        try:
            file_extension = os.path.splitext(name)[1]
            unique_name = f"{uuid.uuid4().hex}{file_extension}"
            
            content.seek(0)
            file_data = content.read()
            
            request_id = f"{self.store_id}:{int(time.time() * 1000)}:{hex(random.randint(0, 2**32))[2:]}"
            
            url = f"{self.api_url}/?pathname={unique_name}"
            headers = {
                'Authorization': f'Bearer {self.token}',
                'x-api-version': '11',
                'x-api-blob-request-id': request_id,
                'x-api-blob-request-attempt': '0',
                'x-add-random-suffix': 'false',
                'x-content-type': getattr(content, 'content_type', 'application/octet-stream'),
            }
            
            response = requests.put(url, headers=headers, data=file_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('url', f"https://{self.store_id}.public.blob.vercel-storage.com/{unique_name}")
            else:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"Error uploading to Vercel Blob: {str(e)}")

    def _open(self, name, mode='rb'):
        try:
            response = requests.get(name, timeout=30)
            if response.status_code == 200:
                return ContentFile(response.content)
            else:
                raise FileNotFoundError(f"File not found: {name}")
        except Exception as e:
            raise FileNotFoundError(f"Error opening file: {str(e)}")

    def delete(self, name):
        if not self.token or not name:
            return False
            
        try:
            url = f"{self.api_url}/delete"
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'x-api-version': '11',
            }
            
            data = {'urls': [name]}
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            return response.status_code == 200
        except Exception:
            return False

    def exists(self, name):
        try:
            response = requests.head(name, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def url(self, name):
        return name

    def size(self, name):
        try:
            response = requests.head(name, timeout=10)
            return int(response.headers.get('Content-Length', 0))
        except Exception:
            return 0