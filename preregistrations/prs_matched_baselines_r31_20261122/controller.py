"""Single local GPU queue; source-only, sum process-wall budget, no auto-retry."""
from common import *
import sys,subprocess,threading,ctypes,csv,statistics
verify_binding()
assert read(ROOT/'PUBLICATION_RECEIPT.json')['anonymous_exact_bytes_verified']
assert not (ROOT/'RUN_STARTED.json').exists(),'Refuse duplicate controller'
put(ROOT/'RUN_STARTED.json',dict(utc=now(),pid=os.getpid(),source_only=True))
queue=read(ROOT/'public/QUEUE.json');configs=read(ROOT/'public/FROZEN_CONFIGS.json')
prior=.0132828877777744;charged=prior;done=[];failed=[];active=None
started=time.monotonic();halt=threading.Event();high_since=None;last_sample=None
hardware=(ROOT/'logs/HARDWARE.jsonl').open('a',encoding='utf8',buffering=1)
class Power(ctypes.Structure):
    _fields_=[('ACLineStatus',ctypes.c_ubyte),('BatteryFlag',ctypes.c_ubyte),('BatteryLifePercent',ctypes.c_ubyte),('SystemStatusFlag',ctypes.c_ubyte),('BatteryLifeTime',ctypes.c_uint32),('BatteryFullLifeTime',ctypes.c_uint32)]
def stop(reason,extra=None):
    if not (ROOT/'STOP.json').exists():put(ROOT/'STOP.json',dict(reason=reason,utc=now(),extra=extra))
def sample():
    global high_since,last_sample
    t=time.monotonic();s=Power();assert ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
    v=dict(utc=now(),monotonic=t,ACLineStatus=s.ACLineStatus,battery_percent=s.BatteryLifePercent,interval_seconds=None if last_sample is None else t-last_sample)
    if last_sample is not None and t-last_sample>20:stop('sleep/hibernate or monitoring-gap interruption',v)
    last_sample=t
    if s.ACLineStatus!=1:stop('AC disconnected',v)
    fields='name,driver_version,temperature.gpu,pstate,clocks.sm,clocks.mem,power.draw,power.limit,clocks_throttle_reasons.active,utilization.gpu,memory.used'
    try:
        raw=subprocess.check_output(['nvidia-smi','--query-gpu='+fields,'--format=csv,noheader,nounits'],text=True,timeout=10,creationflags=0x08000000).strip()
        rows=list(csv.reader(raw.splitlines()));assert len(rows)==1,'local single GPU expected'
        v['gpu']=dict(zip(fields.split(','),[x.strip() for x in rows[0]]))
        assert 'RTX 4060 Laptop' in v['gpu']['name']
        temp=float(v['gpu']['temperature.gpu'])
        if temp>=85:
            if high_since is None:high_since=t
            if t-high_since>=30:stop('core temperature >=85C for >=30s',v)
        else:high_since=None
        v['core_hot_continuous_seconds']=0 if high_since is None else t-high_since
        v['throttle_flags_record_only']=True
    except Exception as e:
        v['driver_query_error']=repr(e);stop('GPU driver/query error',v)
    hardware.write(json.dumps(v,ensure_ascii=False)+'\n');put(ROOT/'TELEMETRY_LATEST.json',v)
    if active is not None and charged+(time.monotonic()-active['start'])/3600>=80:stop('80 GPU-hour hard limit')
    return v
def progress():
    running=None
    if active:
        p=Path(active['out'])/'LIVE.json'
        try:running=read(p)
        except (FileNotFoundError,json.JSONDecodeError):running=dict(fit_id=active['fit_id'],stage='initializing',eta_seconds=None)
    elapsed_hours=charged+((time.monotonic()-active['start'])/3600 if active else 0)
    measured={}
    for m in configs:
        vals=[d['charged_seconds'] for d in done if d['model']==m]
        measured[m]=statistics.median(vals) if vals else None
    waiting=[q for q in queue if q['fit_id'] not in {d['fit_id'] for d in done} and (not active or q['fit_id']!=active['fit_id'])]
    # Max-epoch envelope; early stopping makes realized duration lower and uncertain.
    eta=0.;all_measured=True
    for q in waiting:
        v=measured[q['model']]
        if v is None:all_measured=False
        else:eta+=v
    if running:eta+=running.get('eta_seconds') or 0
    put(ROOT/'LIVE.json',dict(status='STOPPED' if (ROOT/'STOP.json').exists() else 'RUNNING',completed=len(done),total=len(queue),failed=failed,running=running,waiting=[q['fit_id'] for q in waiting],charged_GPU_hours=elapsed_hours,remaining_GPU_hours=max(0,80-elapsed_hours),overall_eta_seconds=eta if all_measured else None,eta_note='waiting measured completed fits for all models' if not all_measured else 'completed-fit model medians plus current max-epoch envelope; not guaranteed',measured_fit_seconds_by_model=measured,elapsed_wall_seconds=time.monotonic()-started,updated_utc=now()))
def monitor():
    while not halt.wait(5):
        try:sample();progress()
        except BaseException as e:stop('monitor engineering failure',repr(e))
try:
    # Query only power policy metadata; no machine configuration changes.
    policies={n:subprocess.check_output(['powercfg','/query','SCHEME_CURRENT','SUB_SLEEP',n],text=True,errors='replace',creationflags=0x08000000) for n in ['STANDBYIDLE','HIBERNATEIDLE']}
    import re
    for n,txt in policies.items():
        indices=re.findall(r'0x[0-9a-fA-F]{8}',txt)
        assert len(indices)>=2 and int(indices[-2],16)==0,'AC sleep/hibernate policy not zero: '+n
    put(ROOT/'POWER_POLICY_START.json',dict(utc=now(),queries=policies))
    sample();assert not (ROOT/'STOP.json').exists(),'safety precheck failed'
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    env=os.environ.copy();env.update(PYTHONNOUSERSITE='1',TEMP=str(ROOT/'tmp'),TMP=str(ROOT/'tmp'),CUDA_CACHE_PATH=str(ROOT/'tmp/cuda'))
    env['PATH']=str(ENV/'Library/bin')+';'+str(ENV)+';'+env['PATH']
    for q in queue:
        if (ROOT/'STOP.json').exists():break
        verify_binding()
        # Frozen R3 conservative maximum-attempt budget from second probe epoch.
        probe=read(R3/('public/probe_results/'+q['model']+'.json'))
        e2=probe['epoch_timings'][1]['wall_seconds']
        allowance=(4*configs[q['model']]['max_epochs']*e2+probe['process_wall_seconds']+60)/3600
        if 80-charged<allowance:stop('insufficient budget for next complete maximum fit',dict(remaining=80-charged,next_max_hours=allowance));break
        out=ROOT/'fits'/q['fit_id']/'attempt001';out.mkdir(parents=True,exist_ok=False)
        owners=[i for i in range(1,10) if i!=q['held']]
        reg=dict(**q,source_subjects=owners,source_files=[str(Path('D:/BCI_builds/PRS_UNIFORM_NEWSEEDS/data')/('S%d.npz'%i)) for i in owners],split_seed=20261221,allowed_sessions='source T only',target_reads_authorized=False,created_utc=now())
        put(out/'REGISTRATION.json',reg)
        put(out/'POWER_START.json',read(ROOT/'TELEMETRY_LATEST.json'))
        with (out/'stdout.txt').open('x',encoding='utf8') as stdout,(out/'stderr.txt').open('x',encoding='utf8') as stderr:
            begin=time.monotonic()
            p=subprocess.Popen([str(ENV/'python.exe'),'-X','utf8',str(ROOT/'train_worker.py'),q['fit_id']],env=env,stdout=stdout,stderr=stderr,creationflags=0x08000000)
            active=dict(fit_id=q['fit_id'],out=str(out),start=begin,pid=p.pid);progress()
            while p.poll() is None:
                if (ROOT/'STOP.json').exists():p.terminate();p.wait(timeout=30);break
                time.sleep(1)
            seconds=time.monotonic()-begin;charged+=seconds/3600;active=None
        put(out/'PROCESS_ACCOUNT.json',dict(seconds=seconds,charged_GPU_hours=seconds/3600,returncode=p.returncode,utc=now()))
        put(out/'POWER_END.json',read(ROOT/'TELEMETRY_LATEST.json'))
        completed=out/'TRAINING_COMPLETED.json'
        if p.returncode or not completed.exists():
            failed.append(q['fit_id']);stop('fit interrupted or failed; no automatic retry',dict(fit_id=q['fit_id'],code=p.returncode));progress();break
        d=read(completed);assert sha(d['model_file'])==d['model_sha256']
        d.update(charged_seconds=seconds,completion_marker_sha256=sha(completed));done.append(d)
        put(ROOT/'MODEL_HASH_MANIFEST.json',dict(fits=done,completed=len(done),total=81,charged_GPU_hours=charged,target_inference=False))
        progress();print(json.dumps(dict(completed=len(done),fit_id=q['fit_id'],charged_GPU_hours=charged)),flush=True)
    status='ALL_TRAINING_COMPLETED' if len(done)==81 else 'STOPPED_INCOMPLETE'
    put(ROOT/'FINAL.json',dict(status=status,completed_fits=len(done),total_fits=81,failed_fits=failed,wall_seconds=time.monotonic()-started,charged_GPU_hours=charged,prior_probe_hours=prior,model_manifest_sha256=sha(ROOT/'MODEL_HASH_MANIFEST.json') if (ROOT/'MODEL_HASH_MANIFEST.json').exists() else None,target_reads=0,target_inference=False,finished_utc=now()))
except BaseException as e:
    import traceback
    stop('controller failure',dict(error=repr(e),traceback=traceback.format_exc()))
    if active:
        try:p.terminate();p.wait(timeout=30)
        except Exception:pass
    raise
finally:
    halt.set()
    if 'thread' in globals():thread.join(timeout=20)
    progress();hardware.close()
