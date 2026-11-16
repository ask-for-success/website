import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError


MANIFEST_FORMAT_VERSION = 1
CHUNK_SIZE = 1024 * 1024
BACKUP_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")


class BackupError(RuntimeError):
    pass


def environment_value(name, default=None, *, required=False):
    value = os.getenv(name, default)
    if required and not value:
        raise BackupError(f"Missing required environment variable: {name}")
    return value


def environment_integer(name, default):
    value = environment_value(name, str(default))
    try:
        parsed = int(value)
    except ValueError as error:
        raise BackupError(f"{name} must be an integer.") from error
    if parsed < 1:
        raise BackupError(f"{name} must be greater than zero.")
    return parsed


@dataclass(frozen=True)
class BackupConfig:
    backup_root: Path
    application_version: str
    database_host: str
    database_port: str
    database_name: str
    database_user: str
    database_password: str
    storage_endpoint: str
    storage_access_key: str
    storage_secret_key: str
    storage_region: str
    public_bucket: str
    private_bucket: str
    restic_repository: str
    restic_password_file: str
    retention_daily: int
    retention_weekly: int
    retention_monthly: int

    @classmethod
    def from_environment(cls):
        return cls(
            backup_root=Path(
                environment_value("AFS_BACKUP_ROOT", "/backups")
            ).resolve(),
            application_version=environment_value(
                "AFS_BACKUP_APP_VERSION",
                "unknown",
            ),
            database_host=environment_value(
                "AFS_DB_HOST",
                "database",
            ),
            database_port=environment_value("AFS_DB_PORT", "5432"),
            database_name=environment_value(
                "AFS_DB_NAME",
                required=True,
            ),
            database_user=environment_value(
                "AFS_DB_USER",
                required=True,
            ),
            database_password=environment_value(
                "AFS_DB_PASSWORD",
                required=True,
            ),
            storage_endpoint=environment_value(
                "AFS_STORAGE_S3_ENDPOINT_URL",
                required=True,
            ).rstrip("/"),
            storage_access_key=environment_value(
                "AFS_STORAGE_ACCESS_KEY",
                required=True,
            ),
            storage_secret_key=environment_value(
                "AFS_STORAGE_SECRET_KEY",
                required=True,
            ),
            storage_region=environment_value(
                "AFS_STORAGE_REGION",
                "us-east-1",
            ),
            public_bucket=environment_value(
                "AFS_STORAGE_PUBLIC_BUCKET",
                "afs-public-media",
            ),
            private_bucket=environment_value(
                "AFS_STORAGE_PRIVATE_BUCKET",
                "afs-private-files",
            ),
            restic_repository=environment_value(
                "AFS_BACKUP_REPOSITORY",
                "",
            ),
            restic_password_file=environment_value(
                "AFS_BACKUP_PASSWORD_FILE",
                "",
            ),
            retention_daily=environment_integer(
                "AFS_BACKUP_RETENTION_DAILY",
                14,
            ),
            retention_weekly=environment_integer(
                "AFS_BACKUP_RETENTION_WEEKLY",
                8,
            ),
            retention_monthly=environment_integer(
                "AFS_BACKUP_RETENTION_MONTHLY",
                12,
            ),
        )

    @property
    def snapshots_root(self):
        return self.backup_root / "snapshots"

    def postgres_environment(self):
        environment = os.environ.copy()
        environment["PGPASSWORD"] = self.database_password
        return environment

    def require_restic(self):
        if not self.restic_repository:
            raise BackupError("AFS_BACKUP_REPOSITORY is not configured.")
        if not self.restic_password_file:
            raise BackupError("AFS_BACKUP_PASSWORD_FILE is not configured.")
        password_file = Path(self.restic_password_file)
        if not password_file.is_file():
            raise BackupError(
                "The configured Restic password file is not available."
            )


def utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def generate_backup_id():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def relative_file(snapshot_directory, relative_path):
    snapshot_root = Path(snapshot_directory).resolve()
    candidate = (snapshot_root / relative_path).resolve()
    if not candidate.is_relative_to(snapshot_root):
        raise BackupError(f"Unsafe path in backup manifest: {relative_path}")
    return candidate


def run_command(arguments, *, environment=None, capture_output=False):
    try:
        return subprocess.run(
            arguments,
            check=True,
            env=environment,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as error:
        raise BackupError(f"Required executable not found: {arguments[0]}") from error
    except subprocess.CalledProcessError as error:
        message = (error.stderr or error.stdout or str(error)).strip()
        raise BackupError(
            f"Command failed ({arguments[0]}): {message}"
        ) from error


def create_storage_client(config):
    return boto3.client(
        "s3",
        endpoint_url=config.storage_endpoint,
        aws_access_key_id=config.storage_access_key,
        aws_secret_access_key=config.storage_secret_key,
        region_name=config.storage_region,
        config=BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def backup_database(config, snapshot_directory):
    dump_path = Path(snapshot_directory) / "database.dump"
    run_command(
        [
            "pg_dump",
            "--host",
            config.database_host,
            "--port",
            config.database_port,
            "--username",
            config.database_user,
            "--dbname",
            config.database_name,
            "--format",
            "custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(dump_path),
        ],
        environment=config.postgres_environment(),
    )
    digest, size = sha256_file(dump_path)
    return {
        "engine": "postgresql",
        "database_name": config.database_name,
        "dump_format": "custom",
        "file": dump_path.name,
        "size": size,
        "sha256": digest,
    }


def normalized_etag(value):
    return value.strip('"') if value else ""


def optional_object_headers(response):
    header_names = {
        "CacheControl": "cache_control",
        "ContentDisposition": "content_disposition",
        "ContentEncoding": "content_encoding",
        "ContentLanguage": "content_language",
        "ContentType": "content_type",
    }
    return {
        manifest_name: response.get(response_name)
        for response_name, manifest_name in header_names.items()
        if response.get(response_name) is not None
    }


def backup_bucket(client, bucket_name, bucket_index, snapshot_directory):
    destination = Path(snapshot_directory) / "objects" / str(bucket_index)
    destination.mkdir(parents=True, exist_ok=True)
    object_records = []
    paginator = client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket_name):
        for source_record in page.get("Contents", []):
            key = source_record["Key"]
            key_digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
            relative_path = Path("objects") / str(bucket_index) / (
                f"{key_digest}.blob"
            )
            object_path = Path(snapshot_directory) / relative_path
            response = client.get_object(Bucket=bucket_name, Key=key)
            body = response["Body"]
            digest = hashlib.sha256()
            size = 0
            try:
                with object_path.open("wb") as destination_file:
                    for chunk in body.iter_chunks(chunk_size=CHUNK_SIZE):
                        if not chunk:
                            continue
                        destination_file.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
            finally:
                body.close()

            expected_size = source_record.get("Size")
            expected_etag = normalized_etag(source_record.get("ETag"))
            actual_etag = normalized_etag(response.get("ETag"))
            if expected_size is not None and expected_size != size:
                raise BackupError(
                    f"Object changed during backup: {bucket_name}/{key}"
                )
            if expected_etag and actual_etag and expected_etag != actual_etag:
                raise BackupError(
                    f"Object changed during backup: {bucket_name}/{key}"
                )

            record = {
                "key": key,
                "file": relative_path.as_posix(),
                "size": size,
                "sha256": digest.hexdigest(),
                "etag": actual_etag,
                "metadata": response.get("Metadata", {}),
            }
            record.update(optional_object_headers(response))
            object_records.append(record)

    object_records.sort(key=lambda record: record["key"])
    return {
        "name": bucket_name,
        "object_count": len(object_records),
        "objects": object_records,
    }


def write_manifest(snapshot_directory, manifest):
    manifest_path = Path(snapshot_directory) / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    digest, _ = sha256_file(manifest_path)
    checksum_path = Path(snapshot_directory) / "manifest.sha256"
    checksum_path.write_text(
        f"{digest}  manifest.json\n",
        encoding="utf-8",
    )


def verify_file(snapshot_directory, record, label):
    file_path = relative_file(snapshot_directory, record["file"])
    if not file_path.is_file():
        raise BackupError(f"Missing {label} file: {record['file']}")
    digest, size = sha256_file(file_path)
    if size != record["size"]:
        raise BackupError(f"Incorrect size for {label}: {record['file']}")
    if digest != record["sha256"]:
        raise BackupError(f"Incorrect checksum for {label}: {record['file']}")


def load_and_verify_snapshot(snapshot_directory):
    snapshot_directory = Path(snapshot_directory).resolve()
    manifest_path = snapshot_directory / "manifest.json"
    checksum_path = snapshot_directory / "manifest.sha256"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise BackupError("The backup manifest or its checksum is missing.")

    checksum_parts = checksum_path.read_text(encoding="utf-8").split()
    if len(checksum_parts) != 2 or checksum_parts[1] != "manifest.json":
        raise BackupError("The manifest checksum file is invalid.")
    manifest_digest, _ = sha256_file(manifest_path)
    if manifest_digest != checksum_parts[0]:
        raise BackupError("The backup manifest checksum does not match.")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise BackupError("The backup manifest is not valid JSON.") from error
    if manifest.get("format_version") != MANIFEST_FORMAT_VERSION:
        raise BackupError("The backup manifest format is not supported.")
    if manifest.get("backup_id") != snapshot_directory.name:
        raise BackupError("The backup ID does not match its directory name.")

    verify_file(
        snapshot_directory,
        manifest["database"],
        "database dump",
    )
    referenced_files = {manifest["database"]["file"]}
    for bucket in manifest["storage"]["buckets"]:
        objects = bucket.get("objects", [])
        if bucket.get("object_count") != len(objects):
            raise BackupError(
                f"Object count mismatch for bucket: {bucket.get('name')}"
            )
        for object_record in objects:
            if object_record["file"] in referenced_files:
                raise BackupError(
                    f"Duplicate file reference: {object_record['file']}"
                )
            referenced_files.add(object_record["file"])
            verify_file(
                snapshot_directory,
                object_record,
                f"object {bucket['name']}/{object_record['key']}",
            )
    return manifest


def restic_arguments(config):
    config.require_restic()
    return [
        "restic",
        "--repo",
        config.restic_repository,
        "--password-file",
        config.restic_password_file,
    ]


def run_restic(config, arguments):
    run_command(restic_arguments(config) + arguments)


def create_backup(config):
    if config.restic_repository:
        config.require_restic()
    config.snapshots_root.mkdir(parents=True, exist_ok=True)
    backup_id = generate_backup_id()
    partial_directory = config.snapshots_root / f".partial-{backup_id}"
    final_directory = config.snapshots_root / backup_id
    partial_directory.mkdir()
    started_at = utc_timestamp()

    try:
        database_record = backup_database(config, partial_directory)
        storage_client = create_storage_client(config)
        bucket_records = [
            backup_bucket(
                storage_client,
                config.public_bucket,
                0,
                partial_directory,
            ),
            backup_bucket(
                storage_client,
                config.private_bucket,
                1,
                partial_directory,
            ),
        ]
        manifest = {
            "format_version": MANIFEST_FORMAT_VERSION,
            "backup_id": backup_id,
            "started_at": started_at,
            "completed_at": utc_timestamp(),
            "application_version": config.application_version,
            "database": database_record,
            "storage": {
                "type": "s3-compatible-logical-export",
                "buckets": bucket_records,
            },
        }
        write_manifest(partial_directory, manifest)
        partial_directory.rename(final_directory)
        try:
            load_and_verify_snapshot(final_directory)
        except Exception:
            shutil.rmtree(final_directory)
            raise
        if config.restic_repository:
            run_restic(
                config,
                [
                    "backup",
                    str(final_directory),
                    "--tag",
                    "afs",
                    "--tag",
                    backup_id,
                ],
            )
    except Exception:
        if partial_directory.exists():
            shutil.rmtree(partial_directory)
        raise

    print(f"Created and verified backup: {backup_id}")
    if config.restic_repository:
        print("Copied the backup to the configured encrypted Restic repository.")
    else:
        print(
            "No Restic repository is configured; the verified snapshot remains "
            "on local backup storage."
        )
    return backup_id


def snapshot_directory(config, backup_id):
    if not BACKUP_ID_PATTERN.fullmatch(backup_id or ""):
        raise BackupError("The backup ID is invalid.")
    candidate = (config.snapshots_root / backup_id).resolve()
    if not candidate.is_relative_to(config.snapshots_root.resolve()):
        raise BackupError("The backup ID is invalid.")
    if not candidate.is_dir():
        raise BackupError(f"Backup not found: {backup_id}")
    return candidate


def fetch_restic_backup(config, backup_id):
    if not BACKUP_ID_PATTERN.fullmatch(backup_id or ""):
        raise BackupError("The backup ID is invalid.")
    config.require_restic()
    config.snapshots_root.mkdir(parents=True, exist_ok=True)
    final_directory = config.snapshots_root / backup_id
    if final_directory.exists():
        raise BackupError(f"A local backup already exists: {backup_id}")

    staging_root = config.backup_root / f".restic-fetch-{uuid.uuid4().hex}"
    staging_root.mkdir(parents=True)
    try:
        run_restic(
            config,
            [
                "restore",
                "latest",
                "--tag",
                backup_id,
                "--target",
                str(staging_root),
            ],
        )
        candidates = [
            manifest_path.parent
            for manifest_path in staging_root.rglob("manifest.json")
            if manifest_path.parent.name == backup_id
        ]
        if len(candidates) != 1:
            raise BackupError(
                "The selected Restic snapshot does not contain exactly one "
                "matching backup set."
            )
        source_directory = candidates[0]
        load_and_verify_snapshot(source_directory)
        source_directory.rename(final_directory)
        try:
            load_and_verify_snapshot(final_directory)
        except Exception:
            shutil.rmtree(final_directory)
            raise
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)

    print(f"Fetched and verified backup: {backup_id}")


def list_backups(config):
    if not config.snapshots_root.exists():
        print("No local backups are available.")
        return
    found = False
    for candidate in sorted(config.snapshots_root.iterdir()):
        if not candidate.is_dir() or candidate.name.startswith("."):
            continue
        found = True
        try:
            manifest = load_and_verify_snapshot(candidate)
            print(
                f"{manifest['backup_id']}  {manifest['completed_at']}  verified"
            )
        except BackupError as error:
            print(f"{candidate.name}  INVALID  {error}")
    if not found:
        print("No local backups are available.")


def database_table_count(config):
    result = run_command(
        [
            "psql",
            "--host",
            config.database_host,
            "--port",
            config.database_port,
            "--username",
            config.database_user,
            "--dbname",
            config.database_name,
            "--tuples-only",
            "--no-align",
            "--command",
            (
                "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN "
                "('pg_catalog', 'information_schema');"
            ),
        ],
        environment=config.postgres_environment(),
        capture_output=True,
    )
    try:
        return int(result.stdout.strip())
    except ValueError as error:
        raise BackupError("Unable to inspect the target database.") from error


def restore_database(config, snapshot_directory, manifest, allow_nonempty):
    table_count = database_table_count(config)
    if table_count and not allow_nonempty:
        raise BackupError(
            "The target database is not empty. Use a clean recovery database "
            "or explicitly allow a non-empty target."
        )
    arguments = [
        "pg_restore",
        "--host",
        config.database_host,
        "--port",
        config.database_port,
        "--username",
        config.database_user,
        "--dbname",
        config.database_name,
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
    ]
    if allow_nonempty:
        arguments.extend(["--clean", "--if-exists"])
    dump_path = relative_file(snapshot_directory, manifest["database"]["file"])
    arguments.append(str(dump_path))
    run_command(arguments, environment=config.postgres_environment())


def ensure_bucket(client, bucket_name):
    try:
        client.head_bucket(Bucket=bucket_name)
    except ClientError as error:
        status_code = error.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        if status_code != 404:
            raise
        client.create_bucket(Bucket=bucket_name)


def bucket_has_objects(client, bucket_name):
    response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
    return bool(response.get("Contents"))


def validate_storage_target(config, manifest, allow_nonempty):
    configured_buckets = {config.public_bucket, config.private_bucket}
    backup_buckets = {
        bucket["name"] for bucket in manifest["storage"]["buckets"]
    }
    if backup_buckets != configured_buckets:
        raise BackupError(
            "The backup bucket names do not match the configured recovery "
            "bucket names."
        )
    client = create_storage_client(config)
    for bucket in manifest["storage"]["buckets"]:
        bucket_name = bucket["name"]
        ensure_bucket(client, bucket_name)
        if bucket_has_objects(client, bucket_name) and not allow_nonempty:
            raise BackupError(
                f"The target bucket is not empty: {bucket_name}. Use clean "
                "recovery buckets or explicitly allow a non-empty target."
            )
    return client


def restore_storage(
    config,
    snapshot_directory,
    manifest,
    allow_nonempty,
    client=None,
):
    if client is None:
        client = validate_storage_target(config, manifest, allow_nonempty)
    for bucket in manifest["storage"]["buckets"]:
        bucket_name = bucket["name"]
        for object_record in bucket["objects"]:
            object_path = relative_file(
                snapshot_directory,
                object_record["file"],
            )
            parameters = {
                "Bucket": bucket_name,
                "Key": object_record["key"],
                "Metadata": object_record.get("metadata", {}),
            }
            optional_parameters = {
                "cache_control": "CacheControl",
                "content_disposition": "ContentDisposition",
                "content_encoding": "ContentEncoding",
                "content_language": "ContentLanguage",
                "content_type": "ContentType",
            }
            for manifest_name, request_name in optional_parameters.items():
                if manifest_name in object_record:
                    parameters[request_name] = object_record[manifest_name]
            with object_path.open("rb") as source:
                parameters["Body"] = source
                client.put_object(**parameters)
            restored = client.head_object(
                Bucket=bucket_name,
                Key=object_record["key"],
            )
            if restored["ContentLength"] != object_record["size"]:
                raise BackupError(
                    f"Restored object size mismatch: "
                    f"{bucket_name}/{object_record['key']}"
                )


def restore_backup(
    config,
    backup_id,
    *,
    restore_database_selected,
    restore_storage_selected,
    confirmation,
    allow_nonempty,
):
    if confirmation != backup_id:
        raise BackupError(
            "Restore confirmation must exactly match the backup ID."
        )
    if not restore_database_selected and not restore_storage_selected:
        raise BackupError("Select database, storage, or both for restoration.")
    directory = snapshot_directory(config, backup_id)
    manifest = load_and_verify_snapshot(directory)
    storage_client = None
    if restore_database_selected:
        table_count = database_table_count(config)
        if table_count and not allow_nonempty:
            raise BackupError(
                "The target database is not empty. Use a clean recovery "
                "database or explicitly allow a non-empty target."
            )
    if restore_storage_selected:
        storage_client = validate_storage_target(
            config,
            manifest,
            allow_nonempty,
        )
    if restore_database_selected:
        restore_database(config, directory, manifest, allow_nonempty)
    if restore_storage_selected:
        restore_storage(
            config,
            directory,
            manifest,
            allow_nonempty,
            client=storage_client,
        )
    print(f"Restored selected components from backup: {backup_id}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create, verify, and restore Ask For Success backups."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create", help="Create and verify a backup set.")
    commands.add_parser("list", help="List and verify local backup sets.")

    verify = commands.add_parser("verify", help="Verify one local backup set.")
    verify.add_argument("backup_id")

    restore = commands.add_parser(
        "restore",
        help="Restore selected data into a clean recovery target.",
    )
    restore.add_argument("backup_id")
    restore.add_argument("--database", action="store_true")
    restore.add_argument("--storage", action="store_true")
    restore.add_argument("--confirm-backup-id", required=True)
    restore.add_argument(
        "--allow-nonempty-target",
        action="store_true",
        help="Allow destructive replacement in a non-empty recovery target.",
    )

    commands.add_parser(
        "restic-init",
        help="Initialize the configured encrypted Restic repository.",
    )
    commands.add_parser(
        "restic-check",
        help="Verify the configured Restic repository and stored data.",
    )
    commands.add_parser(
        "restic-list",
        help="List Ask For Success snapshots in the Restic repository.",
    )
    restic_fetch = commands.add_parser(
        "restic-fetch",
        help="Fetch and verify one backup from the Restic repository.",
    )
    restic_fetch.add_argument("backup_id")
    commands.add_parser(
        "restic-retention",
        help="Apply the configured daily, weekly, and monthly retention policy.",
    )
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    config = BackupConfig.from_environment()

    if options.command == "create":
        create_backup(config)
    elif options.command == "list":
        list_backups(config)
    elif options.command == "verify":
        directory = snapshot_directory(config, options.backup_id)
        load_and_verify_snapshot(directory)
        print(f"Backup is valid: {options.backup_id}")
    elif options.command == "restore":
        restore_backup(
            config,
            options.backup_id,
            restore_database_selected=options.database,
            restore_storage_selected=options.storage,
            confirmation=options.confirm_backup_id,
            allow_nonempty=options.allow_nonempty_target,
        )
    elif options.command == "restic-init":
        run_restic(config, ["init"])
    elif options.command == "restic-check":
        run_restic(config, ["check", "--read-data"])
    elif options.command == "restic-list":
        run_restic(config, ["snapshots", "--tag", "afs"])
    elif options.command == "restic-fetch":
        fetch_restic_backup(config, options.backup_id)
    elif options.command == "restic-retention":
        run_restic(
            config,
            [
                "forget",
                "--tag",
                "afs",
                "--keep-daily",
                str(config.retention_daily),
                "--keep-weekly",
                str(config.retention_weekly),
                "--keep-monthly",
                str(config.retention_monthly),
                "--prune",
            ],
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BackupError, ClientError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
