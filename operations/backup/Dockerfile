FROM restic/restic:0.19.1@sha256:136600b6ff6843d61d355f7f71f460a166429f35de6fd11b568fece3c9a4d510 AS restic

FROM postgres:17-bookworm

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        openssh-client \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY --from=restic /usr/bin/restic /usr/local/bin/restic

RUN python3 -m venv /opt/afs-backup-venv

COPY operations/backup/requirements.txt /tmp/backup-requirements.txt
RUN /opt/afs-backup-venv/bin/pip install \
    --no-cache-dir \
    -r /tmp/backup-requirements.txt

WORKDIR /opt/afs-backup
COPY operations/backup /opt/afs-backup

ENTRYPOINT ["/opt/afs-backup-venv/bin/python", "/opt/afs-backup/backup.py"]
CMD ["create"]
