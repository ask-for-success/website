import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from apps.recruitment.storage import PrivateMediaStorage

from ..backends import PublicMediaStorage
from ..management.commands.initialize_storage import ensure_bucket


class StorageBackendTests(SimpleTestCase):
    @override_settings(
        SEAWEEDFS_PUBLIC_BASE_URL="https://media.askforsuccess.example/public",
    )
    def test_public_storage_builds_external_url(self):
        storage = PublicMediaStorage()

        url = storage.url("content/news/community photo.jpg")

        self.assertEqual(
            url,
            "https://media.askforsuccess.example/public/"
            "content/news/community%20photo.jpg",
        )

    def test_private_storage_never_returns_public_url(self):
        with self.assertRaisesMessage(
            ValueError,
            "Private files do not have public URLs",
        ):
            PrivateMediaStorage().url("recruitment/cvs/private.pdf")

    def test_missing_bucket_is_created(self):
        client = Mock()
        client.head_bucket.side_effect = ClientError(
            {
                "Error": {"Code": "NoSuchBucket", "Message": "Missing"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            "HeadBucket",
        )

        created = ensure_bucket(client, "afs-public-media")

        self.assertTrue(created)
        client.create_bucket.assert_called_once_with(Bucket="afs-public-media")

    @override_settings(
        FILE_STORAGE_BACKEND="seaweedfs",
        SEAWEEDFS_PUBLIC_BUCKET="afs-public-media",
        SEAWEEDFS_PRIVATE_BUCKET="afs-private-files",
    )
    @patch(
        "apps.file_storage.management.commands.initialize_storage.storage_client"
    )
    def test_initializer_applies_public_policy_only(self, client_factory):
        client = client_factory.return_value

        call_command("initialize_storage", stdout=StringIO())

        self.assertEqual(client.head_bucket.call_count, 2)
        policy_call = client.put_bucket_policy.call_args.kwargs
        self.assertEqual(policy_call["Bucket"], "afs-public-media")
        policy = json.loads(policy_call["Policy"])
        self.assertEqual(
            policy["Statement"][0]["Resource"],
            ["arn:aws:s3:::afs-public-media/*"],
        )
        client.delete_bucket_policy.assert_called_once_with(
            Bucket="afs-private-files"
        )

    def test_local_file_migration_preserves_object_names(self):
        with (
            TemporaryDirectory() as public_source,
            TemporaryDirectory() as private_source,
            TemporaryDirectory() as public_target,
            TemporaryDirectory() as private_target,
        ):
            public_path = Path(public_source) / "content" / "photo.jpg"
            public_path.parent.mkdir(parents=True)
            public_path.write_bytes(b"public-image")
            private_path = Path(private_source) / "recruitment" / "cv.pdf"
            private_path.parent.mkdir(parents=True)
            private_path.write_bytes(b"private-cv")
            destination_storages = {
                "default": FileSystemStorage(location=public_target),
                "private": FileSystemStorage(location=private_target),
            }

            with (
                override_settings(
                    FILE_STORAGE_BACKEND="seaweedfs",
                    MEDIA_ROOT=public_source,
                    PRIVATE_MEDIA_ROOT=private_source,
                ),
                patch(
                    "apps.file_storage.management.commands."
                    "migrate_local_files.storages",
                    destination_storages,
                ),
            ):
                call_command("migrate_local_files", stdout=StringIO())

            self.assertEqual(
                (Path(public_target) / "content" / "photo.jpg").read_bytes(),
                b"public-image",
            )
            self.assertEqual(
                (Path(private_target) / "recruitment" / "cv.pdf").read_bytes(),
                b"private-cv",
            )
