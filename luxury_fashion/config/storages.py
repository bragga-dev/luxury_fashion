import os

import boto3
from botocore.client import Config
from django.conf import settings
from storages.utils import clean_name
from storages.backends.s3boto3 import S3Boto3Storage


class MediaFilesStorage(S3Boto3Storage):
    bucket_name = os.environ.get("MINIO_BUCKET_MEDIA", "luxuryfashionmedia")
    default_acl = "public-read"
    file_overwrite = True
    custom_domain = (
    f"{os.environ.get('MINIO_PUBLIC_URL')}/"
    f"{os.environ.get('MINIO_BUCKET_MEDIA', 'luxuryfashionmedia')}")
    url_protocol = getattr(settings, "MINIO_URL_PROTOCOL", os.environ.get("MINIO_URL_PROTOCOL", "http:"))

class StaticFilesStorage(S3Boto3Storage):
    bucket_name = os.environ.get("MINIO_BUCKET_STATIC", "luxuryfashionstatic")
    default_acl = "public-read"
    file_overwrite = True

class PrivateFilesStorage(S3Boto3Storage):
    bucket_name = os.environ.get("MINIO_BUCKET_PRIVATE", "luxuryfashionprivate")
    default_acl = None
    file_overwrite = False
    querystring_auth = True
    querystring_expire = 3600
    custom_domain = None  # nunca herdar AWS_S3_CUSTOM_DOMAIN (aponta pro bucket público de mídia)

    def url(self, name, parameters=None, expire=None, http_method=None):
        """
        URL assinada alcançável pelo navegador. O endpoint interno (ex.: minio:9000)
        não resolve fora do Docker, e o host entra na assinatura V4 — então, com
        MINIO_EXTERNAL_URL definida, a assinatura é gerada já contra o host público.
        """
        external = os.environ.get("MINIO_EXTERNAL_URL")
        if not external:
            return super().url(name, parameters, expire, http_method)

        client = boto3.client(
            "s3",
            endpoint_url=external,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        params = {"Bucket": self.bucket_name, "Key": self._normalize_name(clean_name(name))}
        if parameters:
            params.update(parameters)
        return client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expire or self.querystring_expire,
            HttpMethod=http_method,
        )