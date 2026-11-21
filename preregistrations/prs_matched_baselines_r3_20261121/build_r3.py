"""Metadata-only R3 assembly. Never load EEG arrays, weights or prediction files."""
from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parent;P=R/'public';P.mkdir(exist_ok=True)
R2=R.parent/'PRS_MatchedBaselines_R2_Stage0_20261121'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,v):
    p=P/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def copy(p,n):
    dest=P/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(Path(p).read_bytes().replace(b'\r\n',b'\n'))

reg=json.loads((R/'REGISTRATION.json').read_bytes());m=json.loads((R/'SOURCE_MANIFEST_PRIVATE.json').read_bytes())
assert reg['held']==1 and reg['source_subjects']==list(range(2,10)) and reg['epochs_per_model']==2
assert not (R/'STOP.json').exists()
assert all(Path(p).resolve().name==f'S{s}.npz' for s,p in zip(reg['source_subjects'],reg['source_files']))
copy(R/'REGISTRATION.json','REGISTRATION.json')
source=[]
for item in m['source_files']:
    selected={k:item[k] for k in ['owner','logical_file','sha256','fields','shape','storage_dtype','model_port_dtype','label_shape','trial_ids','train_ids_sha256','val_ids_sha256']}
    selected['train_count']=len(item['train_ids']);selected['val_count']=len(item['val_ids']);source.append(selected)
write('SOURCE_MANIFEST_PUBLIC.json',dict(held=1,source_owners=reg['source_subjects'],source_files=source,
    source_hash_object='local archived sourceT NPZ file bytes;EEG not redistributed',
    private_manifest_sha256=sha(R/'SOURCE_MANIFEST_PRIVATE.json'),registration_sha256=sha(R/'REGISTRATION.json'),
    train_shape=m['train_shape'],val_shape=m['val_shape'],raw_shape=m['raw_shape'],train_ids_sha256=m['train_ids_sha256'],val_ids_sha256=m['val_ids_sha256'],
    normalizer_sha256=m['normalizer_sha256'],normalizer_source=m['normalizer_source'],normalizer_values_published=False,
    split_algorithm=m['split_algorithm'],trial_id_definition=m['trial_id_definition'],
    native_GDF_event_mapping_independently_verified=False,source_raw_GDF_pipeline_benchmarked=False))

audits=[];first=None;source_opens=0
for p in sorted((R/'logs').glob('ACCESS_*.jsonl')):
    rows=[json.loads(s) for s in p.read_text(encoding='utf8').splitlines()]
    denied=[v for v in rows if v['event']=='DENIED'];src=[v for v in rows if v['source_data']]
    assert not denied
    assert all(Path(v['path']).name in [f'S{s}.npz' for s in range(2,10)] for v in src)
    assert all(not Path(v['path']).name.lower().startswith(('s1.npz','a01t.','a01e.')) for v in rows)
    if src:
        minimum=min(v['utc'] for v in src);first=minimum if first is None else min(first,minimum)
    source_opens+=len(src)
    audits.append(dict(file=p.relative_to(R).as_posix(),sha256=sha(p),events=len(rows),source_file_opens=len(src),denied=0))
assert first>=reg['registered_utc']
write('ACCESS_AUDIT.json',dict(registration_utc=reg['registered_utc'],first_source_open_utc=first,registration_preceded_source_open=True,
    logs=audits,total_source_file_open_events=source_opens,held_data_opens=0,E_OpenBMI_opens=0,denied=0,
    coverage='Python open hooks with exact8-file allowlist;not OS ACL or complete DLL system-call audit',
    dataset_files_read_only=True,stopping_rule='any forbidden open logs STOP then exits90;controller stops all remaining jobs'))

models=['EEGNet','EEGNeX','ATCNet'];budgets={};results={};cap={'EEGNet':500,'EEGNeX':200,'ATCNet':1000}
for model in models:
    path=R/'output'/model/'RESULT.json';v=json.loads(path.read_bytes());results[model]=v
    assert v['epochs']==2 and v['held']==1 and v['seed']==42
    assert v['status']=='source_probe_complete_weights_discarded' and not v['weights_saved'] and not v['weights_reused']
    assert v['source_train_ids_sha256']==m['train_ids_sha256'] and v['source_val_ids_sha256']==m['val_ids_sha256']
    assert v['normalizer_sha256']==m['normalizer_sha256']
    assert v['optimizer_updates']==2*v['train_steps_per_epoch']
    assert not v['held_scores_exported'] and not v['source_scores_exported']
    copy(path,f'probe_results/{model}.json')
    e=v['epoch_timings'];steady=e[1]['wall_seconds']
    fixed=v['process_wall_seconds']-sum(x['wall_seconds'] for x in e)+max(0,e[0]['wall_seconds']-steady)
    assert fixed>=0
    estimate=[27*(fixed+factor*cap[model]*steady)/3600 for factor in [1.5,4]]
    budgets[model]=dict(fits=27,max_epochs=cap[model],measured_steady_epoch_seconds=steady,
        measured_fixed_overhead_seconds=fixed,GPU_hours=estimate,peak_allocator_bytes=v['peak_allocator_bytes'])
training=[sum(budgets[k]['GPU_hours'][i] for k in models) for i in [0,1]]
complete=json.loads((R/'COMPLETE.json').read_bytes());spent=complete['conservative_single_GPU_charge_hours']
total=[training[0]+1+.25+spent,training[1]+6+2+spent]
write('BUDGET_ESTIMATE.json',dict(hardware='local RTX4060 Laptop8GB only',cap_GPU_hours=80,no_paid_resources=True,
    probe_GPU_hours_conservative_wall=spent,budget_remaining_after_probe=80-spent,models=budgets,training_GPU_hours=training,
    baseline_forward_unmeasured=[1,6],PRS_forward_unmeasured=[.25,2],stage1_plus_probe_GPU_hours=total,
    CPU_bias_unmeasured_hours=[1,8],formula='27*(F+[1.5,4]*max_epochs*measured_epoch2_wall)/3600',
    planning_multipliers_unchanged_from_R2=[1.5,4],ETA_or_guarantee=False,long_term_thermal_stability_proven=False,
    cap_includes_failed_attempts_and_reruns=True,no_formal_jobs_started=True))

hardware=[json.loads(s) for s in (R/'logs/HARDWARE.jsonl').read_text(encoding='utf8').splitlines()]
temps=[float(v['gpu']['temperature.gpu']) for v in hardware if 'gpu' in v]
thermal=[v for v in hardware if v.get('thermal_slowdown_flag')]
write('HARDWARE_TRACE.json',dict(samples=hardware,log_sha256=sha(R/'logs/HARDWARE.jsonl'),
    summary=dict(samples=len(hardware),all_AC_connected=all(v['ACLineStatus']==1 for v in hardware),
      observed_sampler_gaps_over20s=sum(v['suspend_gap_detected'] for v in hardware),max_GPU_core_temperature_C=max(temps),
      thermal_flag_samples=len(thermal),thermal_flag_mask_values=sorted(set(v['gpu']['clocks_throttle_reasons.active'] for v in thermal)),
      power_cap_samples=sum(v.get('power_cap_flag',False) for v in hardware)),
    mask_reference='https://docs.nvidia.com/deploy/archive/R515/nvml-api/group__nvmlClocksThrottleReasons.html',
    interpretation='0x20 software-thermal and0x4 power-cap occurred;do not infer no throttling from low core temperature;memory/CPU temperatures unmeasured',
    sleep_policy=dict(AC_standby_seconds=0,AC_hibernate_seconds=0,DC_standby_seconds=1800,DC_hibernate_seconds=1800,
      changed_by_agent=False,hibernation_policy_query='after probe;no policy changes issued'),
    sleep_query_log_sha256=sha(R/'logs/sleep_policy.txt'),hibernate_query_log_sha256=sha(R/'logs/hibernate_policy.txt')))

for name in ['access_guard.py','source_pipeline.py','baseline_factory.py','probe_worker.py','run_probes.py','dashboard.pyw','build_r3.py']:
    copy(R/name,name)
copy(R/'ENVIRONMENT_RECHECK.json','ENVIRONMENT_RECHECK.json')
copy(R2/'public/FROZEN_CONFIGS.json','FROZEN_CONFIGS.json')
copy(R2/'public/PRS_SOURCE_REPLAY_CONTRACT.json','PRS_SOURCE_REPLAY_CONTRACT.json')
copy(R/'METADATA_COMPLETE.json','METADATA_COMPLETE.json')
verify=(R2/'public/verify_anonymous.py').read_text(encoding='utf8').replace('prs_matched_baselines_r2_20261121','prs_matched_baselines_r3_20261121')
(P/'verify_anonymous.py').write_bytes(verify.encode('utf8'));(P/'.gitattributes').write_bytes(b'* -text\n')

r2manifest=json.loads((R2/'public/SHA256SUMS.json').read_bytes())
assert all(sha(R2/'public'/name)==s['sha256'] for name,s in r2manifest['files'].items())
write('PARENT_AND_ENGINEERING_RECORD.json',dict(parent_commit='a5446a52e99b3c4b7411f9836fdc4127b19140a6',parent_files_unchanged=True,
    frozen_R2_worker_sha256=sha(R2/'synthetic_smoke.py'),derived_factory_sha256=sha(R/'baseline_factory.py'),
    derivation='R2 run prefix up to model construction;fixed probe seed42 substitutes synthetic seed20261121;no model hyperparameter changed',
    metadata_initial_failure='script assumed cache storagefloat32;actualfloat64;fixed existing R2 float32 model-port conversion before any updates',
    metadata_failure_log_sha256=sha(R/'logs/metadata_attempt1_storage_dtype.stderr.txt'),
    environment_assertion='pre-import60 vs R2 post-TF77 metadata;17 setuptools vendored entries;post-TF context matches exactly;no dependency changes',
    probes_rerun=False,completed_probe_fits=3,probe_epochs_total=6,total_optimizer_updates=sum(v['optimizer_updates'] for v in results.values()),
    formal_training_fits=0,held_scores=0,real_source_T_owners=list(range(2,10)),E_OpenBMI_reads=0,
    probes_weights_saved=False,probe_weights_reused=False,PRS_source_replay_run=False,
    PPU_jobs_or_uploads=0,no_paid_resources=True,temporary_dashboard_refresh_stopped=True,
    actual_executed_code_sha256={n:sha(R/n) for n in ['access_guard.py','source_pipeline.py','baseline_factory.py','probe_worker.py','run_probes.py']},
    log_index=[dict(file=p.relative_to(R).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted((R/'logs').glob('*')) if p.is_file()]))

write('FIT_RESTART_POLICY.json',dict(unit='one model×outer_fold×training_seed',completed_marker='TRAINING_COMPLETED',
    completed_fits='retain immutable successful checkpoint/normalizer/source-selection metadata;never retrain because another fit or inference fails',
    interrupted_fits='keep failed attempt for audit;new attempt starts whole fit with same seed and fresh model/optimizer/RNG;no epoch resume',
    probe_fits='retain logs only;weights discarded;not counted as completed formal fits',
    inference='separate status/job;failure does not invalidate completed training',
    attempts_count_toward80h=True,automatic_infinite_retry=False,
    budget_exhaustion='stop/suspend scheduling;current interrupted fit not scored;completed fits retained;do not reduce folds,seeds,trials or epochs silently',
    machine_records=dict(before_after=['AC,battery,active power scheme,AC/DC standby andhibernate timeout,GPU,driver'],
       interval_seconds_formal=5,AC_loss='interrupt at next safe batch boundary',
       thermal_stop_proposed='thermal flag continuous>=30s OR core>=85C continuous>=30s;stop fit,no automatic retry',
       idle_bit_not_thermal=True,no_permanent_global_power_changes=True,
       temporary_paths='formal TEMP/TMP/CUDA_CACHE_PATH on non-system drive',
       suspend='UTC+monotonic gaps and available OS resume events;do not infer full OS audit from sampling alone')))

# Public files contain only metadata, code and performance. No raw data,labels,normalizer values or weights.
for p in P.rglob('*'):
    if p.is_file() and p.name!='SHA256SUMS.json':p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
write('PLAN_DRAFT.json',dict(title='同口径基线对比',revision='R3',status='FROZEN_DRAFT_AWAITING_USER_CONFIRMATION',
    normative_document=dict(file='PLAN_DRAFT.md',sha256=sha(P/'PLAN_DRAFT.md')),
    parent=dict(commit='a5446a52e99b3c4b7411f9836fdc4127b19140a6',JSON_SHA256='1eb4485b8691f3312fd0103bced108597feec06bdc7a89518233604f7bf3c941'),
    authorization=dict(phase05_source_only=True,phase05_complete=True,formal_training=False,held_data_reads=False,E_OpenBMI_reads=False,
      source_probe_held=1,source_subjects=list(range(2,10)),probe_seed=42,max_probe_epochs=2),
    decisions=dict(cap_GPU_hours=80,card='local RTX4060 Laptop only',no_paid_resources=True,PPU=False,
      Conformer='excluded',stage2='after stage1 review',literature_arm='not now'),
    probe_result_files=[f'probe_results/{x}.json' for x in models],source_manifest='SOURCE_MANIFEST_PUBLIC.json',
    access_audit='ACCESS_AUDIT.json',machine_trace='HARDWARE_TRACE.json',restart='FIT_RESTART_POLICY.json',
    stage1_proposed=dict(baselines=models,seeds=[42,43,44],folds=9,fits=81,PRS='historical single frozen five-expert reference;development-selected',
      planned_total_GPU_hours=total,remaining_budget_after_probe=80-spent),
    actual=dict(probe_fits=3,probe_epochs=6,optimizer_updates=298,formal_fits=0,weights_saved=False,held_reads=0,E_OpenBMI_reads=0),
    protocol='R2 unchanged;sourceT75/25;raw22×1000;current-inclusive post-fusion causal rule;subject-paired bootstrap',
    PRS_replay='R2 registered2e-5 contract;still not run',
    claims='pipeline timing/metadata only;no accuracy/gain/generalization/long-run thermal stability claim',
    next='user R3 review before any formal training;no automatic expansion',ready_for_formal_execution=False,
    hash_object='exact bytes in the Git commit'))
files={}
for p in sorted(P.rglob('*')):
    if p.is_file() and p.name!='SHA256SUMS.json':
        b=p.read_bytes();assert b'\r' not in b and not b.startswith(b'\xef\xbb\xbf')
        files[p.relative_to(P).as_posix()]=dict(sha256=sha(p),bytes=len(b))
write('SHA256SUMS.json',dict(hash_object='exact bytes in the Git commit',encoding='UTF8 noBOM LF',
    self_hash='excluded;full commit+anonymous verification receipt bind manifest itself',files=files))
print(json.dumps(dict(PLAN_DRAFT_sha256=sha(P/'PLAN_DRAFT.json'),markdown_sha256=sha(P/'PLAN_DRAFT.md'),
    manifest_items=len(files),stage1_plus_probe_GPU_hours=total,probe_charge_GPU_hours=spent,
    source_opens=source_opens,thermal_flag_samples=len(thermal),public_bytes=sum(p.stat().st_size for p in P.rglob('*') if p.is_file()))))
