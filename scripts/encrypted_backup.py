"""Stream pg_dump into authenticated GPG encryption; never persist a plaintext dump."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlsplit, unquote, parse_qs


def database_environment(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname:
        raise ValueError('Use a PostgreSQL libpq connection URL')
    env = os.environ.copy()
    for key in ('BACKUP_DATABASE_URL', 'BACKUP_PASSPHRASE', 'RESTORE_DATABASE_URL'):
        env.pop(key, None)
    env.update(PGHOST=parsed.hostname, PGPORT=str(parsed.port or 5432),
               PGDATABASE=unquote(parsed.path.lstrip('/')), PGUSER=unquote(parsed.username or ''),
               PGPASSWORD=unquote(parsed.password or ''))
    query = parse_qs(parsed.query)
    for key in ('sslmode', 'sslrootcert'):
        if key in query:
            env['PG' + key.upper()] = query[key][0]
    if env.get('PGSSLMODE') != 'verify-full':
        raise ValueError('Database backups/restores require sslmode=verify-full and a trusted CA')
    return env


def crypt(arguments, secret, **kwargs):
    if len(secret) < 32 or '\n' in secret:
        raise ValueError('Use a single-line backup passphrase of at least 32 characters')
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, secret.encode() + b'\n')
        os.close(write_fd)
        write_fd = -1
        return subprocess.run(['gpg', '--batch', '--yes', '--pinentry-mode', 'loopback',
                               '--passphrase-fd', str(read_fd), *arguments],
                              pass_fds=(read_fd,), stderr=subprocess.DEVNULL, **kwargs)
    finally:
        os.close(read_fd)
        if write_fd >= 0:
            os.close(write_fd)


def backup(destination):
    env = database_environment(os.environ['BACKUP_DATABASE_URL'])
    secret = os.environ['BACKUP_PASSPHRASE']
    if len(secret) < 32:
        raise ValueError('Backup passphrase must contain at least 32 characters')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.partial')
    try:
        with partial.open('xb') as output:
            os.chmod(partial, 0o600)
            with subprocess.Popen(['pg_dump', '--format=custom', '--no-owner', '--no-acl',
                                   '--schema=public'], env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL) as dump:
                try:
                    encrypted = crypt(['--symmetric', '--cipher-algo', 'AES256', '--output', '-'],
                                      secret, stdin=dump.stdout, stdout=output, env=env)
                finally:
                    dump.stdout.close()
                if dump.wait() or encrypted.returncode:
                    raise RuntimeError('Backup failed; no artifact retained')
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)


def restore(archive):
    # Explicit opt-in; intended only for a new isolated recovery database.
    if os.environ.get('CONFIRM_ISOLATED_RESTORE') != 'yes':
        raise ValueError('Set CONFIRM_ISOLATED_RESTORE=yes for an empty isolated target')
    env = database_environment(os.environ['RESTORE_DATABASE_URL'])
    if os.environ.get('RESTORE_DATABASE_URL') == os.environ.get('BACKUP_DATABASE_URL'):
        raise ValueError('Restore target must differ from backup source')
    with tempfile.TemporaryDirectory(prefix='biteai-restore-') as directory:
        plain = Path(directory) / 'database.dump'
        # Authenticate the entire encrypted file before invoking pg_restore.
        result = crypt(['--output', str(plain), '--decrypt', str(archive)],
                       os.environ['BACKUP_PASSPHRASE'], env=env)
        if result.returncode:
            raise RuntimeError('Decryption/authentication failed; target was not touched')
        subprocess.run(['pg_restore', '--exit-on-error', '--single-transaction', '--no-owner',
                        '--no-acl', '--dbname', env['PGDATABASE'], str(plain)],
                       env=env, stderr=subprocess.DEVNULL, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['backup', 'restore'])
    parser.add_argument('archive')
    args = parser.parse_args()
    try:
        (backup if args.operation == 'backup' else restore)(args.archive)
    except Exception:
        # Provider errors can contain connection credentials; do not echo them in CI.
        raise SystemExit('Backup/recovery failed. Check secure configuration and PostgreSQL client compatibility.') from None
