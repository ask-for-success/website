import json

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def storage_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.SEAWEEDFS_ENDPOINT_URL,
        aws_access_key_id=settings.SEAWEEDFS_ACCESS_KEY,
        aws_secret_access_key=settings.SEAWEEDFS_SECRET_KEY,
        region_name=settings.SEAWEEDFS_REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def ensure_bucket(client, bucket_name):
    try:
        client.head_bucket(Bucket=bucket_name)
        return False
    except ClientError as error:
        status_code = error.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        if status_code != 404:
            raise
    client.create_bucket(Bucket=bucket_name)
    return True


class Command(BaseCommand):
    help = "Create and secure the configured SeaweedFS media buckets."

    def handle(self, *args, **options):
        if settings.FILE_STORAGE_BACKEND != "seaweedfs":
            self.stdout.write("SeaweedFS storage is disabled; nothing to initialize.")
            return

        client = storage_client()
        try:
            for bucket_name in (
                settings.SEAWEEDFS_PUBLIC_BUCKET,
                settings.SEAWEEDFS_PRIVATE_BUCKET,
            ):
                created = ensure_bucket(client, bucket_name)
                action = "Created" if created else "Found"
                self.stdout.write(f"{action} bucket {bucket_name}.")

            public_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicMediaRead",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [
                            f"arn:aws:s3:::{settings.SEAWEEDFS_PUBLIC_BUCKET}/*"
                        ],
                    }
                ],
            }
            client.put_bucket_policy(
                Bucket=settings.SEAWEEDFS_PUBLIC_BUCKET,
                Policy=json.dumps(public_policy),
            )
            try:
                client.delete_bucket_policy(
                    Bucket=settings.SEAWEEDFS_PRIVATE_BUCKET
                )
            except ClientError as error:
                status_code = error.response.get("ResponseMetadata", {}).get(
                    "HTTPStatusCode"
                )
                if status_code not in {404, 405, 501}:
                    raise
        except Exception as error:
            raise CommandError(
                f"Unable to initialize SeaweedFS storage: {error}"
            ) from error

        self.stdout.write(
            self.style.SUCCESS(
                "SeaweedFS public and private buckets are ready."
            )
        )
