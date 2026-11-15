from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)

    def url(self, name):
        raise ValueError(
            "Private files do not have public URLs. Use a protected API endpoint."
        )


private_media_storage = PrivateMediaStorage()
