from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Copy existing local public and private files into SeaweedFS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List files without uploading them.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace objects that already exist at the same key.",
        )

    def handle(self, *args, **options):
        if settings.FILE_STORAGE_BACKEND != "seaweedfs":
            raise CommandError(
                "Set AFS_STORAGE_BACKEND=seaweedfs before migrating files."
            )

        totals = {"uploaded": 0, "skipped": 0, "planned": 0}
        storage_roots = (
            ("public", Path(settings.MEDIA_ROOT), storages["default"]),
            ("private", Path(settings.PRIVATE_MEDIA_ROOT), storages["private"]),
        )
        for label, source_root, destination in storage_roots:
            if not source_root.exists():
                self.stdout.write(f"No local {label} directory at {source_root}.")
                continue
            source_files = sorted(
                path for path in source_root.rglob("*") if path.is_file()
            )
            for source_path in source_files:
                object_name = source_path.relative_to(source_root).as_posix()
                if options["dry_run"]:
                    totals["planned"] += 1
                    self.stdout.write(f"Would upload {label}: {object_name}")
                    continue
                if destination.exists(object_name):
                    if not options["overwrite"]:
                        totals["skipped"] += 1
                        continue
                    destination.delete(object_name)
                with source_path.open("rb") as source_file:
                    saved_name = destination.save(
                        object_name,
                        File(source_file, name=object_name),
                    )
                if saved_name != object_name:
                    raise CommandError(
                        f"Storage changed {object_name} to {saved_name}; "
                        "database file references would become invalid."
                    )
                totals["uploaded"] += 1

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete: {totals['planned']} files found."
                )
            )
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Migration complete: {totals['uploaded']} uploaded, "
                f"{totals['skipped']} already present."
            )
        )
