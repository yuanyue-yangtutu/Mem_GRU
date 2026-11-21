"""Authorized source-T cache only; no target loader, no pretrained model loading."""
from pathlib import Path
import json,hashlib,time
ROOT=Path(__file__).resolve().parent

def encoded(x):return (json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8')
def digest(x):return hashlib.sha256(encoded(x)).hexdigest()

def prepare(write_manifest=False):
    import numpy as np
    started=time.perf_counter();reg=json.loads((ROOT/'REGISTRATION.json').read_bytes())
    rng=np.random.default_rng(reg['split_seed']);xs=[];ys=[];ids=[];train=[];val=[];files=[];offset=0
    for owner,path in zip(reg['source_subjects'],reg['source_files']):
        path=Path(path)
        assert path.name==f'S{owner}.npz' and owner!=reg['held']
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(2**20),b''):h.update(chunk)
        with np.load(path,allow_pickle=False) as z:
            fields=list(z.files)
            assert 'x' in fields and 'y' in fields,(path,fields)
            x=np.asarray(z['x']);y=np.asarray(z['y'])
        assert x.shape==(288,22,1000),(path,x.shape)
        assert y.shape==(288,) and np.array_equal(np.unique(y),[0,1,2,3]),(path,y.shape,np.unique(y))
        storage_dtype=str(x.dtype)
        assert np.isfinite(x).all() and x.dtype in (np.float32,np.float64),(path,x.dtype)
        # Frozen R2 specifies float32 at the model port, not the cache storage dtype.
        x=x.astype(np.float32,copy=False)
        assert np.isfinite(x).all()
        counts=[int((y==c).sum()) for c in range(4)]
        assert counts==[72]*4,(path,counts)
        local=[f'IV2a:S{owner:02d}:T:cache_row{j:03d}' for j in range(288)]
        source_train=[];source_val=[]
        for c in range(4):
            ix=rng.permutation(np.flatnonzero(y==c));source_train.extend(ix[:54].tolist());source_val.extend(ix[54:].tolist())
        train.extend((np.asarray(source_train)+offset).tolist());val.extend((np.asarray(source_val)+offset).tolist())
        files.append(dict(owner=owner,logical_file=path.name,sha256=h.hexdigest(),fields=fields,
            shape=list(x.shape),storage_dtype=storage_dtype,model_port_dtype=str(x.dtype),label_shape=list(y.shape),trial_ids=local,
            train_ids=[local[j] for j in source_train],val_ids=[local[j] for j in source_val],
            train_ids_sha256=digest([local[j] for j in source_train]),val_ids_sha256=digest([local[j] for j in source_val])))
        xs.append(x);ys.append(y);ids.extend(local);offset+=len(y)
    x=np.concatenate(xs);y=np.concatenate(ys).astype(np.int64);train=np.array(train);val=np.array(val)
    assert len(train)==1728 and len(val)==576 and not np.intersect1d(train,val).size
    load_s=time.perf_counter()-started;beg=time.perf_counter()
    mu=float(x[train].mean(dtype=np.float64));sd=float(x[train].std(dtype=np.float64,ddof=0));assert sd>0
    normalizer=dict(mean=mu,sd=sd,ddof=0,fit_dtype='float64',fit_source_owners=reg['source_subjects'],
        fit_trial_ids_sha256=digest([ids[j] for j in train]),validation_used_for_fit=False,target_used=False)
    xt=((x[train].astype(np.float64)-mu)/sd).astype(np.float32)
    xv=((x[val].astype(np.float64)-mu)/sd).astype(np.float32)
    normal_s=time.perf_counter()-beg
    manifest=dict(held=reg['held'],source_owners=reg['source_subjects'],registration_sha256=hashlib.sha256((ROOT/'REGISTRATION.json').read_bytes()).hexdigest(),
        split_seed=reg['split_seed'],split_algorithm='PCG64 default_rng, owner2..9/class0..3;permuted72:first54 train,last18 val',
        trial_id_definition='archived cache row identity;not independently verified native GDF acquisition event IDs',
        train_trial_ids=[ids[j] for j in train],val_trial_ids=[ids[j] for j in val],
        train_ids_sha256=digest([ids[j] for j in train]),val_ids_sha256=digest([ids[j] for j in val]),
        raw_shape=list(x.shape),train_shape=list(xt.shape),val_shape=list(xv.shape),normalizer_sha256=digest(normalizer),
        normalizer_source='only source-train1728 trials;one population scalar mean/std,ddof0;float64 fit,float32 transform',
        original_raw_preprocessing_benchmarked=False,source_files=files)
    # Hashable identity excludes timings; the exact same source split/norm must replay across all3 probes.
    if write_manifest:
        (ROOT/'SOURCE_MANIFEST_PRIVATE.json').write_bytes(encoded(manifest))
        (ROOT/'NORMALIZER_PRIVATE.json').write_bytes(encoded(normalizer))
    else:
        archived=json.loads((ROOT/'SOURCE_MANIFEST_PRIVATE.json').read_bytes())
        assert digest(archived)==digest(manifest),'Source/split/normalizer changed;stop before fitting'
    return xt,y[train],xv,y[val],manifest,dict(source_load_and_verify_seconds=load_s,normalizer_and_transform_seconds=normal_s)

if __name__=='__main__':
    from access_guard import install
    install('metadata',True)
    xt,yt,xv,yv,m,t=prepare(True)
    (ROOT/'METADATA_COMPLETE.json').write_bytes(encoded(dict(status='source_metadata_complete',held=m['held'],
        source_owners=m['source_owners'],train_shape=m['train_shape'],val_shape=m['val_shape'],
        manifest_sha256=hashlib.sha256((ROOT/'SOURCE_MANIFEST_PRIVATE.json').read_bytes()).hexdigest(),timings=t)))
    print(json.dumps(dict(train_shape=m['train_shape'],val_shape=m['val_shape'],source_owners=m['source_owners'])))
