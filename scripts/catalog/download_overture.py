import os,json,warnings,argparse
from pathlib import Path
from collections import Counter
import pyarrow as pa
import pyarrow.fs as fs
import overturemaps.core as core

pa.set_cpu_count(2);pa.set_io_thread_count(4)
def filesystem(connect_timeout=None,request_timeout=None):
 return fs.S3FileSystem(anonymous=True,region='us-west-2',proxy_options=os.environ.get('HTTPS_PROXY'),tls_ca_file_path=os.getenv('SSL_CERT_FILE','/etc/ssl/certs/ca-certificates.crt'),connect_timeout=15,request_timeout=60,retry_strategy=fs.AwsStandardS3RetryStrategy(max_attempts=2))
core._s3_filesystem=filesystem
warnings.simplefilter('error',core.StacIndexWarning)
parser=argparse.ArgumentParser(description='Download an anonymous, spatially bounded Overture places extract. No API key required.')
parser.add_argument('--release',required=True);parser.add_argument('--output',required=True)
args=parser.parse_args();release=args.release;out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
print('Release',release,flush=True)
bbox=(72.7732289,18.8921596,72.9817485,19.2694771)
dataset,expr=core._prepare_query('place',bbox=bbox,release=release,connect_timeout=15,request_timeout=60)
print('Selected files',len(dataset.files),flush=True)
print('Schema',str(dataset.schema),flush=True)
columns=['id','bbox','names','basic_category','taxonomy','confidence','operating_status','addresses','websites','phones','sources']
columns=[x for x in columns if x in dataset.schema.names]
counts=Counter();total=0
output=out/'overture-bbox.jsonl'
with output.open('w') as f:
 for batch in dataset.scanner(columns=columns,filter=expr,batch_size=2048,batch_readahead=1,fragment_readahead=1,use_threads=False).to_batches():
  for row in batch.to_pylist():
   total+=1;counts[row.get('basic_category')]+=1
   # Store the bounded Mumbai extract to inspect categories before filtering.
   f.write(json.dumps(row,ensure_ascii=False)+'\n')
  print('Scanned',total,flush=True)
(out/'overture-download.json').write_text(json.dumps({'release':release,'bbox':bbox,'rows':total,'categories':counts,'files':dataset.files},indent=2))
print(json.dumps({'rows':total,'categories':counts}),flush=True)
