"""Generated test certificates are isolated fixtures, never production trust roots."""
import json
import ssl
import subprocess
from pathlib import Path
import pytest
from app.database_tls import connection_url
from app.build_database_ca import build_bundle, SOURCE

@pytest.fixture(scope='module')
def ca(tmp_path_factory):
    root=tmp_path_factory.mktemp('db-ca')
    cert=root/'root.crt'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','2',
                    '-keyout',str(root/'root.key'),'-out',str(cert),'-subj','/CN=BiteAI isolated test CA',
                    '-addext','basicConstraints=critical,CA:TRUE'],check=True,capture_output=True)
    return cert

@pytest.mark.parametrize('setting',['','?sslmode=verify-full&sslrootcert=/etc/secrets/supabase-ca.crt',
                                    '?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt',
                                    '?sslmode=require','?sslrootcert=system'])
def test_supabase_uses_image_ca_and_preserves_credentials(ca,setting):
    url=connection_url('postgresql://postgres.fixture:not%40a%3Areal%25password@aws-0-ap-south-1.pooler.supabase.com:5432/postgres'+setting,bundle_path=ca)
    assert url.drivername=='postgresql+psycopg'
    assert url.password=='not@a:real%password' and url.username=='postgres.fixture'
    assert url.query['sslmode']=='verify-full' and url.query['sslrootcert']==str(ca)

def test_custom_existing_ca_and_non_supabase_preserved(ca):
    value='postgres://user:fixture@db.fixture.supabase.co/db?sslrootcert='+str(ca)
    assert connection_url(value,bundle_path='/missing').query['sslrootcert']==str(ca)
    unrelated=connection_url('postgresql://u:p@localhost/db?sslmode=verify-ca&sslrootcert=/custom')
    assert unrelated.query['sslmode']=='verify-ca'
    lookalike=connection_url('postgresql://u:p@aws.pooler.supabase.com.evil.test/db?sslmode=verify-ca')
    assert lookalike.query['sslmode']=='verify-ca'

def test_missing_invalid_and_duplicate_ca_fail_before_network(ca,tmp_path):
    host='postgresql://user:private-test-placeholder@db.fixture.supabase.co/db'
    with pytest.raises(ValueError,match='missing'):connection_url(host,bundle_path=tmp_path/'missing')
    invalid=tmp_path/'bad.crt';invalid.write_text('invalid certificate')
    with pytest.raises(ValueError,match='invalid'):connection_url(host,bundle_path=invalid)
    with pytest.raises(ValueError,match='duplicate'):connection_url(host+'?sslrootcert=/a&sslrootcert=/b',bundle_path=ca)

def test_builder_installs_readable_valid_ca_and_records_provenance(ca,tmp_path):
    result=build_bundle(tmp_path/'bundle.pem',fetch=ca.read_bytes,system_ca=ca,source='isolated test fixture')
    assert result.is_file() and result.stat().st_mode & 0o444==0o444
    ssl.create_default_context(cafile=str(result))
    metadata=json.loads(result.with_suffix('.json').read_text())
    assert metadata['source']=='isolated test fixture' and len(metadata['sha256'])==64

def test_invalid_download_does_not_create_bundle(ca,tmp_path):
    output=tmp_path/'bundle.pem'
    with pytest.raises(ValueError):build_bundle(output,fetch=lambda:b'invalid',system_ca=ca)
    assert not output.exists()
    with pytest.raises(ValueError):build_bundle(output,fetch=lambda:b'PRIVATE KEY',system_ca=ca)
    assert not output.exists()

def test_sqlite_unchanged():
    assert connection_url('sqlite:///./local.sqlite').get_backend_name()=='sqlite'
