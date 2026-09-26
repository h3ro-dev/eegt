"""Run one extracted replay under the original root and existing numeric lock."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,os,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/'work/transition-extracted-r2'
RECEIPT=ROOT/'work/continuation/transition-replay-r2-receipt.json'
LOG=ROOT/'work/continuation/transition-replay-r2.log'
lock=(ROOT/'work/continuation/transition-numeric.lock').open('a+')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
if RECEIPT.exists():raise FileExistsError('preserve earlier replay receipt')
cmd=[str(ROOT/'work/direct-events/review/.venv/bin/python'),str(PACKET/'repo/scripts/reproduce_events.py'),'reproduce']
env=dict(os.environ)
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:env[key]='1'
r={'schema':'eegt-extracted-replay-run/v1','state':'RUNNING','original_task':'01a0d46f-1d63-72f3-95d0-692535ad6615','work_id':'eco-uzwh8s.34.2','owner':'session-13ffd342d925791b856652db872e4142','machine':'studio0','mode':'existing_root_no_new_worker','started_utc':datetime.now(timezone.utc).isoformat(),'wrapper_pid':os.getpid(),'command':cmd,'cwd':str(PACKET),'log':str(LOG),'extraction_receipt_sha256':hashlib.sha256((ROOT/'outputs/eegt/results/012/extraction-receipt.json').read_bytes()).hexdigest(),'fresh_physical_readback':json.loads((ROOT/'work/transition-release/replay-r2-physical-readback.json').read_text()),'timeout_seconds':7200,'numeric_processes':1,'threads':1,'planning_peak_rss_bytes':2147483648}
def save():
 p=RECEIPT.with_suffix('.partial');p.write_text(json.dumps(r,indent=2)+'\n');p.replace(RECEIPT)
assert (datetime.now(timezone.utc)-datetime.fromisoformat(r['fresh_physical_readback']['observed_utc'])).total_seconds()<120
r['admission_reason']='Previous full replay measured 1.23GB RSS and one CPU; fresh 80GiB unused,67.42percent CPU idle,pressure1,zero swap sample and about856GiB free disk. Existing root, nice10, same numeric lock; no new worker or competing EEGT numeric process.'
started=time.monotonic()
with LOG.open('x') as log:
 p=subprocess.Popen(cmd,cwd=PACKET,env=env,stdout=log,stderr=subprocess.STDOUT)
 r['numeric_pid']=p.pid;save()
 try:code=p.wait(timeout=7200)
 except subprocess.TimeoutExpired:
  p.terminate()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.wait()
  code=p.returncode;r['timeout']=True
r.update(state='EXITED',exit_code=code,ended_utc=datetime.now(timezone.utc).isoformat(),elapsed_wall_seconds=time.monotonic()-started)
if code==0:
 receipts=sorted((PACKET/'repo/results/012').glob('reproduction-*.json'))
 latest=receipts[-1];generated=json.loads(latest.read_text())
 r['generated_receipt']=str(latest);r['generated_receipt_sha256']=hashlib.sha256(latest.read_bytes()).hexdigest();r['scientific_reproduction_status']=generated.get('status');r['full_scientific_summary']=generated.get('full_scientific_summary')
save();print(json.dumps(r))
raise SystemExit(code)
