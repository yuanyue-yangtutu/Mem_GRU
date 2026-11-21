from pathlib import Path
import json,hashlib,time,os,datetime,threading
_write_lock=threading.RLock()
ROOT=Path(__file__).resolve().parent
R3=Path('D:/BCI_builds/PRS_MatchedBaselines_R3_Stage05_20261121')
R2=Path('D:/BCI_builds/PRS_MatchedBaselines_R2_Stage0_20261121')
OFFICIAL=Path('D:/BCI_builds/PRS_MatchedBaselines_Draft_20261121/sources')
ENV=Path('E:/BCI_CV/.conda/prs_stage0_tf210')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def put(p,v):
    with _write_lock:
        p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
        t=p.with_suffix(p.suffix+'.tmp')
        t.write_bytes((json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf8'))
        for i in range(100):
            try:t.replace(p);return
            except PermissionError:time.sleep(.02)
        raise RuntimeError('atomic metadata publication failed: '+str(p))
def verify_binding():
    for path,expected in read(ROOT/'public/EXECUTION_BINDINGS.json')['files'].items():
        assert sha(path)==expected,'hash mismatch: '+path
