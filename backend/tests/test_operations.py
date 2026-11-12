import importlib.util
from pathlib import Path
import os
import shutil
import subprocess
import pytest
from test_api import client

spec=importlib.util.spec_from_file_location('backup',Path(__file__).resolve().parents[2]/'scripts/encrypted_backup.py')
backup=importlib.util.module_from_spec(spec);spec.loader.exec_module(backup)


def test_mail_requires_credentials_and_secure_links(monkeypatch):
    from app.account_security import mail_enabled
    for key,value in {'SMTP_HOST':'smtp.gmail.com','SMTP_USER':'letsbiteai@gmail.com','EMAIL_FROM':'letsbiteai@gmail.com','PUBLIC_APP_URL':'https://example.test'}.items():
        monkeypatch.setenv(key,value)
    monkeypatch.delenv('SMTP_PASSWORD',raising=False)
    assert not mail_enabled()
    monkeypatch.setenv('SMTP_PASSWORD','fixture')
    assert mail_enabled()
    monkeypatch.setenv('PUBLIC_APP_URL','http://example.test')
    assert not mail_enabled()


def test_backup_rejects_insecure_connection():
    with pytest.raises(ValueError):backup.database_environment('postgresql://user:secret@localhost/db?sslmode=require')
    env=backup.database_environment('postgresql://user:p%40ss@db.example/db?sslmode=verify-full')
    assert env['PGPASSWORD']=='p@ss' and env['PGSSLMODE']=='verify-full'


@pytest.mark.skipif(not shutil.which('gpg'),reason='GPG required')
def test_backup_encrypted_roundtrip_failure_cleanup_and_wrong_key(tmp_path,monkeypatch):
    executable=tmp_path/'pg_dump'
    executable.write_text('#!/bin/sh\nprintf "isolated database fixture"\n')
    executable.chmod(0o700)
    monkeypatch.setenv('PATH',str(tmp_path)+os.pathsep+os.environ['PATH'])
    monkeypatch.setenv('BACKUP_DATABASE_URL','postgresql://fixture:fixture@db.example/fixture?sslmode=verify-full')
    monkeypatch.setenv('BACKUP_PASSPHRASE','isolated-test-passphrase-'+'a'*32)
    home=tmp_path/'gpg';home.mkdir(mode=0o700);monkeypatch.setenv('GNUPGHOME',str(home))
    archive=tmp_path/'backup.gpg';backup.backup(archive)
    assert b'isolated database fixture' not in archive.read_bytes()
    plain=tmp_path/'restored'
    assert backup.crypt(['--output',str(plain),'--decrypt',str(archive)],os.environ['BACKUP_PASSPHRASE']).returncode==0
    assert plain.read_bytes()==b'isolated database fixture'
    assert backup.crypt(['--output',str(tmp_path/'wrong'),'--decrypt',str(archive)],'wrong-key-'+'b'*32).returncode!=0
    executable.write_text('#!/bin/sh\nprintf partial\nexit 1\n')
    with pytest.raises(RuntimeError):backup.backup(tmp_path/'failed.gpg')
    assert not (tmp_path/'failed.gpg').exists() and not list(tmp_path.glob('*.partial'))


def test_health_retries_and_sends_only_failure_origins(monkeypatch):
    import io
    health_spec=importlib.util.spec_from_file_location('health',Path(__file__).resolve().parents[2]/'scripts/check_health.py')
    health=importlib.util.module_from_spec(health_spec);health_spec.loader.exec_module(health)
    attempts=[];sent=[]
    def response(url,timeout):
        attempts.append(url)
        if 'onrender.com' in url:raise OSError('fixture outage')
        return io.BytesIO(b'{"status":"ok","database":"connected"}')
    class SMTP:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def login(self,user,password):assert user=='letsbiteai@gmail.com' and password=='fixture'
        def send_message(self,message):sent.append(message)
    monkeypatch.setattr(health.urllib.request,'urlopen',response)
    monkeypatch.setattr(health.time,'sleep',lambda _:None)
    monkeypatch.setattr(health.smtplib,'SMTP_SSL',SMTP)
    monkeypatch.setenv('SMTP_PASSWORD','fixture')
    with pytest.raises(SystemExit,match='incident email sent'):health.check()
    assert len(attempts)==4 and len(sent)==1
    assert 'https://biteai-demo.onrender.com' in sent[0].get_content()
    assert 'qxtx.vercel.app' not in sent[0].get_content()


def test_security_email_uses_signed_https_relay_without_redirects(monkeypatch):
    import hashlib,hmac,json
    from app import account_security as security
    secret='isolated-relay-secret-'+'a'*32
    for key,value in {'EMAIL_TRANSPORT':'https-relay','EMAIL_RELAY_SECRET':secret,'EMAIL_RELAY_URL':'https://restaurant-management-system-qxtx.vercel.app/api/internal/security-mail','PUBLIC_APP_URL':'https://restaurant-management-system-qxtx.vercel.app','SMTP_PASSWORD':'abcdefghijklmnop'}.items():
        monkeypatch.setenv(key,value)
    sent=[]
    class Client:
        def __init__(self,**kwargs):assert kwargs['follow_redirects'] is False
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,content,headers):
            sent.append(json.loads(content))
            expected=hmac.new(secret.encode(),(headers['X-BiteAI-Mail-Time']+'.'+content).encode(),hashlib.sha256).hexdigest()
            assert hmac.compare_digest(expected,headers['X-BiteAI-Mail-Signature'])
            return type('Response',(),{'status_code':200})()
    monkeypatch.setattr(security.httpx,'Client',Client)
    assert security.mail_enabled()
    security.send_security_email('fixture@example.test','verify','a'*43)
    assert sent[0]['purpose']=='verify'
    monkeypatch.setenv('EMAIL_RELAY_URL','https://untrusted.example/relay')
    assert not security.mail_enabled()


def test_operator_mail_test_is_private_and_fixed_recipient(client,monkeypatch):
    from app import account_security as security
    secret='isolated-mail-operator-secret-'+'x'*32
    monkeypatch.setenv('EMAIL_TRANSPORT','https-relay')
    monkeypatch.setenv('EMAIL_RELAY_SECRET',secret)
    assert client.post('/internal/email-test').status_code==404
    assert client.post('/internal/email-test',headers={'Authorization':'Bearer wrong'}).status_code==404
    sent=[]
    monkeypatch.setattr(security,'send_security_email',lambda email,purpose,token:sent.append((email,purpose)))
    response=client.post('/internal/email-test',headers={'Authorization':'Bearer '+secret})
    assert response.status_code==200 and sent==[('letsbiteai@gmail.com','test')]
    assert secret not in response.text
