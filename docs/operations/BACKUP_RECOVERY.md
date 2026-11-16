# Backup and recovery

This document is the source of truth for protecting and recovering PostgreSQL
and SeaweedFS data. Docker volumes provide persistence but are not backups.

## Implemented backup package

The `backup` Docker Compose service creates one portable backup set containing:

- a PostgreSQL custom-format logical dump;
- every object from the public SeaweedFS bucket;
- every object from the private SeaweedFS bucket;
- object keys, sizes, checksums, content metadata, and relevant HTTP headers;
- a versioned JSON manifest and a checksum for that manifest.

The export uses the S3-compatible API instead of copying SeaweedFS internal
volume files. A backup can therefore be restored into a new SeaweedFS instance
without depending on the original Docker volume layout.

The package does not store application secrets, environment files, source code,
or SeaweedFS bucket policies. Source code remains in Git, secrets must be held in
the production secret manager, and the idempotent `initialize_storage` command
recreates the approved bucket policies.

## Consistency requirement

A complete backup must represent PostgreSQL and object storage at the same
logical moment. Pause application writes before creating a backup and keep them
paused until the command succeeds. For local validation this can be done with:

```powershell
docker compose stop backend
docker compose --profile operations run --rm backup create
docker compose start backend
```

Production must use a maintenance or write-drain procedure at the reverse proxy
or application layer. Do not rely on copying a running PostgreSQL or SeaweedFS
Docker volume.

## Build and test the package

Build the dedicated image:

```powershell
docker compose --profile operations build backup
```

Run its isolated unit tests:

```powershell
docker compose --profile operations run --rm `
  --entrypoint /opt/afs-backup-venv/bin/python `
  backup -m unittest discover -s tests -v
```

The image contains the PostgreSQL 17 client, the pinned S3 client, Restic, and
the backup utility. It does not run during normal application startup.

## Local backup commands

Create and verify a local backup set:

```powershell
docker compose --profile operations run --rm backup create
```

List local sets and verify each manifest:

```powershell
docker compose --profile operations run --rm backup list
```

Verify one set and every contained file:

```powershell
docker compose --profile operations run --rm backup verify BACKUP_ID
```

Local sets are written below `AFS_BACKUP_HOST_PATH`, which defaults to the
ignored `backups/` directory. These logical sets contain private personal data
in readable form. Production staging must use an encrypted disk, strict file
permissions, and short retention. A local copy on the production server does
not satisfy the off-host backup requirement.

## Encrypted remote repository

The future association-controlled server can be connected without changing the
backup utility. DevOps will provide:

- a Restic repository such as `sftp:backup@backup-host:/srv/afs-backups`;
- an SSH private key and pinned `known_hosts` file mounted read-only;
- a Restic password file mounted as a Docker secret;
- firewall rules that allow the production host to reach only the backup host;
- independent monitoring and capacity limits on the backup host.

Set `AFS_BACKUP_REPOSITORY` and the in-container
`AFS_BACKUP_PASSWORD_FILE` path through production secrets. Initialize the
encrypted repository exactly once:

```powershell
docker compose --profile operations run --rm backup restic-init
```

After configuration, every `create` command verifies the local set and copies
it into the encrypted Restic repository. Apply retention with:

```powershell
docker compose --profile operations run --rm backup restic-retention
```

The default policy keeps 14 daily, 8 weekly, and 12 monthly snapshots. DevOps
may change the three `AFS_BACKUP_RETENTION_*` values after capacity review.

Verify repository metadata and all encrypted backup data with:

```powershell
docker compose --profile operations run --rm backup restic-check
```

List the association backups held in the encrypted repository:

```powershell
docker compose --profile operations run --rm backup restic-list
```

Fetch one selected backup into the local recovery area and verify every file:

```powershell
docker compose --profile operations run --rm backup `
  restic-fetch BACKUP_ID
```

The fetch command rejects malformed identifiers, existing local destinations,
missing manifests, and any checksum failure. It never restores directly into a
live database or live bucket.

The Restic password must not exist only on the production server. At least two
authorized association administrators must hold protected recovery copies.

## Guarded restore

Restoration is intentionally refused unless all of these conditions are met:

- the backup manifest and every database and object checksum are valid;
- the confirmation value exactly matches the backup ID;
- at least one restore component is explicitly selected;
- the target database and target buckets are empty.

Point the backup service at a clean, isolated recovery PostgreSQL database and
SeaweedFS instance, then run:

```powershell
docker compose --profile operations run --rm backup restore BACKUP_ID `
  --database --storage --confirm-backup-id BACKUP_ID
```

After restoration, apply the storage policies and validate the application:

```powershell
docker compose run --rm backend python manage.py initialize_storage
docker compose run --rm backend python manage.py migrate --check
docker compose run --rm backend python manage.py check
```

`--allow-nonempty-target` enables destructive replacement in a non-empty
target. It exists for supervised disaster recovery only and must never be used
for routine validation.

## Isolated local restore validation

`compose.recovery.yaml` creates a separate Compose project with temporary
PostgreSQL and SeaweedFS data. It publishes no host ports, does not connect to
the development services, and loses all recovered data when the isolated
project is removed.

Point `AFS_BACKUP_HOST_PATH` at the directory containing `snapshots/`, then
start the clean recovery services:

```powershell
docker compose -p afs-recovery -f compose.recovery.yaml `
  --profile recovery up -d --build recovery-database recovery-seaweedfs
```

Restore one verified backup:

```powershell
docker compose -p afs-recovery -f compose.recovery.yaml `
  --profile recovery run --rm recovery-restore restore BACKUP_ID `
  --database --storage --confirm-backup-id BACKUP_ID
```

Inspect the restored database when required:

```powershell
docker compose -p afs-recovery -f compose.recovery.yaml `
  exec recovery-database psql -U afs_recovery -d afs_recovery -c "\dt"
```

Remove only the isolated recovery project after validation:

```powershell
docker compose -p afs-recovery -f compose.recovery.yaml `
  --profile recovery down
```

## Required recovery validation

Before production launch, the DevOps team must complete and record a recovery
exercise on an isolated host:

1. retrieve one encrypted backup with `restic-fetch`;
2. verify the complete repository and selected backup set;
3. restore PostgreSQL and both SeaweedFS buckets into clean services;
4. apply bucket policies and start the matching application version;
5. verify authentication, CMS images, candidate CV authorization, membership,
   recruitment, events, donations, and audit records;
6. record actual recovery time and any missing operational step;
7. destroy the isolated recovery environment securely.

The off-host backup requirement remains incomplete until this exercise succeeds.
