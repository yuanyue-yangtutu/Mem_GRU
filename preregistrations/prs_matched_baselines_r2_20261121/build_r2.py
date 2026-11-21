"""Documentation packaging/static checks only; no real-data or model evaluation."""
from pathlib import Path
import ast,hashlib,json,math,shutil,subprocess
R=Path(__file__).resolve().parent;P=R/'public';P.mkdir(exist_ok=True)
OLD=R.parent/'PRS_MatchedBaselines_Revision1_20261121'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,v):
 p=P/n;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def copy(src,name):
 p=P/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(Path(src).read_bytes().replace(b'\r\n',b'\n'))

results={};audit=[];budgets={};runtime=json.loads((R/'evidence/ENVIRONMENT_LOCK.json').read_bytes())
for name,epochs in [('EEGNet',500),('EEGNeX',200),('ATCNet',1000)]:
 d=R/'output'/name;r=json.loads((d/'RESULT.json').read_bytes())
 assert r['status']=='synthetic_smoke_passed'
 assert r['synthetic_optimizer_steps']==23 and len(r['train_step_seconds'])==20
 results[name]=r;copy(d/'RESULT.json',f'results/{name}.json');copy(d/'MODEL_CONFIG.json',f'model_configs/{name}.json')
 events=[json.loads(s) for s in (d/'ACCESS.jsonl').read_text(encoding='utf8').splitlines()]
 denied=[e for e in events if e['event']=='DENIED']
 forbidden=[e for e in events if str(e.get('path','')).lower().endswith(('.npy','.npz','.mat','.gdf','.edf','.bdf','.fif','.pt','.pth','.h5','.hdf5','.pkl','.pickle'))]
 assert not denied and not forbidden
 audit.append(dict(model=name,log_sha256=sha(d/'ACCESS.jsonl'),open_events=len(events),
   forbidden_suffix_opens=0,denied=0,coverage='Python open audit, not OS-level DLL audit',
   script_sha256=sha(R/'synthetic_smoke.py'),source_code_hashes=r['source_hashes']))
 b=r['batch'];ts=math.ceil(1728/b);vs=math.ceil(576/b)
 med=27*epochs*(ts*r['train_median_s']+vs*r['eval_median_s'])/3600
 high=27*epochs*(ts*r['train_p90_s']+vs*max(r['eval_step_seconds']))/3600
 cold=27*sum(r['warmup_seconds'])/3600
 budgets[name]=dict(fits=27,max_epochs=epochs,batch=b,steps_train=ts,steps_val=vs,
   raw_median_GPU_h=med,raw_p90_GPU_h=high,cold_warmup_GPU_h=cold,
   planned_GPU_h=[1.5*med+cold,4*high+cold],peak_allocator_bytes=r['peak_allocator_bytes'],
   train_step_seconds=r['train_step_seconds'],eval_step_seconds=r['eval_step_seconds'])
training=[sum(x['planned_GPU_h'][j] for x in budgets.values()) for j in (0,1)]
total=[training[0]+1+.25,training[1]+6+2]
write('BUDGET_ESTIMATE.json',dict(hardware='RTX4060 Laptop8GB, driver560.94',measured_model_microbenchmarks=True,
 real_data_pipeline_measured=False,not_ETA=True,not_spending_authorization=True,models=budgets,
 formula='27*max_epochs*(ceil1728/batch*train_step+ceil576/batch*eval_step)/3600',
 planning_multipliers=[1.5,4],multipliers_measured=False,training_GPU_h=training,
 unmeasured_baseline_forward_buffer=[1,6],unmeasured_PRS_forward_buffer=[.25,2],stage1_total_GPU_h=total,
 unmeasured_CPU_bias_hours=[1,8],PRS_training_not_updated=True))
write('STATIC_AUDIT.json',dict(model_entrypoints_executed=False,only_AST_model_definitions=True,
 real_data_probe=False,source_replay=False,checks=audit,all_pass=True,
 EEGNeX_changes='Remove plot_model/internal compile only; retain official BN last axis',
 EEGNet_changes='kernel64 sample-rate-support adaptation; pure input transpose;batch16 author-example protocol supplement',
 ATCNet_changes='2022 upstream commit;paper0.0009;4 AST initializer call sites He->Glorot;exclude2023 added L2',
 target_path_access='No targeted data file IO; Python-hook coverage only; no claim of complete OS audit'))

copy(R/'evidence/FROZEN_CONFIGS.json','FROZEN_CONFIGS.json')
copy(R/'evidence/ENVIRONMENT_LOCK.json','ENVIRONMENT_LOCK.json')
copy(R/'evidence/conda-explicit.txt','conda-explicit.txt')
copy(R/'evidence/pip-only-lock.txt','pip-only-lock.txt')
public_env=json.loads((P/'ENVIRONMENT_LOCK.json').read_bytes())
public_env['archived_raw_conda_explicit_sha256']=public_env['conda_explicit_sha256']
public_env['conda_explicit_sha256']=sha(P/'conda-explicit.txt')
public_env['pip_only_lock_sha256']=sha(P/'pip-only-lock.txt')
public_env['conda_explicit_hash_object']='exact bytes of conda-explicit.txt in this Git package; archived raw CRLF export hash is separate'
public_env['runtime_files_hash_object']='actual installed binary/source bytes in isolated environment, not redistributed Git files'
write('ENVIRONMENT_LOCK.json',public_env)
copy(R/'evidence/BCI_UNCHANGED.json','BCI_UNCHANGED.json')
copy(R/'synthetic_smoke.py','synthetic_smoke.py');copy(R/'lock_runtime.py','lock_runtime.py');copy(__file__,'build_r2.py')
verify=(OLD/'verify_anonymous.py').read_text(encoding='utf8').replace('prs_matched_baselines_revision1_20261121','prs_matched_baselines_r2_20261121')
(P/'verify_anonymous.py').write_bytes(verify.encode('utf8'))
(P/'.gitattributes').write_bytes(b'* -text\n')

versions=json.loads((OLD/'SOURCE_REPOS.json').read_bytes())
for repo in versions:
 if repo['model']=='ATCNet':
  repo['R1_commit']=repo['commit'];repo['commit']='cd702831b1310476507dde3a10a9fc4dcd0d3cbd'
  repo['commit_url']='https://github.com/Altaheri/EEG-ATCNet/commit/'+repo['commit'];repo['reason']='2022 original paper recipe;not performance-selected'
  repo['files']=json.loads((R/'evidence/atcnet_2022/SOURCE.json').read_bytes())['files']
 repo['stage0_instantiated']=repo['model'] in results
 if repo['model']=='EEG-Conformer':repo['status']='excluded by user'
 if repo['model']=='DSGNet':repo['status']='literature only;not matched baseline'
source_files=[]
for model,repo,directory,commit,names in [
 ('EEGNet','vlawhern/arl-eegmodels','arl-eegmodels','4a512e503198db2010848813ead9afbf8cd54c97',['EEGModels.py']),
 ('EEGNeX','chenxiachan/EEGNeX','EEGNeX','044d7fb2a5b953c7004f30fe45db40d1ce57af5c',['BenchmarkModels.py']),
 ('ATCNet','Altaheri/EEG-ATCNet','EEG-ATCNet','cd702831b1310476507dde3a10a9fc4dcd0d3cbd',['models.py','attention_models.py','main.py'])]:
 folder=R.parent/'PRS_MatchedBaselines_Draft_20261121'/'sources'/directory
 for name in names:
  raw=subprocess.check_output(['git','-C',str(folder),'show',commit+':'+name])
  actual=(R/'evidence/atcnet_2022'/name if model=='ATCNet' else folder/name).read_bytes()
  source_files.append(dict(model=model,path=name,commit=commit,upstream_git_blob_sha256=hashlib.sha256(raw).hexdigest(),
   actual_local_execution_source_sha256=hashlib.sha256(actual).hexdigest(),
   differ_only_in_newlines=actual.replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n'),
   url=f'https://github.com/{repo}/blob/{commit}/{name}'))
write('SOURCE_VERSIONS.json',dict(upstream_hash_object='Git-commit blob bytes; local execution-source SHA separately in results',
 repositories=versions,source_files=source_files,actual_worker_sha256=sha(R/'synthetic_smoke.py'),
 parent_R1_commit='4f101eb62af515f76a2f81c832d84682ce7eb6e7'))

oldm=json.loads((OLD/'SHA256SUMS.json').read_bytes())
assert all(sha(OLD/n)==s['sha256'] for n,s in oldm['files'].items())
write('ENGINEERING_LEDGER.json',dict(
 failures=['Windows clone path parsing','offline cache missing','cache-directory configuration',
  'GPU precheck attempted before clone completed:missing numpy.version','invalid encoding alias',
  'BN metadata duplicate name','EEGNet channels-last input transpose missing'],
 failures_pre_optimizer=True,old_successful_profiles=dict(EEGNeX_steps=23,ATCNet_2023_steps=23),
 final_profiles_steps=69,total_synthetic_optimizer_updates=115,scientific_training_fits=0,
 formal_data_probe_epochs=0,real_EEG_reads=0,real_label_reads=0,E_OpenBMI_reads=0,
 PPU=dict(browser='same-chat in-app browser;actual visible new terminal',python='3.10.13',tensorflow_available=False,torch_available=True,
  model_jobs_submitted=0,paid_resources_created=0,interpretation='TF profile unsupported as currently installed;no silent PyTorch substitution'),
 conda_clone_success=True,bci_unchanged=True,R1_files_unchanged=True,
 temp_cleanup=dict(archives=72,GiB=1.41,scope='own completed-install compressed package cache only;environment/research assets retained'),
 raw_log_files=[dict(file=str(p.relative_to(R)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted((R/'logs').glob('*')) if p.is_file()]))
write('PRS_SOURCE_REPLAY_CONTRACT.json',dict(status='REGISTERED_NOT_RUN',scope='R2 historical five neural experts and their complete equal-weight mean only',
 max_abs_probability_error=2e-5,rtol=0,argmax_changes_required=0,near_tie_margin_flag=4e-5,
 source='explicit user preregistration this turn, not fit to target or source outcomes',
 rationale='small absolute float32/backend arithmetic engineering budget, coupled to zero decision changes and exact provenance/port binding',
 caveat='not empirically validated by stage0; does not establish training isolation or accuracy; no source fixture or weights read',
 old_full_PRS_45_gates_unchanged=True,old_2e_6_oracle_unchanged=True,old_E_OpenBMI_PLANS_unchanged=True))

# The normative text was authored with LF, but normalize every new public text once.
for p in P.rglob('*'):
 if p.is_file() and p.name!='SHA256SUMS.json':p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
write('PLAN_DRAFT.json',dict(title='同口径基线对比',revision='R2',status='FROZEN_DRAFT_AWAITING_USER_CONFIRMATION',
 normative_document=dict(file='PLAN_DRAFT.md',sha256=sha(P/'PLAN_DRAFT.md')),
 authorization=dict(phase0_static_and_synthetic=True,phase0_complete=True,formal_training=False,real_data_reads=False,
  source_fixture_replay=False,E_OpenBMI_target_reads=False,real_2epoch_probe=False,scoring=False),
 decisions=dict(budget_cap=None,money_cap=None,production_GPU_model_count=None,Conformer='excluded',
  stage2='decide after stage1 review',literature_arm='not now'),
 stage1=dict(baselines=list(results),seeds=[42,43,44],fits=81,PRS='historical frozen single system;development-selected;not equal three repetitions',
  protocol='P_T source8 T75/25;heldT288;raw22channels250Hz0–4s',GPU_hours=total),
 configs='FROZEN_CONFIGS.json',environment='ENVIRONMENT_LOCK.json',synthetic_results=[f'results/{m}.json' for m in results],
 source_replay='PRS_SOURCE_REPLAY_CONTRACT.json;not run',
 bias='post-fusion original probabilities0..t inclusive;first20 unchanged;lambda=.1+20/n;original pinned solver;balanced prior assumption;not pure zero calibration',
 statistics='R1 paired person-block50000 bootstrap;seed20261121;raw/corrected;development selection caveat',
 prerequisites_before_formal_work=['user R2 review/execution authorization','explicit budget cap and production card allocation',
  'authorized real source input metadata/fixture gates, no replacement or tolerance relaxation beyond explicitly registered contract'],
 ready_for_formal_execution=False,hash_object='exact bytes in the Git commit'))
files={}
for p in sorted(P.rglob('*')):
 if p.is_file() and p.name!='SHA256SUMS.json':
  b=p.read_bytes();assert b'\r' not in b and not b.startswith(b'\xef\xbb\xbf')
  files[p.relative_to(P).as_posix()]=dict(sha256=sha(p),bytes=len(b))
write('SHA256SUMS.json',dict(hash_object='exact bytes in the Git commit',encoding='UTF8,noBOM,LF',
 self_hash='excluded to avoid recursion;full commit and anonymous receipt bind manifest itself',files=files))
print(json.dumps(dict(PLAN_DRAFT_sha256=sha(P/'PLAN_DRAFT.json'),markdown_sha256=sha(P/'PLAN_DRAFT.md'),
 manifest_items=len(files),stage1_GPU_hours=total,public_bytes=sum(p.stat().st_size for p in P.rglob('*') if p.is_file()))))
