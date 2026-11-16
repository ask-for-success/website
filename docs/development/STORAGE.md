# File storage

SeaweedFS is the implemented self-hosted object-storage service. It runs inside Docker and exposes an S3-compatible API to Django. PostgreSQL stores file paths and metadata; it never stores file bytes.

## Storage boundaries

| Storage | Bucket | Access |
|---|---|---|
| CMS images, event images, and public presentation thumbnails | `afs-public-media` | Anonymous read; authenticated Django writes |
| Candidate CVs and future private documents | `afs-private-files` | Authenticated Django access only; no public URL |

Gallery videos remain on YouTube and are embedded by URL. They are not uploaded to SeaweedFS.

The API contracts do not depend on the storage implementation. Public image fields return the configured public media URL. CV downloads continue through the protected recruitment endpoint, where applicant-or-HR authorization is checked before Django reads the private object.

## Local Docker environment

Start the complete stack:

```powershell
docker compose up -d --build
```

Docker starts PostgreSQL, SeaweedFS, an idempotent bucket-initialization job, and Django. The SeaweedFS S3 endpoint is bound to Windows loopback at `http://localhost:8333`. Its data persists in the `seaweedfs_data` Docker volume.

The default public media base is:

```text
http://localhost:8333/afs-public-media
```

Inspect service health and initialization:

```powershell
docker compose ps -a
docker compose logs storage-init seaweedfs
```

The `storage-init` service is expected to exit with code `0` after creating or finding both buckets and applying their access policies. It runs again safely whenever the stack is recreated.

## Local web interfaces

SeaweedFS exposes its management interfaces only on the Windows loopback address. They are available from this computer but are not published to other devices on the network:

| Interface | Local URL | Purpose |
|---|---|---|
| Admin UI | `http://localhost:12535` | Storage administration, maintenance, and service status |
| Filer UI | `http://localhost:8888/buckets/` | Browse public and private bucket objects |
| Master UI | `http://localhost:9333` | Inspect cluster topology and volume status |
| S3 endpoint | `http://localhost:8333` | Application API endpoint; not a dashboard |

The Admin UI uses `AFS_SEAWEEDFS_ADMIN_PASSWORD`. The default value in `compose.yaml` is for local development only and must be replaced before any non-local deployment. The Filer and Master interfaces must remain private in production.

## Configuration

Copy `.env.example` to `.env` and replace every development secret before a non-local deployment.

| Variable | Purpose |
|---|---|
| `AFS_STORAGE_BACKEND` | `seaweedfs` for object storage or `filesystem` for a standalone Django fallback. |
| `AFS_STORAGE_S3_ENDPOINT_URL` | Internal S3 endpoint used by Django. |
| `AFS_STORAGE_PUBLIC_BASE_URL` | Browser-facing base URL for public media. |
| `AFS_STORAGE_ACCESS_KEY` | S3 access key. |
| `AFS_STORAGE_SECRET_KEY` | S3 secret key. |
| `AFS_STORAGE_PUBLIC_BUCKET` | Public media bucket name. |
| `AFS_STORAGE_PRIVATE_BUCKET` | Private document bucket name. |
| `AFS_STORAGE_REGION` | S3 signing region. |
| `AFS_STORAGE_S3_HOST_PORT` | Loopback port used by local development. |
| `AFS_SEAWEEDFS_ADMIN_PASSWORD` | SeaweedFS administration password. |
| `AFS_SEAWEEDFS_ADMIN_HOST_PORT` | Local Admin UI port. |
| `AFS_SEAWEEDFS_FILER_HOST_PORT` | Local Filer UI port. |
| `AFS_SEAWEEDFS_MASTER_HOST_PORT` | Local Master UI port. |

`compose.yaml` deliberately supplies the internal endpoint as `http://seaweedfs:8333`. In production, `AFS_STORAGE_PUBLIC_BASE_URL` must be the HTTPS media URL exposed by the organization's reverse proxy, not an internal Docker hostname.

## Existing local files

The migration command copies files without deleting the local originals and preserves their exact relative names so database references remain valid.

Preview the work:

```powershell
docker compose exec backend python manage.py migrate_local_files --dry-run
```

Copy files that do not already exist:

```powershell
docker compose exec backend python manage.py migrate_local_files
```

Use `--overwrite` only when existing objects at the same keys must deliberately be replaced.

## Production requirements

Before production traffic, the team must:

- replace all development credentials with secrets managed outside version control;
- publish public media through an HTTPS reverse proxy while keeping SeaweedFS administration and private buckets off the public network;
- back up the `seaweedfs_data` volume to an independent destination and test restoration;
- monitor storage capacity, service health, and failed uploads;
- define retention and recovery procedures for public media and private documents.

Do not remove the persistent volume until its contents have been backed up and the deletion is explicitly approved.
