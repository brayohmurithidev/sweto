# Database backups

Every night at 03:30 Nairobi time, each environment's database and its env
file are dumped, encrypted and copied off the server.

| What | Where | Kept |
|---|---|---|
| Encrypted backup | `/var/backups/sweto/<env>/sweto_<env>-<UTC time>.tar.age` on the server | 14 days |
| Same file | `<bucket>/<env>/` in object storage (Contabo, private bucket) | 30 days |

Each backup is one [age](https://age-encryption.org)-encrypted tar with:

- `sweto_<env>.dump`: `pg_dump --format=custom`, restored with `pg_restore`;
- `<env>.env`: the API settings, including `MPESA_CREDENTIALS_KEY`. Without
  that key the gyms' saved M-Pesa passkeys can't be decrypted after a
  restore, so it travels with the data.

Only the age **public** key is on the server. The **private** key that opens
backups lives offline (password manager). Someone who copies the bucket, or
the server's backup folder, can't read them.

Files: `deploy/backup/` holds `sweto-backup` (the script),
`sweto-backup@.service` / `.timer` (systemd, one instance per environment),
`sweto-restore-check` and `backup.env.example`.

## Install on the VPS (once)

1. Tools:

   ```bash
   sudo apt install -y age rclone
   ```

2. A key pair. Generate it, keep the private key in your password manager,
   and leave only the public key on the server:

   ```bash
   age-keygen -o /dev/shm/sweto-backup.key
   ```

   It prints `Public key: age1…`; that goes in `AGE_RECIPIENT`. Copy the whole
   file (`cat /dev/shm/sweto-backup.key`) into your password manager, then
   `rm /dev/shm/sweto-backup.key`.

3. A **private** bucket for backups (e.g. `sweto-backups`), separate from
   photos, in the same region as the server.

4. Settings, from `backup.env.example`:

   ```bash
   sudo install -d -m 700 /etc/sweto
   sudo install -m 600 deploy/backup/backup.env.example /etc/sweto/backup.env
   sudoedit /etc/sweto/backup.env
   ```

   Fill in `AGE_RECIPIENT`, `BACKUP_REMOTE`, the endpoint and the S3 key pair.

5. Script, restore check and timer:

   ```bash
   sudo install -m 755 deploy/backup/sweto-backup deploy/backup/sweto-restore-check /usr/local/bin/
   sudo install -m 644 deploy/backup/sweto-backup@.service deploy/backup/sweto-backup@.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now sweto-backup@staging.timer
   ```

   For production later: `sweto-backup@prod.timer`.

6. A first backup now, and its log:

   ```bash
   sudo systemctl start sweto-backup@staging.service
   journalctl -u sweto-backup@staging -n 5 --no-pager -o cat
   ```

   Expect `Backup OK: sweto_staging-<time>.tar.age (…), copied to …`.

## Prove a backup restores

Do this once after installing, and again every month or so:

```bash
sudo sh -c 'umask 077; cat > /dev/shm/sweto-backup.key'   # paste the private key, then Ctrl-D
sudo sh -c 'sweto-restore-check "$(ls -t /var/backups/sweto/staging/*.tar.age | head -1)" /dev/shm/sweto-backup.key'
sudo rm /dev/shm/sweto-backup.key
```

(`/dev/shm` is memory only, so the key never touches the disk.)

It restores into a throwaway database `sweto_restore_check`, prints row
counts, the newest payment and the migration, then drops it. The live
database isn't touched.

## Restore for real

Only after deciding to replace the live data (e.g. after a bad migration):

1. Stop the API and its jobs:
   `sudo systemctl stop sweto-staging sweto-staging-*.timer`.
2. Decrypt the chosen backup (from the server folder, or download it with
   `rclone copy contabo:sweto-backups/staging/<file> .`):

   ```bash
   mkdir -m 700 /dev/shm/restore
   age -d -i /dev/shm/sweto-backup.key <file>.tar.age | tar -C /dev/shm/restore -xf -
   ```

3. Recreate the database and load it:

   ```bash
   sudo -u postgres dropdb sweto_staging
   sudo -u postgres createdb -O sweto_staging sweto_staging
   sudo -u postgres pg_restore --no-owner --role=sweto_staging --dbname=sweto_staging < /dev/shm/restore/sweto_staging.dump
   ```

4. Make sure `/srv/sweto/config/staging.env` still has the same
   `MPESA_CREDENTIALS_KEY` as the backup's `staging.env`. If the server was
   rebuilt, restore that file too.
5. Start again: `sudo systemctl start sweto-staging sweto-staging-*.timer`.
   Then `sudo rm -rf /dev/shm/restore /dev/shm/sweto-backup.key`.

## If a backup fails

`systemctl status sweto-backup@staging` and
`journalctl -u sweto-backup@staging` show why. The script stops at the first
error and never leaves an unencrypted dump behind (it works in a temporary
folder that is always deleted). The usual causes are wrong S3 keys or bucket
name, or a full disk.
