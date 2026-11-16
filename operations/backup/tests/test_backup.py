import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from backup import (
    BackupError,
    fetch_restic_backup,
    load_and_verify_snapshot,
    restore_backup,
    sha256_file,
)


class BackupManifestTests(TestCase):
    def create_snapshot(self, root):
        snapshot = Path(root) / "20261116T120000Z-12345678"
        object_directory = snapshot / "objects" / "0"
        object_directory.mkdir(parents=True)
        database_path = snapshot / "database.dump"
        database_path.write_bytes(b"database backup")
        object_path = object_directory / "object.blob"
        object_path.write_bytes(b"stored file")
        database_hash, database_size = sha256_file(database_path)
        object_hash, object_size = sha256_file(object_path)
        manifest = {
            "format_version": 1,
            "backup_id": snapshot.name,
            "started_at": "2026-11-16T12:00:00+00:00",
            "completed_at": "2026-11-16T12:00:01+00:00",
            "application_version": "test",
            "database": {
                "engine": "postgresql",
                "database_name": "afs",
                "dump_format": "custom",
                "file": "database.dump",
                "size": database_size,
                "sha256": database_hash,
            },
            "storage": {
                "type": "s3-compatible-logical-export",
                "buckets": [
                    {
                        "name": "afs-public-media",
                        "object_count": 1,
                        "objects": [
                            {
                                "key": "content/image.gif",
                                "file": "objects/0/object.blob",
                                "size": object_size,
                                "sha256": object_hash,
                                "etag": "test-etag",
                                "metadata": {},
                            }
                        ],
                    },
                    {
                        "name": "afs-private-files",
                        "object_count": 0,
                        "objects": [],
                    },
                ],
            },
        }
        manifest_path = snapshot / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest_hash, _ = sha256_file(manifest_path)
        (snapshot / "manifest.sha256").write_text(
            f"{manifest_hash}  manifest.json\n",
            encoding="utf-8",
        )
        return snapshot

    def test_complete_snapshot_is_verified(self):
        with TemporaryDirectory() as directory:
            snapshot = self.create_snapshot(directory)

            manifest = load_and_verify_snapshot(snapshot)

            self.assertEqual(manifest["backup_id"], snapshot.name)
            self.assertEqual(
                manifest["storage"]["buckets"][0]["object_count"],
                1,
            )

    def test_tampered_object_is_rejected(self):
        with TemporaryDirectory() as directory:
            snapshot = self.create_snapshot(directory)
            object_path = snapshot / "objects" / "0" / "object.blob"
            object_path.write_bytes(b"stored fIle")

            with self.assertRaisesRegex(BackupError, "Incorrect checksum"):
                load_and_verify_snapshot(snapshot)

    def test_manifest_path_escape_is_rejected(self):
        with TemporaryDirectory() as directory:
            snapshot = self.create_snapshot(directory)
            manifest_path = snapshot / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["storage"]["buckets"][0]["objects"][0]["file"] = (
                "../../outside.blob"
            )
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            manifest_hash, _ = sha256_file(manifest_path)
            (snapshot / "manifest.sha256").write_text(
                f"{manifest_hash}  manifest.json\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(BackupError, "Unsafe path"):
                load_and_verify_snapshot(snapshot)

    def test_restore_requires_exact_confirmation(self):
        with self.assertRaisesRegex(BackupError, "exactly match"):
            restore_backup(
                None,
                "backup-id",
                restore_database_selected=True,
                restore_storage_selected=True,
                confirmation="different-id",
                allow_nonempty=False,
            )

    def test_restore_requires_an_explicit_component(self):
        with self.assertRaisesRegex(BackupError, "Select database"):
            restore_backup(
                None,
                "backup-id",
                restore_database_selected=False,
                restore_storage_selected=False,
                confirmation="backup-id",
                allow_nonempty=False,
            )

    @patch("backup.run_restic")
    def test_restic_fetch_verifies_and_places_snapshot(self, run_restic_mock):
        with TemporaryDirectory() as directory:
            backup_root = Path(directory)
            config = Mock()
            config.backup_root = backup_root
            config.snapshots_root = backup_root / "snapshots"

            def restore_snapshot(_config, arguments):
                target = Path(arguments[arguments.index("--target") + 1])
                restored_root = target / "backups" / "snapshots"
                self.create_snapshot(restored_root)

            run_restic_mock.side_effect = restore_snapshot
            backup_id = "20261116T120000Z-12345678"

            fetch_restic_backup(config, backup_id)

            restored = config.snapshots_root / backup_id
            self.assertTrue(restored.is_dir())
            load_and_verify_snapshot(restored)
            config.require_restic.assert_called_once_with()

    def test_restic_fetch_rejects_invalid_backup_id(self):
        with self.assertRaisesRegex(BackupError, "backup ID is invalid"):
            fetch_restic_backup(None, "../unsafe")
