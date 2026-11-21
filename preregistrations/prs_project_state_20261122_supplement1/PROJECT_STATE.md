# PROJECT_STATE：冻结项目状态

文档整理，不是新PLAN或执行授权。旧文件原字节保留；公开提交号绑定原规范包，报告指纹与原规范文件角色区分。空提交号表示公开绑定缺口，不能自行补称已公开。

|组件|状态|说明|原公开提交|
|---|---|---|---|
|OpenBMI A/B|已执行并锁定|输出哈希锁定提交`80db932a5195954744249b6ca94208d9118d3884`；清单SHA-256 `78616980123354a96d0941176de8cc5131b0cf847c550709a01cbf2307899a2b`（公开核验后才本轮标签读取评分；原规范提交不变）。冻结IV2a五专家平均及偏置的外部迁移；A/B共享输出，不是独立重复。第1会话已评分曝光，第2会话历史标签曝光；不能声称OpenBMI原生完整PRS有效。|4882d1eb18580eb737e8ff783d823cdfcbd403ca|
|E跟进|已关闭|已曝光历史E上的探索性冻结跟进；一轮源侧定位后未过停止线，不可执行。草案确认不等于执行授权。|761fa735d3f66f187b662ca8ddd218fd3ef9929f|
|完整PRS在OpenBMI|不可执行|完整PRS次要臂源侧回放H1/H2/H4/H5超差；未替换，不以五专家平均替代其结果。|4882d1eb18580eb737e8ff783d823cdfcbd403ca|
|72.9167%|不可执行|历史探索性最高候选保留，不是稳定泛化成绩；当前完整端到端回放未通过，不可重执行。源训练LOSO但含目标prefix EA及两层past-only偏置，不能并列纯当前试次口径。|未找到公开绑定|
|同口径基线 R1|仅登记|仅草案登记；默认值与协议边界修订，无正式训练。|4f101eb62af515f76a2f81c832d84682ce7eb6e7|
|同口径基线 R2|已执行并锁定|阶段0已执行锁定：独立环境、合成输入前向/反向冒烟；不是实数据准确率验证。|a5446a52e99b3c4b7411f9836fdc4127b19140a6|
|同口径基线 R3|已执行并锁定|阶段0.5已执行锁定：固定一折源8人T的短探针，权重丢弃；未输出留出者成绩。|1244dfb59ecd6034767ea536233cf6b6cae8c97d|
|同口径基线 R3资源附录|仅登记|仅登记：本机+两个单卡PPU+双卡PPU；80小时按各卡累计，非训练授权。|befcdae91e7d614c91657f7c0dbec2e2744619ef|
|同口径基线阶段1/2|未运行|正式九折多种子比较未获执行授权；Conformer不纳入，阶段2后议，文献口径臂当前不做。|1244dfb59ecd6034767ea536233cf6b6cae8c97d|
|PPU|仅登记|只读资源快照已核对；两个单卡当时占用，另一节点可见4卡但只授权2卡；默认Python无TensorFlow。兼容性试验未运行、分流任务未启动；不是实时空闲保证。|befcdae91e7d614c91657f7c0dbec2e2744619ef|
|归档|已执行并锁定|求解器敏感性、论文表、数字溯源和45格明细已完成；仅归档，不解除实验阻断。|未找到公开绑定|

## OpenBMI A/B
- `OpenBMI_TwoPlans_Revision2_20261120/PLAN_A.json` — SHA-256 `f55a5849858727eb6fc1bca8827871317341532e58f707fbf0abeff266aa0848`（normative_or_evidence）
- `OpenBMI_TwoPlans_Revision2_20261120/PLAN_B.json` — SHA-256 `62ee03306b1b9693fcccecc5f56a94c8121fd0fdcdf3fede3233594eee5e59d2`（normative_or_evidence）
- `OpenBMI_TwoPlans_Revision2_20261120/ASSET_REFERENCES.json` — SHA-256 `8a35776e317f11afb12119b1105ccb7222bcfd4de2cb6accc351ab847351a0f2`（normative_or_evidence）
- `OpenBMI_AB_Execution_20261120/REPORT.md` — SHA-256 `2f05c3b60eb6126584e9f1f03076cc9323e6108c90815ca4257063d1de625cea`（normative_or_evidence）
- `OpenBMI_AB_Execution_20261120/REPORT_SUPPLEMENT.md` — SHA-256 `bdd0f001289a67be15571e0d85ac239d6410d2eb49c704306c08e3af9f738133`（normative_or_evidence）

## E跟进
- `IV2a_E_FrozenFollowup_Revision1_20261120/PLAN_DRAFT.json` — SHA-256 `3d5b7c18082484f03dee69c09efee7b81be0b7ff9775b905da8587f7632a9c16`（normative_or_evidence）
- `PRS_FrozenArchive_20261121/tables/09_preflight_45_cells.csv` — SHA-256 `a0858fff89ba1d2b41f901120b81aa1522108b6bf1eb1170330ef1f0d998a697`（normative_or_evidence）

## 完整PRS在OpenBMI
- `OpenBMI_TwoPlans_Revision2_20261120/PLAN_A.json` — SHA-256 `f55a5849858727eb6fc1bca8827871317341532e58f707fbf0abeff266aa0848`（normative_or_evidence）
- `OpenBMI_AB_Execution_20261120/REPORT_SUPPLEMENT.md` — SHA-256 `bdd0f001289a67be15571e0d85ac239d6410d2eb49c704306c08e3af9f738133`（normative_or_evidence）

## 72.9167%
- `PRS729167_FullChainAudit_20261120/REPORT.md` — SHA-256 `3fe62d99ea29085f5efb82c4ee19d5b6e2a677c002fe91f70cd4627e24b1dbae`（historical_evidence_not_new_execution_plan）
- `PRS_FrozenArchive_20261121/KNOWN_GAPS.md` — SHA-256 `b410dc6fc404a1b063fa92cfe5e35efb8b66be3f0837376c8fad42e6ec73c214`（historical_evidence_not_new_execution_plan）

## 同口径基线 R1
- `PRS_MatchedBaselines_Revision1_20261121/PLAN_DRAFT.md` — SHA-256 `d654faa52de3b1e38bd562cb51b267464dfef53cb19f6ef8eeb7c0f44ec3053c`（normative_or_evidence）
- `PRS_MatchedBaselines_Revision1_20261121/PLAN_DRAFT.json` — SHA-256 `05e1d0c093f64648a8afb4ab0b21d8fa8043c80e51e4870fa49c7c2ebaf02bf5`（normative_or_evidence）
- `PRS_MatchedBaselines_Revision1_20261121/SHA256SUMS.json` — SHA-256 `e7078eaf28e884197864ba63f4c78a2f8bf1adaa8d0b85309ccb31401b7b5c29`（normative_or_evidence）

## 同口径基线 R2
- `PRS_MatchedBaselines_R2_Stage0_20261121/public/PLAN_DRAFT.md` — SHA-256 `b73df2ee83aa52ed2872471532ad7ba17b3564b462db4a36dc2cce3803b7fc55`（normative_or_evidence）
- `PRS_MatchedBaselines_R2_Stage0_20261121/public/PLAN_DRAFT.json` — SHA-256 `1eb4485b8691f3312fd0103bced108597feec06bdc7a89518233604f7bf3c941`（normative_or_evidence）
- `PRS_MatchedBaselines_R2_Stage0_20261121/public/SHA256SUMS.json` — SHA-256 `1f42d8ffc7a7f167a01cee49b90b20866ee3ba7cb1963708379a932edc23b2f3`（normative_or_evidence）

## 同口径基线 R3
- `PRS_MatchedBaselines_R3_Stage05_20261121/public/PLAN_DRAFT.md` — SHA-256 `de06bb67a183bf93ae1427be935c990812172c4cfeef1ae672c71010fd94c0df`（normative_or_evidence）
- `PRS_MatchedBaselines_R3_Stage05_20261121/public/PLAN_DRAFT.json` — SHA-256 `b864e41f4bd5d51e8cbba36aa5c1fc3a138d57ceb9bdce9efdfef43339fad122`（normative_or_evidence）
- `PRS_MatchedBaselines_R3_Stage05_20261121/public/SHA256SUMS.json` — SHA-256 `566beff849db83179e57e1c16b37f95d53b641df8f919f0dbd910eca1b639bad`（normative_or_evidence）

## 同口径基线 R3资源附录
- `PRS_R3_PPU_ResourceAmendment_20261121/public/PLAN_DRAFT.md` — SHA-256 `0a223ce902739a635e8ba327171f05fc2d9d18324de0b62fbc4014c6234e37ad`（normative_or_evidence）
- `PRS_R3_PPU_ResourceAmendment_20261121/public/PLAN_DRAFT.json` — SHA-256 `43d82c515c29afedbc81e081cbc0b0a8f74a4dd88287453e34fc682f4944ba8e`（normative_or_evidence）
- `PRS_R3_PPU_ResourceAmendment_20261121/public/SHA256SUMS.json` — SHA-256 `31d5afb29764c25a824f799c9ae1fc39ae9c7929565bce49fdd94c983acf7c67`（normative_or_evidence）

## 同口径基线阶段1/2
- `PRS_MatchedBaselines_R3_Stage05_20261121/public/PLAN_DRAFT.json` — SHA-256 `b864e41f4bd5d51e8cbba36aa5c1fc3a138d57ceb9bdce9efdfef43339fad122`（normative_or_evidence）

## PPU
- `PRS_R3_PPU_ResourceAmendment_20261121/public/RESOURCE_INVENTORY.json` — SHA-256 `fe854546250ce3343afe5cd114c2132b19365d8fa4bdc39dda8459f76c45d093`（normative_or_evidence）
- `PRS_R3_PPU_ResourceAmendment_20261121/public/CHECKS_AND_GAPS.json` — SHA-256 `997fe4bf67e823cad659447baab6357b5143f410541244c748120fd249034a2c`（normative_or_evidence）

## 归档
- `PRS_FrozenArchive_20261121/ARCHIVE_SCOPE.json` — SHA-256 `247aaca1fabefea3f8caa9f20f2002074cb381a752ee8f869101524c6e818083`（archive_scope_and_evidence）
- `PRS_FrozenArchive_20261121/REPORT.md` — SHA-256 `004380570bd71d4976e0e9154f2d0eabec9d0d2a85ba47cfefb01025717612d1`（archive_scope_and_evidence）
- `PRS_FrozenArchive_20261121/DELIVERY_MANIFEST.json` — SHA-256 `0c324af019ca30d49933b1fffc8e1fbac13de40b5482d845b260ce844b0be49a`（archive_scope_and_evidence）

## OpenBMI A/B输出锁定证据补充

清单文件：`preregistrations/openbmi-split-studies-20261120-revision2/outputs/OUTPUT_SHA256_20261120.json`。

全部输出的哈希锁定公开提交，先于本轮第1会话标签档案首次打开与评分；不是模型规范提交，不含预测内容。

仓库级pushed_at，不是提交级独立签名PushEvent；Python日志记录NPZ档案open，不单独记录内部y.npy读取时刻。代码顺序与核验记录支持本轮公开核验后评分；不否认历史会话曝光。

- `D:\BCI_builds\OpenBMI_AB_Execution_20261120\PUBLIC_OUTPUT_RECEIPT.json` — SHA-256 `4a3368bac2d28834c4e975d15df15cc2f5868c11137769c54b789cc0ebea96dd`

- `D:\BCI_builds\OpenBMI_AB_Execution_20261120\REPORT_SUPPLEMENT.md` — SHA-256 `bdd0f001289a67be15571e0d85ac239d6410d2eb49c704306c08e3af9f738133`
