"""Documentation-only packaging. No ML imports, array loading or experiment calls."""
from pathlib import Path
import hashlib, json, subprocess, datetime

R = Path(__file__).resolve().parent
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name, value):
    (R/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def git(folder,*args):
    return subprocess.check_output(['git','-C',str(folder),*args],text=True,encoding='utf8').strip()

repos=[('EEGNet','vlawhern/arl-eegmodels','arl-eegmodels'),
       ('EEGNeX','chenxiachan/EEGNeX','EEGNeX'),
       ('ATCNet','Altaheri/EEG-ATCNet','EEG-ATCNet'),
       ('EEG-Conformer','eeyhsong/EEG-Conformer','EEG-Conformer'),
       ('DSGNet','xicheng105/DSGNet','DSGNet')]
records=[]; files=[]
for model,repo,directory in repos:
    d=R/'sources'/directory
    commit=git(d,'rev-parse','HEAD')
    assert len(commit)==40 and not git(d,'status','--porcelain')
    tracked=git(d,'ls-tree','-r','--name-only','HEAD').splitlines()
    chosen=[p for p in tracked if p.endswith(('.py','.ipynb','.md','.txt','.yml','.yaml','.toml')) or 'license' in p.lower()]
    records.append(dict(model=model,repository=repo,commit=commit,
        commit_time=git(d,'show','-s','--format=%cI','HEAD'),
        commit_url=f'https://github.com/{repo}/commit/{commit}',
        tracked_file_count=len(tracked),hashed_text_files=len(chosen),
        code_executed=False,source_license_verification='DSGNet: no license file in tracked tree; others preserve upstream notices'))
    for p in chosen:
        files.append(dict(model=model,path=p,sha256=sha(d/p),bytes=(d/p).stat().st_size,
            url=f'https://github.com/{repo}/blob/{commit}/{p}'))
write('SOURCE_REPOS.json',records)
write('SOURCE_FILES_SHA256.json',files)

local_sources={
 'five_expert_loader':'D:/BCI_builds/PriResCal_STYLE9_Best_65p2778_20261114/code/prirescal_frozen_loader.py',
 'input_contract':'D:/BCI_builds/IV2a_E_FrozenFollowup_Revision1_20261120/GEOMETRY_INPUT_CONTRACT.json',
 'bias_solver':'D:/BCI_builds/OpenBMI_AB_Execution_20261120/stage/code/bias_rule.py',
 'bias_caller_inclusive':'D:/BCI_builds/OpenBMI_AB_Execution_20261120/stage/code/worker.py',
 'original_bias_protocol':'D:/BCI_builds/PRS_UnlabelledBias_20261120/PLAN.json',
}
write('LOCAL_SOURCE_REFERENCES.json',[
 dict(role=k,logical_source='/'.join(Path(v).parts[-3:]),sha256=sha(v),bytes=Path(v).stat().st_size,
      source_only_or_protocol_read=True,executed=False) for k,v in local_sources.items()])
write('RETRIEVAL_NOTES.json',dict(
 date='2026-11-21 Asia/Shanghai',
 github_metadata='Official GitHub connector verified all five repos; shallow git checkout used to obtain immutable commits and file hashes.',
 failures=[
  'Unauthenticated GitHub REST API rate-limited (HTTP403); initial empty SOURCE_REPOS.json was unusable and regenerated from verified git commits. No results derived from failed API.',
  'arXiv EEGNet HTML v5 404; official PDF v4 retrieved with web tool.',
  'Brunel DSGNet full-text landing fetch timed out via web and SSL failed via PowerShell; indexed institution metadata found, full paper not obtained. No TLS bypass.',
  'First narrow rg command accidentally passed PowerShell -ErrorAction to rg; it failed; no experimental result affected.'
 ],
 execution=dict(training=0,neural_inference=0,smoke_tests=0,data_array_value_reads=0,
                E_reads=0,OpenBMI_target_reads=0,label_reads=0),
 scope_note='No background task, dependency installation, old PLAN edits or output hash edits. Public files contain documentation and source hashes only.'))

blockers=[
 'Common source validation split vs historical PRS recipe needs binding; no target-side selection permitted.',
 'EEGNet MI batch/default kernel vs 250Hz matching adaptation not fully pinned.',
 'EEGNeX accuracy-vs-loss monitor discrepancy and version-dependent defaults.',
 'ATCNet original paper 1000/300 training configuration binding vs revised 500-epoch code.',
 'DSGNet official preview lacks full training, class-alignment loss and weights, dependency and license specification; paper full text not retrieved.',
 'PRS full five-member training recipe and three independent system repeats provenance not yet complete.',
 'Source input units, trial IDs, scalar normalization definition and fixture hashes/tolerances need complete frozen manifest.',
 'Exact literature pooled-source T+E protocol binding and all E access require separate future authorization.',
 'All implementation adapters and isolated environments must be source-only validated and hashed before execution.'
]
write('PLAN_DRAFT.json',dict(
 title='同口径基线对比',date='2026-11-21',timezone='Asia/Shanghai',
 status='DRAFT_NOT_EXECUTABLE_AWAITING_REVIEW',
 authorization=dict(documentation_and_public_submission=True,training=False,inference=False,
  smoke_execution=False,scoring=False,E_access=False,OpenBMI_target_access=False,old_PLAN_modification=False),
 normative_document=dict(file='PLAN_DRAFT.md',sha256=sha(R/'PLAN_DRAFT.md')),
 main_model='five equal-weight neural experts + post-fusion current-inclusive causal bias',
 excluded=['historical 72.9167% candidate','full PRS multi-branch system'],
 baselines=[r['model'] for r in records],training_seeds=[42,43,44],
 PRS_system_repetitions=3,PRS_experts_per_system=5,
 protocols=[
  dict(id='P_T',source='other8 T only',test='held T288',role='primary',
       source_validation='proposed shared per-person/class75/25; compatibility blocker V1'),
  dict(id='P_T_EVAL_TE',source='same frozen P_T weights',test='held T+E576 with independent session correction states',role='descriptive literature-evaluation-domain contrast',extra_training_fits=0),
  dict(id='P_TE_POOL',source='other8 T+E',test='held T+E576',role='conditional separate literature-protocol alternative; not automatically selected')],
 input=dict(channels=22,sfreq=250,samples=1000,window='cue+[0,4)s',external_filter='none beyond native raw acquisition; v81 preprocessing forbidden',target_EA=False),
 causal=dict(first_unchanged_trials=20,history='original probabilities0..t inclusive',
  log_clip=1e-9,lambda_rule='.1+20/n',uniform_target=True,L2='lambda*sum(b*b)/C',
  solver='pinned original L-BFGS-B maxiter150 gtol1e-8',expert_bias=False,
  prior_assumption='depends on class-prior balance; not pure zero calibration'),
 stats=dict(unit='person; average three seed metrics within person',bootstrap_repeats=50000,
  bootstrap_seed=20261121,CI='paired person-block percentile95%; pointwise, not simultaneous',
  inconclusive='CI includes0: 无法区分',counts='increase/decrease/tie per person',
  all_family_superiority_claim_authorized=False),
 cost=dict(measured=False,ETA=None,primary_baseline_fits=135,primary_PRS_component_fits=135,
  primary_total_component_fits=270,primary_gpu_hours_scenario=[299.7,2214],
  combined_with_conditional_source_TE_pool_hours=[899.1,6642],
  missing_defaults_mean_cost_unreliable=True),
 secondary_dataset_options_only=['IV2b native training','IV2b frozen-transfer interface diagnostic',
  'OpenBMI native training','OpenBMI frozen IV2a transfer'],
 blockers=blockers,ready_for_execution=False))

publication=['PLAN_DRAFT.md','PLAN_DRAFT.json','SOURCE_REPOS.json','SOURCE_FILES_SHA256.json',
 'LOCAL_SOURCE_REFERENCES.json','RETRIEVAL_NOTES.json','build_draft_package.py']
write('SHA256SUMS.json',{p:sha(R/p) for p in publication})
print(json.dumps(dict(files=publication+['SHA256SUMS.json'],PLAN_DRAFT_SHA256=sha(R/'PLAN_DRAFT.json'),
 markdown_sha256=sha(R/'PLAN_DRAFT.md'),official_source_files=len(files),blockers=len(blockers)),ensure_ascii=False))
