"""Build-time acquisition of Supabase's official public database CA, using verified HTTPS."""
import argparse
import hashlib
import json
from pathlib import Path
import ssl
import subprocess
import tempfile
from urllib.request import urlopen

SOURCE = 'https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt'
DEFAULT_OUTPUT = Path(__file__).resolve().parent / 'certs' / 'supabase-bundle.pem'

def download():
    # urllib honours inherited proxies and CA trust. Never disable certificate checks.
    with urlopen(SOURCE,timeout=30) as response:
        if response.geturl()!=SOURCE:raise ValueError('Unexpected certificate download redirect')
        payload=response.read(128001)
    if len(payload)>128000:raise ValueError('Database CA download exceeds size limit')
    return payload

def build_bundle(output=DEFAULT_OUTPUT, fetch=download, system_ca=Path('/etc/ssl/certs/ca-certificates.crt'), source=SOURCE):
    payload=fetch()
    if b'PRIVATE KEY' in payload:raise ValueError('A CA download must not contain a private key')
    if payload.count(b'-----BEGIN CERTIFICATE-----')!=1:raise ValueError('Expected one official database CA certificate')
    with tempfile.TemporaryDirectory() as directory:
        certificate=Path(directory)/'source.crt';certificate.write_bytes(payload)
        context=ssl.create_default_context()
        context.load_verify_locations(cafile=str(certificate))
        inspection=subprocess.run(['openssl','x509','-in',str(certificate),'-noout','-ext','basicConstraints'],check=True,capture_output=True,text=True)
        if 'CA:TRUE' not in inspection.stdout:raise ValueError('Downloaded certificate is not a CA')
        subprocess.run(['openssl','x509','-in',str(certificate),'-checkend','86400','-noout'],check=True,capture_output=True)
    roots=Path(system_ca).read_bytes()
    combined=roots.rstrip()+b'\n'+payload.rstrip()+b'\n'
    with tempfile.TemporaryDirectory() as directory:
        checked=Path(directory)/'combined.pem';checked.write_bytes(combined)
        ssl.create_default_context(cafile=str(checked))
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(combined);output.chmod(0o644)
    manifest={'source':source,'sha256':hashlib.sha256(payload).hexdigest()}
    output.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Installed database CA from '+source+'; SHA256 '+manifest['sha256'],flush=True)
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(DEFAULT_OUTPUT))
    parser.add_argument('--certificate-file',help='Explicit trusted local CA, for operator builds or isolated tests')
    args=parser.parse_args()
    if args.certificate_file:
        build_bundle(args.output,fetch=Path(args.certificate_file).read_bytes,source='explicit operator-provided certificate file')
    else:build_bundle(args.output)
