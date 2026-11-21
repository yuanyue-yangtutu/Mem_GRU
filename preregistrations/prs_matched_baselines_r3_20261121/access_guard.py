"""Phase0.5 exact source-file allowlist and Python-open audit. Not an OS sandbox."""
from pathlib import Path
import sys,os,json,time,datetime
ROOT=Path(__file__).resolve().parent
R2=ROOT.parent/'PRS_MatchedBaselines_R2_Stage0_20261121'
OFFICIAL=ROOT.parent/'PRS_MatchedBaselines_Draft_20261121'/'sources'

def canonical(p):return os.path.normcase(str(Path(p).resolve())).replace('\\','/')

def install(name,source_access=True):
    reg=json.loads((ROOT/'REGISTRATION.json').read_bytes())
    allowed={canonical(p) for p in reg['source_files']} if source_access else set()
    roots=[ROOT,R2/'public',R2/'evidence/atcnet_2022',OFFICIAL,Path(sys.prefix)]
    roots=[canonical(p)+'/' for p in roots]
    log=(ROOT/'logs'/('ACCESS_'+name+'.jsonl')).open('a',encoding='utf8',buffering=1)
    def hook(event,args):
        if event!='open' or not args or not isinstance(args[0],str):return
        raw=args[0];path=canonical(raw);mode=str(args[1]) if len(args)>1 else ''
        source=path in allowed
        suffix=Path(path).suffix
        forbidden_asset=suffix in {'.npy','.npz','.mat','.gdf','.edf','.bdf','.fif','.pkl','.pickle','.pt','.pth','.h5','.hdf5'}
        research=path.startswith(('d:/bci_builds/','e:/bci_cv/'))
        permitted_root=any(path.startswith(r) for r in roots)
        reason=None
        if source and any(c in mode for c in 'wax+'):reason='source write forbidden'
        elif forbidden_asset and not source:reason='not one of the8 authorized source T files'
        elif research and not source and not permitted_root:reason='research path outside authorized code/output roots'
        record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),time_ns=time.time_ns(),
                    event='DENIED' if reason else 'open',path=raw,mode=mode,source_data=source,reason=reason)
        log.write(json.dumps(record,ensure_ascii=False)+'\n')
        if reason:
            (ROOT/'STOP.json').write_bytes((json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
            log.flush();os._exit(90)
    sys.addaudithook(hook)
    return reg,log
