"""Stage0 ONLY: synthetic tensors, official AST definitions, no dataset IO.
Run one model per fresh process. No checkpoints or real-data probes are loaded.
"""
import os, sys, json, time, hashlib, ast, traceback, statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCES=ROOT.parent/'PRS_MatchedBaselines_Draft_20261121'/'sources'
MODEL=sys.argv[1]
assert MODEL in ('EEGNet','EEGNeX','ATCNet')
OUT=ROOT/'output'/MODEL
OUT.mkdir(parents=True,exist_ok=True)
os.environ.update(PYTHONNOUSERSITE='1',TF_CPP_MIN_LOG_LEVEL='1',TF_FORCE_GPU_ALLOW_GROWTH='true',
    TF_ENABLE_ONEDNN_OPTS='0',CUDA_CACHE_PATH=str(ROOT/'cuda_cache'))
os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
access=(OUT/'ACCESS.jsonl').open('w',encoding='utf8',buffering=1)

def hook(event,args):
    if event!='open' or not args or not isinstance(args[0],str):return
    p=args[0].replace('\\','/'); low=p.lower()
    denied=low.endswith(('.gdf','.edf','.bdf','.mat','.fif','.npy','.npz','.pkl','.pickle','.pt','.pth','.h5','.hdf5'))
    project=low.startswith(('d:/bci_builds/','e:/bci_cv/'))
    allow=any(low.startswith(str(x).replace('\\','/').lower()+'/') for x in [ROOT,SOURCES,Path(sys.prefix)])
    if denied or (project and not allow):
        access.write(json.dumps(dict(event='DENIED',path=p))+'\n')
        raise RuntimeError('Stage0 real-data/asset boundary: '+p)
    access.write(json.dumps(dict(event='open',path=p,mode=str(args[1]) if len(args)>1 else None))+'\n')
sys.addaudithook(hook)

def save(name,v):
    (OUT/name).write_bytes((json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf8'))

def live(stage,done=0,total=23,eta=None):
    save('LIVE.json',dict(model=MODEL,scope='synthetic-only',stage=stage,completed=done,total=total,
        eta_seconds=eta,ETA_status='waiting for empirical timing' if eta is None else 'empirical synthetic steps',
        real_data_reads=0))

def run():
    live('importing isolated TF; no empirical ETA')
    import numpy as np
    import tensorflow as tf
    import tensorflow.keras.layers as layers
    from tensorflow.keras.models import Model,Sequential
    from tensorflow.keras import backend as K
    from tensorflow.keras.constraints import max_norm
    from tensorflow.keras.regularizers import L2,l1_l2,l2
    import importlib.metadata as metadata
    gpus=tf.config.list_physical_devices('GPU')
    assert gpus,'GPU unavailable: CPU timing cannot stand in for GPU budget'
    for gpu in gpus:tf.config.experimental.set_memory_growth(gpu,True)
    tf.config.experimental.enable_tensor_float_32_execution(False)
    tf.keras.utils.set_random_seed(20261121)
    tf.config.optimizer.set_jit(False)
    K.set_image_data_format('channels_last')
    namespace=dict(tf=tf,np=np,K=K,Model=Model,Sequential=Sequential,max_norm=max_norm,L2=L2,l1_l2=l1_l2,l2=l2)
    namespace.update({n:getattr(layers,n) for n in dir(layers) if not n.startswith('_')})
    adaptations=[];source_hashes={}

    def definitions(path,select=None,remove_side_effects=False,paper_initialization=False):
        raw=path.read_bytes()
        source_key=str(path.relative_to(SOURCES)) if SOURCES in path.parents else str(path.relative_to(ROOT))
        source_hashes[source_key]=hashlib.sha256(raw).hexdigest()
        parsed=ast.parse(raw.decode('utf-8-sig'))
        funcs=[n for n in parsed.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and (select is None or n.name in select)]
        if remove_side_effects:
            for fn in funcs:
                original=len(fn.body)
                fn.body=[n for n in fn.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and
                    ((isinstance(n.value.func,ast.Name) and n.value.func.id=='plot_model') or
                     (isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='compile')))]
                if original!=len(fn.body):adaptations.append(dict(function=fn.name,removed='plot_model and internal compile only; forward layers unchanged'))
        if paper_initialization:
            changed=0
            for fn in funcs:
                for call in ast.walk(fn):
                    if isinstance(call,ast.Call):
                        for kw in call.keywords:
                            if kw.arg=='kernel_initializer' and isinstance(kw.value,ast.Constant) and kw.value.value=='he_uniform':
                                kw.value.value='glorot_uniform';changed+=1
            adaptations.append(dict(function='TCN_block',paper_initialization_override='he_uniform -> glorot_uniform',call_sites=changed,reason='original paper III-C says Glorot; fixed before real data'))
        module=ast.Module(body=funcs,type_ignores=[])
        exec(compile(ast.fix_missing_locations(module),str(path),'exec'),namespace)

    if MODEL=='EEGNet':
        definitions(SOURCES/'arl-eegmodels/EEGModels.py',{'EEGNet'})
        # 64/250=.256s preserves SMR paper32/128=.250s temporal support.
        # This is a disclosed source-independent rate adaptation, not literal32 samples.
        model=namespace['EEGNet'](nb_classes=4,Chans=22,Samples=1000,dropoutRate=.25,kernLength=64,F1=8,D=2,F2=16)
        batch=16;lr=.001
    elif MODEL=='EEGNeX':
        definitions(SOURCES/'EEGNeX/BenchmarkModels.py',{'EEGNeX_8_32'},True)
        model=namespace['EEGNeX_8_32'](1000,22,4)
        batch=128;lr=.001
    else:
        old=ROOT/'evidence/atcnet_2022'
        definitions(old/'attention_models.py')
        definitions(old/'models.py',{'ATCNet','Conv_block','TCN_block'},paper_initialization=True)
        model=namespace['ATCNet'](n_classes=4,in_chans=22,in_samples=1000,n_windows=5,attention='mha',eegn_poolSize=7)
        batch=64;lr=.0009

    opt=tf.keras.optimizers.Adam(learning_rate=lr,beta_1=.9,beta_2=.999,epsilon=1e-7,amsgrad=False)
    ce=tf.keras.losses.CategoricalCrossentropy(from_logits=False,reduction='sum_over_batch_size')
    x=tf.random.stateless_normal([batch,1,22,1000],seed=[20261121,1])
    if MODEL=='EEGNet':
        x=tf.transpose(x,[0,2,3,1])
        adaptations.append(dict(function='EEGNet input',change='B,1,C,T -> B,C,T,1',signal_values_changed=False))
    y=tf.one_hot(tf.range(batch)%4,4)
    assert 'GPU' in x.device,x.device
    bn=[]
    for layer in model.layers:
        if isinstance(layer,layers.BatchNormalization):bn.append(layer.get_config())
    save('MODEL_CONFIG.json',dict(model_json=json.loads(model.to_json()),BN=bn,
        optimizer=opt.get_config(),loss=ce.get_config(),source_hashes=source_hashes,adaptations=adaptations,
        tensor_layout='B,1,22,1000; common raw interface; each model retains official internal axes',
        EEGNeX_BN_note='official unmodified default axis=-1 retained; in channels_first blocks this normalizes last/time axis; not silently fixed' if MODEL=='EEGNeX' else None))

    @tf.function
    def train_step():
        with tf.GradientTape() as tape:
            p=model(x,training=True)
            loss=ce(y,p)
            if model.losses:loss+=tf.add_n(model.losses)
        grads=tape.gradient(loss,model.trainable_variables)
        for g in grads:
            assert g is not None
            tf.debugging.assert_all_finite(g,'nonfinite gradient')
        opt.apply_gradients(zip(grads,model.trainable_variables))
        tf.debugging.assert_all_finite(loss,'nonfinite loss')
        return loss

    @tf.function
    def eval_step():return model(x,training=False)

    tf.config.experimental.reset_memory_stats('GPU:0')
    warm=[];times=[];eval_times=[]
    for i in range(23):
        live('synthetic forward/backward (includes optimizer update)',i)
        start=time.perf_counter(); value=float(train_step().numpy()); elapsed=time.perf_counter()-start
        (warm if i<3 else times).append(elapsed)
        live('synthetic forward/backward',i+1,eta=(22-i)*statistics.median(times) if times else None)
    for i in range(6):
        start=time.perf_counter();p=eval_step().numpy();elapsed=time.perf_counter()-start
        if i:eval_times.append(elapsed)
    assert p.shape==(batch,4) and np.isfinite(p).all() and np.max(abs(p.sum(1)-1))<1e-5
    memory=tf.config.experimental.get_memory_info('GPU:0')
    result=dict(model=MODEL,status='synthetic_smoke_passed',python=sys.version,TF=tf.__version__,keras=metadata.version('keras'),numpy=np.__version__,
        device=tf.config.experimental.get_device_details(gpus[0]),batch=batch,shape=[batch,1,22,1000],classes=4,
        source_hashes=source_hashes,AST_adaptations=adaptations,params_total=model.count_params(),
        params_trainable=int(sum(np.prod(v.shape) for v in model.trainable_variables)),
        optimizer=opt.get_config(),warmup_seconds=warm,train_step_seconds=times,eval_step_seconds=eval_times,
        train_median_s=statistics.median(times),train_min_s=min(times),train_max_s=max(times),
        train_p90_s=float(np.quantile(times,.9)),eval_median_s=statistics.median(eval_times),
        peak_allocator_bytes=memory['peak'],current_allocator_bytes=memory['current'],
        synthetic_optimizer_steps=23,output_shape=list(p.shape),row_sum_max_error=float(np.max(abs(p.sum(1)-1))),
        scientific_training_fits=0,real_EEG_reads=0,real_label_reads=0,E_or_OpenBMI_target_reads=0,
        caveat='synthetic GPU microbenchmark; not real-data throughput or convergence evidence; no source fixture or weights read')
    save('RESULT.json',result);live('complete',23,eta=0)
    print(json.dumps({k:result[k] for k in ['model','params_total','train_median_s','eval_median_s','peak_allocator_bytes','status']}))

try:run()
except BaseException as e:
    save('FAILURE.json',dict(error=repr(e),traceback=traceback.format_exc(),scope='synthetic only',real_data_reads=0))
    live('FAILED')
    raise
