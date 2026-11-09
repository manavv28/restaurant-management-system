"""Supabase connection setup without a dashboard-uploaded certificate dependency."""
from pathlib import Path
import ssl
from sqlalchemy.engine import make_url

BUNDLE = Path(__file__).resolve().parent / 'certs' / 'supabase-bundle.pem'

def is_supabase(host):
    host=(host or '').lower()
    return host.endswith('.pooler.supabase.com') or (
        host.startswith('db.') and host.endswith('.supabase.co') and host.count('.')==3
    )

def connection_url(value, bundle_path=None):
    """Preserve encoded credentials; never change non-Supabase TLS settings."""
    try:url=make_url(value)
    except Exception:raise ValueError('Invalid DATABASE_URL format; check the hidden connection setting') from None
    if url.drivername in ('postgres','postgresql'):url=url.set(drivername='postgresql+psycopg')
    if url.get_backend_name()!='postgresql' or not is_supabase(url.host):return url
    root=url.query.get('sslrootcert')
    if isinstance(root,tuple):raise ValueError('DATABASE_URL has duplicate sslrootcert settings')
    bundle=Path(bundle_path) if bundle_path is not None else BUNDLE
    # Recover transparently from both certificate paths previously recommended.
    if not root or root in ('system','/etc/ssl/certs/ca-certificates.crt') or (root=='/etc/secrets/supabase-ca.crt' and not Path(root).is_file()):
        certificate=bundle
    else:
        certificate=Path(root)
    if not certificate.is_file():
        raise ValueError('Database CA file is missing. Deploy the image containing the Supabase CA bundle, or provide the explicitly configured certificate file.')
    try:
        context=ssl.create_default_context()
        context.load_verify_locations(cafile=str(certificate))
    except (OSError,ssl.SSLError):
        raise ValueError('Database CA file cannot be read or contains an invalid certificate') from None
    return url.update_query_dict({'sslmode':'verify-full','sslrootcert':str(certificate)})
