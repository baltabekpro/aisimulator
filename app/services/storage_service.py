from minio import Minio
from minio.error import S3Error
from core.config import settings
import os

# Initialize Minio client if configured
_minio_client = None
if settings.STORAGE_TYPE.lower() in ("minio", "s3") and settings.S3_ENDPOINT and settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY:
    _minio_client = Minio(
        endpoint=settings.S3_ENDPOINT,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        secure=settings.S3_ENDPOINT.startswith("https://")
    )


def upload_file(bucket: str, object_name: str, file_obj, content_type: str = None) -> str:
    """
    Uploads a file to storage (local or Minio/S3) and returns the public URL.
    """
    # Read file bytes
    file_obj.seek(0)
    data = file_obj.read()
    size = len(data)
    file_obj.seek(0)

    # Minio/S3 storage
    if settings.STORAGE_TYPE.lower() in ("minio", "s3") and _minio_client:
        # Ensure bucket exists
        try:
            if not _minio_client.bucket_exists(bucket):
                _minio_client.make_bucket(bucket)
        except S3Error:
            pass

        # Upload object
        try:
            _minio_client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=file_obj,
                length=size,
                content_type=content_type
            )
        except S3Error as e:
            raise

        # Construct URL
        public_url = os.getenv("MINIO_PUBLIC_URL", settings.S3_ENDPOINT)
        # remove protocol prefix if present
        public_url = public_url.rstrip("/")
        return f"{public_url}/{bucket}/{object_name}"

    # Local filesystem storage
    upload_dir = settings.UPLOAD_DIR.rstrip("/")
    path = os.path.join(upload_dir, object_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    base_url = settings.BASE_URL.rstrip("/")
    return f"{base_url}/{upload_dir}/{object_name}"


def delete_file(bucket: str, object_name: str):
    """
    Deletes a file from storage (local or Minio/S3).
    """
    if settings.STORAGE_TYPE.lower() in ("minio", "s3") and _minio_client:
        try:
            _minio_client.remove_object(bucket, object_name)
        except S3Error:
            pass
    else:
        # Local filesystem delete
        path = os.path.join(settings.UPLOAD_DIR.rstrip("/"), object_name)
        try:
            os.remove(path)
        except OSError:
            pass