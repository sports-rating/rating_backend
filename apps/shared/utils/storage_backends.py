from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class CustomStaticStorage(S3Boto3Storage):
    """
    Storage for static files (CSS, JS, images).
    Uses the S3_STATIC_BUCKET and location prefix.
    """
    bucket_name = settings.S3_STATIC_BUCKET
    location = settings.S3_STATIC_LOCATION
    default_acl = None  # recommended: don’t use public ACLs


class CustomMediaStorage(S3Boto3Storage):
    """
    Storage for user-uploaded media files.
    Uses the S3_MEDIA_BUCKET and no prefix (or "media" if you want).
    """
    bucket_name = settings.S3_MEDIA_BUCKET
    location = settings.S3_MEDIA_LOCATION
    default_acl = None  # media should be private usually
    file_overwrite = False  # important: don’t overwrite user uploads
