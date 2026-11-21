"""Local-only sequential source probes plus temporary hardware telemetry."""
from pathlib import Path
import sys,os,json,time,datetime,threading,subprocess,ctypes,csv
ROOT=Path(__file__).resolve().parent
from access_guard import install
install('controller',False)
ENV=Path('E:/BCI_CV/.conda/prs_stage0_tf210');models=['EEGNet','EEGNeX','ATCNet'];done=threading.Event()
current={'stage':'starting','completed':0,'running':None,'waiting':models,'failed':[]}
start=time.perf_counter();powerlog=(ROOT/'logs/HARDWARE.jsonl').open('a',encoding='utf8',buffering=1)
def put(name,v):
    p=ROOT/name;t=p.with_suffix('.tmp');t.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'));t.replace(p)
class Power(ctypes.Structure):
    _fields_=[('ACLineStatus',ctypes.c_ubyte),('BatteryFlag',ctypes.c_ubyte),('BatteryLifePercent',ctypes.c_ubyte),('SystemStatusFlag',ctypes.c_ubyte),('BatteryLifeTime',ctypes.c_uint32),('BatteryFullLifeTime',ctypes.c_uint32)]
def telemetry():
    previous=None
    while not done.is_set():
        now=time.monotonic();s=Power();ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
        v=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic=now,ACLineStatus=s.ACLineStatus,BatteryPercent=s.BatteryLifePercent,
            suspend_gap_detected=previous is not None and now-previous>20,interval_seconds=None if previous is None else now-previous)
        previous=now
        try:
            fields='timestamp,name,temperature.gpu,pstate,clocks.sm,power.draw,power.limit,clocks_throttle_reasons.active,utilization.gpu,memory.used'
            raw=subprocess.check_output(['nvidia-smi','--query-gpu='+fields,'--format=csv,noheader,nounits'],text=True,timeout=10).strip()
            row=next(csv.reader([raw]));v['gpu']=dict(zip(fields.split(','),[a.strip() for a in row]))
            mask=int(v['gpu']['clocks_throttle_reasons.active'],16);v['thermal_slowdown_flag']=bool(mask&0x60);v['power_cap_flag']=bool(mask&4)
        except Exception as e:v['telemetry_error']=repr(e)
        powerlog.write(json.dumps(v,ensure_ascii=False)+'\n');put('TELEMETRY_LATEST.json',v)
        put('LIVE.json',dict(**current,elapsed_seconds=time.perf_counter()-start,overall_eta_seconds=None,eta_note='model-specific empirical progress;remaining models not yet measured'))
        done.wait(2)
thread=threading.Thread(target=telemetry,daemon=True);thread.start()
try:
    for i,model in enumerate(models):
        if (ROOT/'STOP.json').exists():raise RuntimeError('Access stop marker exists;all probes stopped')
        current.update(stage='source-only probe, at most2 epochs',running=model,waiting=models[i+1:])
        env=os.environ.copy();env['PATH']=str(ENV/'Library/bin')+';'+str(ENV)+';'+env['PATH'];env['PYTHONNOUSERSITE']='1'
        with (ROOT/f'logs/{model}.stdout.txt').open('x',encoding='utf8') as out,(ROOT/f'logs/{model}.stderr.txt').open('x',encoding='utf8') as err:
            begin=time.perf_counter();p=subprocess.run([str(ENV/'python.exe'),'-X','utf8',str(ROOT/'probe_worker.py'),model],env=env,stdout=out,stderr=err)
        if p.returncode:
            current['failed'].append(model);raise RuntimeError(f'{model} failed code{p.returncode};do not auto-rerun')
        current['completed']+=1
        result=json.loads((ROOT/f'output/{model}/RESULT.json').read_bytes())
        print(json.dumps(dict(model=model,fit_seconds=result['fit_seconds'],peak_MiB=result['peak_allocator_bytes']/2**20,probe_epochs=result['epochs'])),flush=True)
    current.update(stage='complete;all weights discarded;formal training not started',running=None,waiting=[])
    put('COMPLETE.json',dict(status='all3_source_probes_complete',models=models,elapsed_seconds=time.perf_counter()-start,
        conservative_single_GPU_charge_hours=(time.perf_counter()-start)/3600,held=1,seed=42,epochs_per_model=2,formal_training_fits=0))
except BaseException as e:
    current['stage']='STOPPED:review failure';put('CONTROLLER_FAILURE.json',dict(error=repr(e)));raise
finally:
    done.set();thread.join(timeout=15);put('LIVE.json',dict(**current,elapsed_seconds=time.perf_counter()-start));powerlog.close()
