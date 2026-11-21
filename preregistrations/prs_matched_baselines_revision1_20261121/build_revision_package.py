"""Only build documentation and source-byte manifests. Never run ML or read data."""
from pathlib import Path
import hashlib, json, subprocess

R = Path(__file__).resolve().parent
OLD = R.parent/'PRS_MatchedBaselines_Draft_20261121'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def write(name, value):
    # write_bytes prevents Windows text-mode CRLF translation.
    (R/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8'))

def git_blob(folder, commit, path):
    return subprocess.check_output(['git','-C',str(folder),'show',f'{commit}:{path}'])

def main():
    repos=json.loads((OLD/'SOURCE_REPOS.json').read_text(encoding='utf8'))
    source_records=[]
    for repo in repos:
        folder=OLD/'sources'/repo['repository'].split('/')[1]
        commit=repo['commit']
        paths=subprocess.check_output(['git','-C',str(folder),'ls-tree','-r','--name-only',commit],text=True,encoding='utf8').splitlines()
        chosen=[p for p in paths if p.endswith(('.py','.ipynb','.md','.txt','.yml','.yaml','.toml')) or 'license' in p.lower()]
        repo['source_hash_object']='upstream Git-commit blob bytes, not local checkout bytes'
        repo['source_license_verification']='no license file in preview; unresolved' if repo['model']=='DSGNet' else 'upstream license file preserved and hashed; no source redistribution in this package'
        for path in chosen:
            raw=git_blob(folder,commit,path)
            source_records.append(dict(model=repo['model'],repository=repo['repository'],commit=commit,
                path=path,sha256=digest(raw),bytes=len(raw),hash_object='upstream Git-commit blob bytes',
                url=f'https://github.com/{repo["repository"]}/blob/{commit}/{path}'))
    write('SOURCE_REPOS.json',repos)
    write('SOURCE_FILES_SHA256.json',dict(hash_object='upstream Git-commit blob bytes',files=source_records))
    local=json.loads((OLD/'LOCAL_SOURCE_REFERENCES.json').read_text(encoding='utf8'))
    write('LOCAL_SOURCE_REFERENCES.json',dict(hash_object='unchanged local archived source/protocol file bytes; not published Git blobs',
        contents_not_reloaded_in_this_revision=True,files=local))

    paper=OLD/'DSGNet_FullText.pdf'
    write('PAPER_REFERENCE.json',dict(
        title='Subject-Independent Deep Learning Framework for Motor Imagery Electroencephalogram Decoding in Neurorehabilitation',
        DOI='10.1109/JBHI.2026.3689121',
        url='https://bura.brunel.ac.uk/bitstream/2438/33344/3/FullText.pdf',
        sha256=digest(paper.read_bytes()),bytes=paper.stat().st_size,pages=13,
        hash_object='downloaded publisher/author PDF bytes, not a file published in this Git package',
        visual_pages_reviewed=[3,4,7,11,12],
        extraction='bundled pypdf; visual render through bundled pdfplumber; no installations',
        source_code_commit='6ab313824b20471229da727a8ef1383ecc4cfbd6'))

    facts=[
        dict(field='optimizer',value='Adam',source='论文原文',page=7,missing='betas/epsilon/version binding'),
        dict(field='learning_rate',value=1e-4,source='论文原文',page=7),
        dict(field='batch',value=128,source='论文原文',page=7,qualification='standard classification; same paragraph says32 per subject for subject-wise DA/DG; sampler unclear'),
        dict(field='epochs',value=500,source='论文原文',page=7),
        dict(field='lambda2',value=.01,source='论文原文',pages=[7,12]),
        dict(field='lambda1',value=1.1,source='论文原文',pages=[11,12],selection_history='IV2a LOSO sensitivity analysis; not independently nested parameter selection'),
        dict(field='windows_stride_depth_kernel',value=[6,1,4,4],source='论文原文＋代码预览',pages=[11,12],selection_history='IV2a sensitivity; temp_model.py DSGNet.__init__'),
        dict(field='initial_filters_kernels',value={'temporal':[8,64],'spectral':[16,96]},source='论文原文＋代码预览',page=4),
        dict(field='depthwise_separable',value={'depth_multiplier':2,'spatial':'E×1','temporal_separable':16,'spectral_separable':24},source='论文原文＋代码预览',page=4),
        dict(field='pooling',value={'temporal':'average','spectral':'max'},source='论文原文＋代码预览',pages=[4,11]),
        dict(field='pool_widths',value={'temporal':[4,8],'spectral':[6,12]},source='代码预览推导',location='_LC_Block kernel_length//16 and//8',paper_value_missing=True),
        dict(field='dropout',value={'paper':None,'preview':.25},source='代码预览；论文训练配置缺失',blocking=True),
        dict(field='SE_reduction',value={'paper_ratio':None,'preview_hidden_dimension':2},source='代码预览；论文训练配置缺失',qualification='seize=2 is hidden dimension, not reduction ratio2',blocking=True),
        dict(field='checkpoint_selection',value=None,source='缺失',blocking=True),
        dict(field='class_center_batch_subject_composition',value=None,source='缺失',qualification='paper defines centers, not exact batch sampler/memory/missing-class rules',blocking=True),
        dict(field='IV2a_protocol',value='other8 T train / other8 E validate / held T+E test',source='论文原文',page=3),
        dict(field='IV2b_protocol',value='other8 sessions1–3 T train /4–5 E validate /held all5 sessions test',source='论文原文＋官方数据集说明',page=3,official='https://www.bbci.de/competition/iv/desc_2b.pdf')]
    write('DEFAULTS_AND_BLOCKERS.json',dict(DSGNet=dict(status='literature_reference_only_excluded_from_matched_training',facts=facts),
        EEGNet=dict(confirmed='F1=8,D=2,F2=16,cross-subject dropout.25,Adam,CE,500epochs,source-val-loss-best',blocking=['MI batch','kernel32 at common250Hz vs original128Hz adaptation']),
        EEGNeX=dict(confirmed='Adam.001,batch128,notebook200epochs,ES20,LR*.5/patience5',blocking=['paper accuracy vs notebook loss monitoring','best checkpoint restoration and framework defaults']),
        ATCNet=dict(confirmed='5windows,MHA,F1=16,D2,k64,pool7,dropout.3,TCN2/k4/32/.3/ELU,Adam.001,batch64',blocking=['original-paper1000/300 vs revised500-epoch recipe binding','source-only validation adaptation']),
        Conformer=dict(status='optional',confirmed='emb40,depth6,batch72,epochs2000,Adam.0002/betas(.5,.999)',blocking=['source-only checkpoint/augmentation adaptation']),
        PRS_stage1=dict(status='historical_frozen_single_system',blocking=['source/checkpoint/input provenance and source-preflight gate remain required']),
        PRS_stage2=dict(status='optional_separate_confirmation',blocking=['complete five-component original training recipe and all loss/validation/version bindings'])))

    old_public=(R/'evidence/old_public_PLAN_DRAFT.json').read_bytes()
    old_local=(OLD/'PLAN_DRAFT.json').read_bytes()
    write('REVISION_NOTES.json',dict(
        supersedes_draft_commit='0d0aee60b91f597a1f72b6b65f1dac441f08e2ee',old_files_unchanged=True,
        hash_erratum=dict(old_public_sha256=digest(old_public),old_manifest_local_sha256=digest(old_local),
            public_CRLF=old_public.count(b'\r\n'),local_CRLF=old_local.count(b'\r\n'),
            differ_only_by_CRLF=old_local.replace(b'\r\n',b'\n')==old_public,
            previous_API_text_equality_claim_withdrawn=True),
        changes=['Hash exact Git-commit bytes; LF/noBOM; scoped .gitattributes; anonymous verifier',
            'DSGNet full paper facts added, missing implementation details retained; literature only',
            'Replace pooled T+E source training with sourceT training/sourceE validation/heldTE test',
            'IV2b literature uses all5 sessions, unlike retained T12 scope',
            'Stage1 three baseline models×3seeds plus historical single frozen PRS',
            'Stage2 optional separately confirmed three-system PRS retraining',
            'Explicit budget/card/stage2/literature-arm decision list'],
        execution=dict(training=0,smoke=0,inference=0,scoring=0,E_reads=0,OpenBMI_target_reads=0,label_reads=0),
        retrieval=dict(DSGNet_full_text='downloaded via TLS curl after web timeouts; no TLS bypass',
            PDF_skill_path='official bundled PDF skill; initial wrong alias path corrected',
            installations=0,subagents=0)))

    # Normalize only new publication files; keep historical byte evidence untouched.
    for name in ['PLAN_DRAFT.md','.gitattributes','build_revision_package.py','verify_anonymous.py']:
        p=R/name
        p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
    write('PLAN_DRAFT.json',dict(title='同口径基线对比',revision='R1',date='2026-11-21',timezone='Asia/Shanghai',
        status='DRAFT_NOT_EXECUTABLE_AWAITING_REVIEW',
        hash_object='exact bytes in the Git commit',normative_document=dict(file='PLAN_DRAFT.md',sha256=digest((R/'PLAN_DRAFT.md').read_bytes())),
        authorization=dict(document_revision_and_publication=True,training=False,smoke=False,inference=False,scoring=False,E_access=False,OpenBMI_target_access=False,old_PLAN_changes=False),
        stage1=dict(protocol='P_T',required_baselines=['EEGNet','EEGNeX','ATCNet'],optional=['EEG-Conformer'],excluded_matched=['DSGNet'],
            seeds=[42,43,44],training_fits=81,PRS='historical frozen SINGLE five-expert system across9 panels; no retraining; tuned on development cohort, not equivalent to new baselines',
            readout='person means of baseline three-seed metrics; PRS single-system metrics; raw/corrected; PRS-vs-baseline contrasts exploratory and selection-biased',
            GPU_hours=dict(training=[43.2,270],PRS_forward=[.25,2],baseline_forward=[1,6],total=[44.45,278],optional_Conformer_training=[108,648])),
        stage2=dict(optional=True,separate_confirmation=True,PRS_system_repetitions=3,components_per_system=5,folds=9,component_fits=135,
            GPU_hours=dict(training=[135,1080],forward=[.75,6],total=[135.75,1086]),
            readout='same source split/checkpoint boundaries; average three system metrics within person; not independent blind confirmation'),
        protocols=dict(P_T=dict(source_train='source8 T 75%',source_validation='source8 T25%',test='held T288',E_forbidden=True),
            P_LIT_TTRAIN_EVAL_TE_TEST=dict(optional=True,separate_confirmation_and_E_authorization=True,source_train='source8 T only',source_validation='source8 E only',test='held T+E576',
                replaces='P_TE_POOL, which incorrectly pooled sourceT+E for training',GPU_hours_three_baselines=[66.8,687],GPU_hours_PRS_three_repeats=[204,2712]),
            IV2b_literature=dict(train='source sessions1–3T',validation='source sessions4–5E',test='held all5',relation='different from retained sessions1/2T; no access authorization')),
        causal=dict(history='original probabilities0..t inclusive',first20_unchanged=True,log_clip=1e-9,lambda_rule='.1+20/n',L2='lambda*sum(b*b)/C',
            solver='original pinned L-BFGS-B maxiter150/gtol1e-8; framework defaults must bind',fusion_level='one post-fusion correction',
            class_prior='uniform, assumes balance; NOT pure zero calibration'),
        statistics=dict(unit='subject, not subject×seed',bootstrap=50000,seed=20261121,CI='paired-block percentile95% pointwise',
            crosses_zero='无法区分',lower_positive_mean_under1pp='方向一致、幅度小',historical_selection_bias_not_removed=True),
        user_decisions=dict(budget_cap_GPU_hours_or_money=None,GPU_model_VRAM_count_and_availability=None,stage2=None,literature_arm_and_E_scope=None,
            optional_Conformer='not included unless explicitly selected'),
        measured_budget=False,ETA=None,ready_for_execution=False))

    names=['.gitattributes','PLAN_DRAFT.md','PLAN_DRAFT.json','SOURCE_REPOS.json','SOURCE_FILES_SHA256.json',
        'LOCAL_SOURCE_REFERENCES.json','PAPER_REFERENCE.json','DEFAULTS_AND_BLOCKERS.json','REVISION_NOTES.json',
        'build_revision_package.py','verify_anonymous.py']
    specs={}
    for name in names:
        raw=(R/name).read_bytes()
        assert b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'),name
        specs[name]=dict(sha256=digest(raw),bytes=len(raw))
    write('SHA256SUMS.json',dict(hash_object='exact bytes in the Git commit',encoding='UTF-8 without BOM, LF; .gitattributes * -text scoped to this package',
        self_hash='excluded to avoid recursion; manifest SHA256 and full commit recorded in anonymous verification receipt',files=specs))
    print(json.dumps(dict(PLAN_DRAFT_sha256=specs['PLAN_DRAFT.json']['sha256'],markdown_sha256=specs['PLAN_DRAFT.md']['sha256'],
        files_in_manifest=len(specs),upstream_files=len(source_records),all_public_text_LF=True)))

if __name__ == '__main__':
    main()
