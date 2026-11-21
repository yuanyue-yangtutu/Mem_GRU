"""One whole source-only fit. No target loader or target prediction."""
from common import *
import sys,importlib.util,traceback,statistics
fit_id=sys.argv[1];out=ROOT/'fits'/fit_id/'attempt001'
reg=read(out/'REGISTRATION.json')
os.environ.update(PYTHONNOUSERSITE='1',TF_CPP_MIN_LOG_LEVEL='1',TF_FORCE_GPU_ALLOW_GROWTH='true',TF_ENABLE_ONEDNN_OPTS='0',CUDA_VISIBLE_DEVICES='0',CUDA_CACHE_PATH=str(ROOT/'tmp/cuda'),TEMP=str(ROOT/'tmp'),TMP=str(ROOT/'tmp'))
os.add_dll_directory(str(ENV/'Library/bin'))
verify_binding()
from access_guard import install
access=install(out,reg)
started=time.perf_counter()
def stopcheck():
    if (ROOT/'STOP.json').exists():raise RuntimeError('global stop: '+str(read(ROOT/'STOP.json')))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def live(stage,epoch=0,batch=0,steps=0,eta=None):
    put(out/'LIVE.json',dict(fit_id=fit_id,model=reg['model'],held=reg['held'],seed=reg['seed'],stage=stage,epoch=epoch,max_epochs=config['max_epochs'] if 'config' in globals() else None,batch=batch,steps=steps,eta_seconds=eta,updated_utc=now()))
try:
    stopcheck();live('loading authorized source T')
    pipeline=module('source_pipeline',ROOT/'source_pipeline.py');pipeline.ROOT=out
    xt,yt,xv,yv,manifest,timing=pipeline.prepare(True)
    factory=module('baseline_factory',ROOT/'baseline_factory.py')
    tf,np,model,batch,lr,source_hashes,adaptations=factory.build(reg['model'],R2,OFFICIAL,reg['seed'])
    assert tf.__version__=='2.10.0' and sys.version_info[:2]==(3,8)
    config=read(ROOT/'public/FROZEN_CONFIGS.json')[reg['model']]
    assert batch==config['batch'] and lr==config['lr']
    optimizer=tf.keras.optimizers.Adam(learning_rate=lr,beta_1=.9,beta_2=.999,epsilon=1e-7,amsgrad=False)
    model.compile(optimizer=optimizer,loss=tf.keras.losses.CategoricalCrossentropy(from_logits=False,label_smoothing=0,reduction='sum_over_batch_size'),metrics=['accuracy'])
    put(out/'MODEL_CONFIG.json',json.loads(model.to_json()))
    put(out/'INPUT_BINDING.json',dict(registration_sha256=sha(out/'REGISTRATION.json'),source_train_ids_sha256=manifest['train_ids_sha256'],source_val_ids_sha256=manifest['val_ids_sha256'],normalizer_sha256=sha(out/'NORMALIZER_PRIVATE.json'),config_sha256=sha(ROOT/'public/FROZEN_CONFIGS.json'),source_hashes=source_hashes,adaptations=adaptations))
    xx=xt[:,:,:,None] if reg['model']=='EEGNet' else xt[:,None,:,:]
    vv=xv[:,:,:,None] if reg['model']=='EEGNet' else xv[:,None,:,:]
    with tf.device('/CPU:0'):
        train=tf.data.Dataset.from_tensor_slices((xx,np.eye(4,dtype=np.float32)[yt])).shuffle(len(yt),seed=reg['seed'],reshuffle_each_iteration=True).batch(batch).prefetch(1)
        val=tf.data.Dataset.from_tensor_slices((vv,np.eye(4,dtype=np.float32)[yv])).batch(batch).prefetch(1)
        options=tf.data.Options();options.experimental_deterministic=True
        train=train.with_options(options);val=val.with_options(options)
    steps=(len(yt)+batch-1)//batch;maxepochs=config['max_epochs']
    epochlog=(out/'SOURCE_HISTORY.jsonl').open('a',encoding='utf8',buffering=1)
    class Monitor(tf.keras.callbacks.Callback):
        def __init__(self):super().__init__();self.durations=[];self.best=None;self.best_epoch=None;self.lastlive=0
        def on_epoch_begin(self,epoch,logs=None):self.epoch=epoch;self.begin=time.perf_counter();stopcheck()
        def on_train_batch_begin(self,batch,logs=None):stopcheck()
        def on_test_batch_begin(self,batch,logs=None):stopcheck()
        def on_train_batch_end(self,b,logs=None):
            if not all(np.isfinite(float(v)) for v in (logs or {}).values()):raise RuntimeError('nonfinite source metrics')
            if time.monotonic()-self.lastlive>2:
                eta=statistics.median(self.durations[-10:])*(maxepochs-self.epoch-(b+1)/steps) if self.durations else None
                live('source train',self.epoch+1,b+1,steps,eta);self.lastlive=time.monotonic()
        def on_epoch_end(self,epoch,logs=None):
            stopcheck();logs=logs or {}
            if not all(np.isfinite(float(v)) for v in logs.values()):raise RuntimeError('nonfinite validation metrics')
            v=float(logs[config['checkpoint']['monitor']]);better=self.best is None or (v<self.best if config['checkpoint']['mode']=='min' else v>self.best)
            if better:
                model.save_weights(str(out/'best.weights.h5'));self.best=v;self.best_epoch=epoch+1
            dt=time.perf_counter()-self.begin;self.durations.append(dt)
            epochlog.write(json.dumps(dict(epoch=epoch+1,seconds=dt,source_metrics={k:float(v) for k,v in logs.items()},lr=float(tf.keras.backend.get_value(optimizer.lr))))+'\n')
            live('source epoch complete',epoch+1,steps,steps,statistics.median(self.durations[-10:])*(maxepochs-epoch-1))
    mon=Monitor();callbacks=[mon]
    if config['scheduler']:callbacks.append(tf.keras.callbacks.ReduceLROnPlateau(**config['scheduler']))
    if config['early_stopping']:callbacks.append(tf.keras.callbacks.EarlyStopping(**config['early_stopping']))
    tf.config.experimental.reset_memory_stats('GPU:0')
    t=time.perf_counter();history=model.fit(train,validation_data=val,epochs=maxepochs,verbose=0,callbacks=callbacks);fitseconds=time.perf_counter()-t
    stopcheck();assert mon.best_epoch is not None
    # best.weights was selected only from source validation, earliest strict optimum.
    model.load_weights(str(out/'best.weights.h5'))
    assert (out/'best.weights.h5').stat().st_size>0
    epochlog.close()
    binding=read(out/'INPUT_BINDING.json')
    done=dict(status='TRAINING_COMPLETED',fit_id=fit_id,model=reg['model'],held=reg['held'],seed=reg['seed'],source_subjects=reg['source_subjects'],epochs_completed=len(mon.durations),best_epoch=mon.best_epoch,fit_seconds=fitseconds,process_wall_seconds=time.perf_counter()-started,optimizer_updates=int(optimizer.iterations.numpy()),peak_allocator_bytes=tf.config.experimental.get_memory_info('GPU:0')['peak'],model_sha256=sha(out/'best.weights.h5'),model_file=str(out/'best.weights.h5'),metadata_hashes={n:sha(out/n) for n in ['REGISTRATION.json','NORMALIZER_PRIVATE.json','SOURCE_MANIFEST_PRIVATE.json','MODEL_CONFIG.json','INPUT_BINDING.json']},source_only=True,held_inference=False,created_utc=now())
    put(out/'TRAINING_COMPLETED.json',done);live('TRAINING_COMPLETED',len(mon.durations),steps,steps,0)
    print(json.dumps(dict(fit_id=fit_id,status=done['status'],model_sha256=done['model_sha256'])),flush=True)
except BaseException as e:
    put(out/'FAILURE.json',dict(error=repr(e),traceback=traceback.format_exc(),whole_fit_restart_required=True,utc=now()));live('FAILED');raise
