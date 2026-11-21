"""Record isolated runtime/configuration metadata only. No model/data loading."""
from pathlib import Path
import os, sys, json, hashlib, inspect, importlib.metadata as md
R=Path(__file__).resolve().parent
os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
import tensorflow as tf
import keras

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(n,v):(R/'evidence'/n).write_bytes((json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf8'))

configs={
 'EEGNet':dict(lr=.001,batch=16,max_epochs=500,kernel_samples=64,
  checkpoint=dict(monitor='val_loss',mode='min',tie='earliest strict minimum',min_delta=0),scheduler=None,early_stopping=None,
  batch_provenance='original MI paper does not specify batch; fixed16 from official author example as disclosed protocol adaptation, not asserted original MI default',
  kernel_provenance='32/128=.250s SMR paper support ->64/250=.256s; fixed rate adaptation before real data, not result-selected'),
 'EEGNeX':dict(lr=.001,batch=128,max_epochs=200,
  checkpoint=dict(monitor='val_accuracy',mode='max',tie='earliest strict maximum',min_delta=0),
  scheduler=dict(monitor='val_accuracy',mode='max',factor=.5,patience=5,min_delta=1e-4,cooldown=0,min_lr=0),
  early_stopping=dict(monitor='val_accuracy',mode='max',patience=20,min_delta=0,baseline=None,restore_best_weights=True),
  monitor_provenance='paper3.3 accuracy takes precedence over notebook val_loss;200 cap from notebook; no target data used'),
 'ATCNet':dict(lr=.0009,batch=64,max_epochs=1000,
  checkpoint=dict(monitor='val_accuracy',mode='max',tie='earliest strict maximum',min_delta=0),
  scheduler=dict(monitor='val_loss',mode='min',factor=.9,patience=20,min_delta=1e-4,cooldown=0,min_lr=.0001),
  early_stopping=dict(monitor='val_accuracy',mode='max',patience=300,min_delta=0,baseline=None,restore_best_weights=True),
  code_commit='cd702831b1310476507dde3a10a9fc4dcd0d3cbd',
  provenance='paper III-C and original2022 main.py agree .0009/64/1000/300; newest2023 architecture L2 additions excluded',
  initialization='paper Glorot uniform; four TCN kernel_initializer he_uniform AST call sites explicitly changed; no structural change')}
for name,c in configs.items():
    c['optimizer']=dict(name='tensorflow.keras.optimizers.Adam',learning_rate=c['lr'],beta_1=.9,beta_2=.999,epsilon=1e-7,
      amsgrad=False,decay=0.0,decoupled_weight_decay=0.0,weight_decay_note='legacy Adam has no decoupled weight_decay argument; no add-on decay')
    c['loss']=dict(name='CategoricalCrossentropy',from_logits=False,label_smoothing=0,reduction='sum_over_batch_size',regularization='exact original layer constraints; no added L2')
    c['BN']=dict(epsilon=.001,momentum=.99,center=True,scale=True,axis='per-layer MODEL_CONFIG JSON; EEGNeX retains official last-axis normalization')
    c['framework']=dict(Python=sys.version.split()[0],tensorflow=tf.__version__,keras=keras.__version__,backend_epsilon=tf.keras.backend.epsilon(),
       dtype='float32',TF32=False,JIT=False,mixed_precision=False,image_data_format='channels_last',
       seed=20261121,full_op_determinism=False,determinism_note='fixed seeds; no promise of bitwise cross-driver equality')
    c['effective_callback_attributes']={}
    for kind,cls in [('scheduler',tf.keras.callbacks.ReduceLROnPlateau),('early_stopping',tf.keras.callbacks.EarlyStopping)]:
        if c[kind]:
            obj=cls(**c[kind]);fields=['monitor','mode','factor','patience','min_delta','cooldown','min_lr','restore_best_weights','baseline']
            c['effective_callback_attributes'][kind]={k:getattr(obj,k) for k in fields if hasattr(obj,k)}
dump('FROZEN_CONFIGS.json',configs)

files={}
for obj in [tf.keras.optimizers.Adam,tf.keras.layers.BatchNormalization,tf.keras.callbacks.EarlyStopping,
            tf.keras.callbacks.ReduceLROnPlateau,tf.keras.layers.MultiHeadAttention,tf.keras.losses.CategoricalCrossentropy]:
    p=Path(inspect.getsourcefile(obj)); files[str(p.relative_to(sys.prefix)).replace('\\','/')]=sha(p)
for p in (Path(sys.prefix)/'Library/bin').glob('*.dll'):
    if p.name.lower().startswith(('cudnn','cublas','cudart')):files['Library/bin/'+p.name]=sha(p)
versions=sorted((d.metadata['Name'],d.version) for d in md.distributions())
packages=json.loads((R/'evidence/conda-list.json').read_text(encoding='utf-8-sig'))
pip_only=sorted((p['name'],p['version']) for p in packages if p.get('channel')=='pypi')
(R/'evidence/pip-only-lock.txt').write_bytes(('\n'.join(n+'=='+v for n,v in pip_only)+'\n').encode('utf8'))
dump('ENVIRONMENT_LOCK.json',dict(prefix=str(Path(sys.prefix)),Python=sys.version,packages=versions,
    pip_only=pip_only,runtime_files_sha256=files,TF_build=tf.sysconfig.get_build_info(),
    conda_explicit_sha256=sha(R/'evidence/conda-explicit.txt'),raw_pip_freeze_sha256=sha(R/'evidence/pip-freeze.txt'),
    independent_from_bci=True,source_clone='finger-bci-author-tf210-gpu; copied to separate E-drive prefix',
    supported_interpreter='PyCharm: E:/BCI_CV/.conda/prs_stage0_tf210/python.exe',
    version_adaptation='EEGNeX author notebook saysTF/Keras2.8; current Windows GPU profile uses2.10 explicitly; not literal original environment reproduction'))
print(json.dumps(dict(configs=list(configs),runtime_hashes=len(files),installed_distributions=len(versions),pip_only=len(pip_only))))
