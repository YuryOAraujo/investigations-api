from minio import Minio
from minio.error import S3Error
from io import BytesIO
import os
from typing import Optional

class MinioService:
  def __init__(self):
    self.client = Minio(
      os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
      access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
      secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
      secure=False
    )
    self.bucket_name = os.getenv('MINIO_BUCKET_NAME', 'investigations')
    self._ensure_bucket_exists()

  def _ensure_bucket_exists(self):
    try:
      if not self.client.bucket_exists(self.bucket_name):
        self.client.make_bucket(self.bucket_name)
    except S3Error as e:
      print(f'Error creating bucket: {e}')

  def upload_pdf(self, file_data: bytes, investigation_id: int, filename: str) -> str:
    object_name = f'investigation_{investigation_id}/{filename}'

    try:
      self.client.put_object(
        bucket_name=self.bucket_name,
        object_name=object_name,
        data=BytesIO(file_data),
        length=len(file_data),
        content_type='application/pdf'
      )
      return object_name
    except S3Error as e:
      raise Exception(f'Error uploading file: {e}')
    
  def download_pdf(self, object_name: str) -> bytes:
    Response = None
    
    try:
      response = self.client.get_object(self.bucket_name, object_name)
      return response.read()
    except S3Error as e:
      raise Exception(f'Error downloading file: {e}')
    finally:
      if response:
        response.close()
        response.release_conn()

  def delete_pdf(self, object_name: str):
    try:
      self.client.remove_object(self.bucket_name, object_name)
    except S3Error as e:
      raise Exception(f'Error deleting file: {e}')
    
  def get_presigned_url(self, object_name: str, expires_in_seconds: int = 3600) -> str:
    try:
      from datetime import timedelta

      url = self.client.presigned_get_object(
        self.bucket_name,
        object_name,
        expires=timedelta(seconds=expires_in_seconds)
      )
    except S3Error as e:
      raise Exception(f'Error generating presigned URL: {e}')
    

minio_service = MinioService()