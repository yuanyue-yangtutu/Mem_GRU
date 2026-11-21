"""Exactly one source-only fold/seed probe, <=2 epochs; never save weights."""
from pathlib import Path
import os,sys,json,time,datetime,statistics,ctypes,traceback
ROOT=Path(__file__).resolve().parent;MODEL=sys.argv[1]
assert MODEL in ['EEGNet','EEGNeX','ATCNet']
os.environ.update(PYTHONNOUSERSITE='1',TF_CPP_MIN_LOG_LEVEL='1',TF_FORCE_GPU_ALLOW_GROWTH='true',
 TF_ENABLE_ONEDNN_OPTS='0',CUDA_CACHE_PATH=str(ROOT/'cuda_cache'))
os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
from access_guard import install,R2,OFFICIAL
reg,access=install(MODEL,True)
OUT=ROOT/'output'/MODEL;OUT.mkdir(exist_ok=True)
start=time.perf_counter()

def write(p,v):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_bytes((json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf8'))
    for i in range(50):
        try:tmp.replace(p);return
        except PermissionError:time.sleep(.01)
    raise RuntimeError('cannot publish progress')

def live(stage,epoch=0,batch=0,total_batches=0,eta=None):
    write(OUT/'LIVE.json',dict(model=MODEL,held=1,seed=42,stage=stage,epoch=epoch,max_epochs=2,
        batch=batch,batches_per_phase=total_batches,eta_seconds=eta,eta_note='waiting empirical timing' if eta is None else 'empirical current-model estimate',
        held_scores_exported=False))

def check_machine():
    p=ROOT/'TELEMETRY_LATEST.json'
    if p.exists():
        v=json.loads(p.read_bytes())
        if v.get('ACLineStatus')!=1:raise RuntimeError('AC power lost;fit interrupted')
        if v.get('suspend_gap_detected'):raise RuntimeError('suspend/resume gap detected;fit interrupted')

try:
    (OUT/'ATTEMPT_STARTED.json').open('x',encoding='utf8').write(json.dumps(dict(seed=42,held=1,epochs_max=2,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())))
    check_machine();live('source load/split/normalizer replay')
    from source_pipeline import prepare
    xt,yt,xv,yv,manifest,pipeline=prepare(False)
    from baseline_factory import build
    t=time.perf_counter();tf,np,model,batch,lr,source_hashes,adaptations=build(MODEL,R2,OFFICIAL,42)
    model_build_seconds=time.perf_counter()-t
    config=json.loads((R2/'public/FROZEN_CONFIGS.json').read_bytes())[MODEL]
    assert batch==config['batch'] and abs(lr-config['lr'])<1e-12
    opt=tf.keras.optimizers.Adam(learning_rate=lr,beta_1=.9,beta_2=.999,epsilon=1e-7,amsgrad=False)
    model.compile(optimizer=opt,loss=tf.keras.losses.CategoricalCrossentropy(from_logits=False,label_smoothing=0),metrics=['accuracy'])
    t=time.perf_counter()
    xx=xt[:,:,:,None] if MODEL=='EEGNet' else xt[:,None,:,:]
    vv=xv[:,:,:,None] if MODEL=='EEGNet' else xv[:,None,:,:]
    with tf.device('/CPU:0'):
        train=tf.data.Dataset.from_tensor_slices((xx,np.eye(4,dtype=np.float32)[yt])).shuffle(len(yt),seed=42,reshuffle_each_iteration=True).batch(batch).prefetch(1)
        val=tf.data.Dataset.from_tensor_slices((vv,np.eye(4,dtype=np.float32)[yv])).batch(batch).prefetch(1)
        options=tf.data.Options();options.experimental_deterministic=True
        train=train.with_options(options);val=val.with_options(options)
    dataset_build_seconds=time.perf_counter()-t
    train_steps=(len(yt)+batch-1)//batch;val_steps=(len(yv)+batch-1)//batch
    tf.config.experimental.reset_memory_stats('GPU:0')

    class Timer(tf.keras.callbacks.Callback):
        def __init__(self):super().__init__();self.epochs=[];self.train_times=[];self.val_times=[];self.epoch=0
        def on_epoch_begin(self,epoch,logs=None):self.epoch=epoch+1;self.begin=time.perf_counter();self.tt=[];self.vt=[];check_machine()
        def on_train_batch_begin(self,batch,logs=None):self.batch_begin=time.perf_counter();check_machine()
        def on_train_batch_end(self,batch,logs=None):
            elapsed=time.perf_counter()-self.batch_begin;self.tt.append(elapsed);self.train_times.append(elapsed)
            assert all(np.isfinite(float(v)) for v in (logs or {}).values()),'nonfinite source training logs'
            eta=None
            if len(self.tt)>=3:eta=((2-self.epoch)*train_steps+(train_steps-batch-1))*statistics.median(self.tt[1:])
            live('source train',self.epoch,batch+1,train_steps,eta)
        def on_test_batch_begin(self,batch,logs=None):self.batch_begin=time.perf_counter();check_machine()
        def on_test_batch_end(self,batch,logs=None):
            elapsed=time.perf_counter()-self.batch_begin;self.vt.append(elapsed);self.val_times.append(elapsed)
            assert all(np.isfinite(float(v)) for v in (logs or {}).values()),'nonfinite source validation logs'
            live('source val',self.epoch,batch+1,val_steps)
        def on_epoch_end(self,epoch,logs=None):
            self.epochs.append(dict(epoch=epoch+1,wall_seconds=time.perf_counter()-self.begin,train_batch_seconds=self.tt,val_batch_seconds=self.vt))
            # Deliberately omit all loss/accuracy values and all predictions.
            write(OUT/'EPOCH_TIMINGS.json',self.epochs)
    cb=Timer();live('source fit:random initialization;no checkpoint/early selection')
    t=time.perf_counter();model.fit(train,validation_data=val,epochs=2,verbose=0,callbacks=[cb]);fit_seconds=time.perf_counter()-t
    assert len(cb.epochs)==2 and int(opt.iterations.numpy())==2*train_steps
    mem=tf.config.experimental.get_memory_info('GPU:0')
    result=dict(status='source_probe_complete_weights_discarded',held=1,source_owners=reg['source_subjects'],seed=42,epochs=2,
        train_shape=list(xt.shape),val_shape=list(xv.shape),batch=batch,train_steps_per_epoch=train_steps,val_steps_per_epoch=val_steps,
        optimizer_updates=int(opt.iterations.numpy()),params_total=model.count_params(),pipeline_timings=pipeline,
        model_build_seconds=model_build_seconds,dataset_build_seconds=dataset_build_seconds,fit_seconds=fit_seconds,
        epoch_timings=cb.epochs,peak_allocator_bytes=mem['peak'],current_allocator_bytes=mem['current'],
        process_wall_seconds=time.perf_counter()-start,source_train_ids_sha256=manifest['train_ids_sha256'],source_val_ids_sha256=manifest['val_ids_sha256'],
        normalizer_sha256=manifest['normalizer_sha256'],source_hashes=source_hashes,adaptations=adaptations,
        real_source_read=True,held_data_reads=0,E_OpenBMI_reads=0,held_scores_exported=False,source_scores_exported=False,
        weights_saved=False,weights_reused=False,formal_training_fits=0,configuration_changed_after_source_scores=False)
    write(OUT/'RESULT.json',result)
    del model,train,val,xt,xv;tf.keras.backend.clear_session();live('complete:weights discarded',2,eta=0)
    print(json.dumps({k:result[k] for k in ['status','params_total','fit_seconds','peak_allocator_bytes','optimizer_updates']}))
except BaseException as e:
    live('FAILED')
    write(OUT/'FAILURE.json',dict(error=repr(e),traceback=traceback.format_exc(),whole_fit_restart_required=True))
    raise
