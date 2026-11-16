from urllib.parse import quote

from django.conf import settings
from storages.backends.s3 import S3Storage


class PublicMediaStorage(S3Storage):
    def url(self, name, parameters=None, expire=None, http_method=None):
        encoded_name = quote(name.lstrip("/"), safe="/")
        return f"{settings.SEAWEEDFS_PUBLIC_BASE_URL}/{encoded_name}"
