from django.core.files.storage import Storage, storages
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateMediaStorage(Storage):
    @property
    def backend(self):
        return storages["private"]

    def open(self, name, mode="rb"):
        return self.backend.open(name, mode)

    def save(self, name, content, max_length=None):
        return self.backend.save(name, content, max_length=max_length)

    def delete(self, name):
        return self.backend.delete(name)

    def exists(self, name):
        return self.backend.exists(name)

    def listdir(self, path):
        return self.backend.listdir(path)

    def size(self, name):
        return self.backend.size(name)

    def path(self, name):
        return self.backend.path(name)

    def get_accessed_time(self, name):
        return self.backend.get_accessed_time(name)

    def get_created_time(self, name):
        return self.backend.get_created_time(name)

    def get_modified_time(self, name):
        return self.backend.get_modified_time(name)

    def get_valid_name(self, name):
        return self.backend.get_valid_name(name)

    def get_available_name(self, name, max_length=None):
        return self.backend.get_available_name(name, max_length=max_length)

    def generate_filename(self, filename):
        return self.backend.generate_filename(filename)

    def url(self, name):
        raise ValueError(
            "Private files do not have public URLs. Use a protected API endpoint."
        )


private_media_storage = PrivateMediaStorage()
