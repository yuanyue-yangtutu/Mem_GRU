"""Metadata-only build. Does not open EEG, labels or historical predictions."""
from common import *
import shutil,ast,difflib
P=ROOT/'public'
assert not (P/'R3_1.json').exists()
for d in ['logs','tmp','tmp/cuda','fits']: (ROOT/d).mkdir(parents=True,exist_ok=True)
# Reuse exact already-verified implementations; factory/model/preprocessing unchanged.
for name in ['source_pipeline.py','baseline_factory.py']:shutil.copyfile(R3/name,ROOT/name)
base=(R3/'public/PLAN_DRAFT.md').read_text(encoding='utf8')
a='阶段1拟仍为EEGNet/EEGNeX/ATCNet各9折×3seed（42/43/44），合计81个正式fit；'
b=a+'调度固定为seed-major：先完成seed42的全部模型×折，再seed43，再seed44；每个seed内按EEGNet、EEGNeX、ATCNet，每模型按留出S1到S9；'
c='- 建议正式门槛（待R3确认）：thermal标志持续≥30秒或核心温度≥85°C持续≥30秒，停止当前fit并记录，不自动重跑；单纯GPU_idle不触发，power-cap单列。必须保留全部原始时序，不能删除低频区间来提高吞吐估计。持续限制需先排查供电/散热，再用新的整fit attempt；不能靠降batch、lr等改科学配置。'
d='- R3.1正式门槛：硬件/热停止仅在核心温度≥85°C持续≥30秒、交流断开、睡眠/休眠或驱动报错时触发；GPU限频标志（包括thermal、power-cap和idle）只记录，不触发停止。本条同时约束第6节“持续限频异常”的解释；数据拒绝、哈希错误、训练故障与80小时预算停止规则保持不变。停止当前fit并记录，不自动重跑；保留全部原始时序，不删除低频区间，不靠降batch、lr等改科学配置。'
assert base.count(a)==base.count(c)==1
new=base.replace(a,b).replace(c,d)
(P/'PLAN_R3_1.md').write_bytes(new.encode('utf8'))
proof=dict(parent_commit='1244dfb59ecd6034767ea536233cf6b6cae8c97d',parent_MD_SHA256=sha(R3/'public/PLAN_DRAFT.md'),parent_JSON_SHA256=sha(R3/'public/PLAN_DRAFT.json'),
 changes=[dict(name='seed-major schedule',old=a,new=b),dict(name='hardware thermal-stop trigger; throttle flags record only',old=c,new=d)],
 reconstructed_equals_R31=True,reverse_equals_parent=new.replace(b,a).replace(d,c)==base,
 unchanged_model_factory=sha(ROOT/'baseline_factory.py')==sha(R3/'baseline_factory.py'),unchanged_source_pipeline=sha(ROOT/'source_pipeline.py')==sha(R3/'source_pipeline.py'),
 note='exactly two normative textual substitutions; historical draft/status wording retained as history. Separate user authorization activates source-only stage1, not any target inference.')
assert proof['reverse_equals_parent']
put(P/'DIFF_PROOF.json',proof)
shutil.copyfile(R3/'public/FROZEN_CONFIGS.json',P/'FROZEN_CONFIGS.json')
assert sha(P/'FROZEN_CONFIGS.json')==sha(R3/'public/FROZEN_CONFIGS.json')==sha(R2/'public/FROZEN_CONFIGS.json')
put(P/'R3_1.json',dict(revision='R3.1',type='two-clause amendment only; not a model change',parent_commit=proof['parent_commit'],parent_normative_sha256=proof['parent_MD_SHA256'],normative_file='PLAN_R3_1.md',normative_sha256=sha(P/'PLAN_R3_1.md'),semantic_changes=[x['name'] for x in proof['changes']],frozen_configs_sha256=sha(P/'FROZEN_CONFIGS.json')))
queue=[dict(fit_id=f'{m}_H{h:02d}_seed{s}',model=m,held=h,seed=s) for s in [42,43,44] for m in ['EEGNet','EEGNeX','ATCNet'] for h in range(1,10)]
assert len(queue)==81 and len({x['fit_id'] for x in queue})==81
put(P/'QUEUE.json',queue)
put(P/'USER_AUTHORIZATION.json',dict(date='2026-11-22 Asia/Shanghai',scope='stage1 source-only training',condition='publish R3.1 and anonymously verify exact bytes and exactly two normative differences before any source load',models=['EEGNet','EEGNeX','ATCNet'],seeds=[42,43,44],folds=9,formal_training=True,target_inference=False,target_scoring=False,held_reads=False,E_OpenBMI_reads=False,PPU=False,budget_GPU_hours=80,prior_probe_charge_hours=.0132828877777744,fit_restart='whole fit only; complete fits retained; interrupted attempts retained not reused',PRS_fixture_inference='not authorized or required for baseline-source training; old gate remains unrun',stop_after_training=True))
put(P/'ENGINEERING_CONTRACT.json',dict(source_access='exact current-fit eight source T paths; no held loader; Python audit not OS/DLL sandbox',
  split='same fixed PCG64 split_seed20261221, ascending current source owners, each class54/18, all models/seeds same fold split',normalization='unchanged R3 scalar source-train-only mean/std; no validation fit',
  metadata_note='reused pipeline contains historical owner2..9 split_algorithm prose; current registration/source_owners lists are authoritative for other held folds; algorithm unchanged',
  max_budget='process-start-to-exit single-card wall, all success/failure attempts + prior source probe, hard cap80; reserve max next-fit budget before launch',
  sleep_detection='power policy snapshot + 5s wall/monotonic sampling; >20s monitoring gap conservatively interrupts as possible sleep/hibernate; not claimed OS-complete event audit',
  telemetry='5s AC/battery/core-temp/clocks/power/utilization/throttle mask; mask is record-only',
  model_checkpoint='earliest strict best source val_loss for EEGNet, source val_accuracy others; scheduler/ES same frozen config; completion marker after file hashes',
  output='local source logs, best weights, model-config, source normalizer, train/val manifest, per-fit completion hashes; no target predictions',
  dashboard='detached Tk viewer; closing never stops controller; batch progress throttled2s, overall model median ETA once measured',
  storage='new TEMP/TMP/CUDA cache on E under run directory; original research assets untouched'))
# Runtime files from existing lock; hash only, never import model here.
lock=read(R2/'public/ENVIRONMENT_LOCK.json')
files={str(ENV/k):v for k,v in lock['runtime_files_sha256'].items()}
for f in [R2/'public/FROZEN_CONFIGS.json',R3/'public/PLAN_DRAFT.md',R3/'public/PLAN_DRAFT.json',OFFICIAL/'arl-eegmodels/EEGModels.py',OFFICIAL/'EEGNeX/BenchmarkModels.py',R2/'evidence/atcnet_2022/models.py',R2/'evidence/atcnet_2022/attention_models.py']:
    files[str(f)]=sha(f)
for f in ROOT.glob('*.py'):
    ast.parse(f.read_text(encoding='utf8'));files[str(f)]=sha(f)
    shutil.copyfile(f,P/f.name)
for f in ROOT.glob('*.pyw'):
    ast.parse(f.read_text(encoding='utf8'));files[str(f)]=sha(f);shutil.copyfile(f,P/f.name)
put(P/'EXECUTION_BINDINGS.json',dict(files=files,hash_object='exact local execution bytes; public copies separately Git-byte hashed'))
verify_binding()
(P/'.gitattributes').write_bytes(b'* -text\n')
for f in P.iterdir():
    if f.suffix in ['.py','.pyw','.json','.md']:
        bts=f.read_bytes();f.write_bytes(bts.replace(b'\r\n',b'\n'))
# Original pipeline/factory public copy may differ CRLF; local bindings remain exact original bytes.
put(P/'SHA256SUMS.json',dict(hash_object='exact bytes in the Git commit',files={f.name:dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(P.iterdir()) if f.name!='SHA256SUMS.json'}))
print(json.dumps(dict(files=len(list(P.iterdir())),R31_SHA256=sha(P/'R3_1.json'),MD_SHA256=sha(P/'PLAN_R3_1.md'),two_changes_only=True,runtime_bindings_verified=True)))
