# Daily encrypted backups and incident checks

The prepared workflow is `.github/workflows/operations.yml`. It backs up the application's **public schema** from Supabase using PostgreSQL 17, encrypts the stream with GnuPG AES-256 before writing it, and uploads only the encrypted file. GitHub artifact retention is seven days. It does not back up Supabase Auth, Storage objects, project settings, roles or extension installation. BiteAI currently uses its own public-schema accounts. Preserve the migrations and extension setup alongside backups.

The workflow also checks both public API origins daily, retries three times to allow Render Free to wake, and emails failures to **mantempp@gmail.com** through that Gmail account. This is a daily check, not continuous monitoring. Missing credentials produce an explicit failed job. GitHub usage and artifact quotas still apply; public-repository artifacts must be treated as publicly accessible even though their content is encrypted.

## Secure configuration required

Under repository Settings → Secrets and variables → Actions, add:

- `BACKUP_DATABASE_URL`: existing Supabase **session-pooler or direct libpq URL**, scheme `postgresql://`, with `sslmode=verify-full`. Use a credential authorized to read all application rows. Transaction pooling is unsuitable for pg_dump.
- `SUPABASE_CA_PEM`: official Supabase database CA certificate PEM, obtained through the project's connection settings. This is trust configuration rather than a password.
- `BACKUP_PASSPHRASE`: a randomly generated single-line secret of at least 32 characters. Keep a separate copy in your password manager. Losing it makes every retained backup unrecoverable; changing it requires retaining the old key for old backups.
- `SMTP_PASSWORD`: a Gmail **App Password** for mantempp@gmail.com, created in Google Account security with two-step verification enabled. A normal Gmail account password will not work. Account policies may disallow App Passwords.

In Render → biteai-demo → Environment, configure `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=465`, `SMTP_USER=mantempp@gmail.com`, `EMAIL_FROM=mantempp@gmail.com` and the same App Password as `SMTP_PASSWORD`. Preserve the existing `PUBLIC_APP_URL`, `DATABASE_URL` and `JWT_SECRET`. Gmail supports a small initial setup; delivery quotas apply. A Gmail address cannot serve as a custom verified domain.

No credential should be pasted into chat or committed. Enter credential values in the account’s secure settings; the existing connections do not supply the missing database password or Gmail App Password.

## Activation and verification

Scheduled GitHub workflows run from the repository's **default branch**, currently `main`. The application release is on `deploy/biteai-mvp`. The workflow is prepared on the deployment branch, but **its schedule is not active** until the workflow file is also present on `main` (or the default branch changes). Do not merge the entire deployment branch into main merely for scheduling: other existing Vercel projects track main. Copy only this workflow through a reviewed infrastructure change after checking those deployment triggers. It explicitly checks out `deploy/biteai-mvp` for its scripts.

After secure configuration and default-branch activation, manually run “BiteAI encrypted backup and health”. Require a successful encrypted artifact upload and a recovery rehearsal before claiming production backups work. Confirm a real email delivery separately; successful health checks do not send mail. Scheduled runs can be delayed by GitHub and inactive public repositories may have schedules disabled.

## Recovery into an isolated database

Download the encrypted artifact to a trusted machine with PostgreSQL 17 client tools, GPG and Python 3. Configure these environment variables securely, without putting secrets in shell history:

- `RESTORE_DATABASE_URL`: a **new, empty isolated** PostgreSQL recovery database with `sslmode=verify-full`.
- `PGSSLROOTCERT`: trusted CA file for that recovery server.
- `BACKUP_PASSPHRASE`: the password-manager copy for this particular backup.
- `CONFIRM_ISOLATED_RESTORE=yes`.

Run `python3 scripts/encrypted_backup.py restore /path/to/biteai.dump.gpg`. Decryption authenticates the entire archive before the target is touched. Restore runs in a single transaction and does not issue destructive `--clean` commands. Its temporary decrypted archive is deleted on normal completion/failure; use an encrypted local disk. Prepare compatible PostGIS/extensions before restore where applicable. A failed authentication never invokes pg_restore.

Compare table counts and complete-row hashes, confirm migration checksums, run the API against the isolated target and verify authentication/catalog behavior. Never point this rehearsal at production. This workflow has encryption round-trip, wrong-key and failed-dump cleanup tests; **an encrypted production backup and full production-data recovery have not yet been performed**.
