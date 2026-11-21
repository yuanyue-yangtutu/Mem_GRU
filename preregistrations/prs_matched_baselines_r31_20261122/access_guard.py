"""Exact per-fit source allowlist; Python audit, not an OS sandbox."""
from common import *
import sys
def canonical(p):return os.path.normcase(str(Path(p).resolve())).replace('\\','/')
def install(out,reg):
    allowed={canonical(p) for p in reg['source_files']}
    assert len(allowed)==8 and all(Path(p).name!='S%d.npz'%reg['held'] for p in allowed)
    roots=[canonical(p)+'/' for p in [ROOT,R2/'public',R2/'evidence/atcnet_2022',OFFICIAL,Path(sys.prefix)]]
    log=(out/'ACCESS.jsonl').open('a',encoding='utf8',buffering=1)
    output=canonical(out)+'/'
    def hook(event,args):
        if event!='open' or not args or not isinstance(args[0],str):return
        raw=args[0];p=canonical(raw);mode=str(args[1]) if len(args)>1 else ''
        source=p in allowed;reason=None
        asset=Path(p).suffix.lower() in {'.npy','.npz','.mat','.gdf','.edf','.bdf','.fif','.pkl','.pickle','.pt','.pth','.h5','.hdf5'}
        if source and any(c in mode for c in 'wax+'):reason='source write'
        elif asset and not source and not p.startswith(output):reason='not current-fold source or own new fit artifact'
        elif p.startswith(('d:/bci_builds/','e:/bci_cv/')) and not source and not any(p.startswith(r) for r in roots):reason='research path outside code/output allowlist'
        record=dict(utc=now(),event='DENIED' if reason else 'open',path=raw,mode=mode,source_data=source,held=reg['held'],reason=reason)
        log.write(json.dumps(record,ensure_ascii=False)+'\n')
        if reason:
            put(ROOT/'STOP.json',record);log.flush();os._exit(90)
    sys.addaudithook(hook)
    return log
