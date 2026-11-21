# 同口径基线对比 R2：阶段0完成后的冻结草案

日期2026-11-21，Asia/Shanghai。状态：**FROZEN_DRAFT_AWAITING_USER_CONFIRMATION；不授权正式训练**。

本草案固定供用户核对的配置与证据，不把“冻结草案”当作执行批准。阶段0仅做静态审查、独立环境克隆/锁定、随机合成22×1000输入的前向/反向及计时。真实EEG、真实标签、E、OpenBMI目标、真实数据2epoch探针、源fixture与历史检查点均未读取/运行。合成类别由索引mod4生成，不从文件读标签。没有神经网络正式训练，没有效果或泛化新成绩。

继承R1提交`4f101eb62af515f76a2f81c832d84682ce7eb6e7`（Markdown SHA d654faa52de3b1e38bd562cb51b267464dfef53cb19f6ef8eeb7c0f44ec3053c；JSON SHA05e1d0c093f64648a8afb4ab0b21d8fa8043c80e51e4870fa49c7c2ebaf02bf5）。R1中数据隔离、P_T试次/输入、因果偏置、被试配对统计及开发曝光声明继续有效；以下配置/范围/预算与R1冲突时，以R2明示项为准。旧R1、E/OpenBMI冻结PLAN、权重、概率及哈希清单均不改字节。

## 1. 用户范围与仍未填写的决策

- 阶段1必选：EEGNet、EEGNeX、ATCNet，各seed42/43/44、完整九折，共81训练fits；全部报告原始与同一因果校正。
- PRS：历史冻结**单套**五专家，九套留出面板，原始/校正并排；它在开发队列上选过/调过，不能与新基线等同视为未选择的三重复。此轮不读取其权重或概率。
- Conformer明确**不纳入**；DSGNet继续仅作不同协议的文献参照，不实例化或训练，不进入匹配配对统计。
- 阶段2PRS三系统重训：**阶段1审阅后再决定**；现在不做。
- 文献口径臂：**现在不做**；不解封任何E。其正确范围仍是源T训练/源E验证/留出T+E测试；IV2b对应全部五会话，与历史T1/2不同。
- 预算上限、金额、正式卡型/数量仍是用户留空的`null`。阶段0测得本机一张RTX4060 Laptop 8GB，不代表用户已指定正式训练卡或授权付费资源。没有预算与执行确认，不排正式任务。

## 2. P_T协议与比较读数

源侧仅其他8人的IV2a-T，留出者全部会话/派生资产从训练、早停、normalizer排除。源T按每源人每类75/25固定拆分，split seed20261121+100h，跨模型/训练seed共享；预期train1728、val576。源val不参与梯度、增强或BN更新，标量mean/std只从源train拟合。留出者T288条、四类、原顺序、原试次清单，九人2592条；不删困难人/错误/低置信度试次。源val为同源人内留试次，不冒称完整嵌套LOSO。

共同外部raw接口：22通道、250Hz、cue后[0,4)秒1000点；不新增v81滤波、目标EA、目标归一化或重采样。通道顺序与R1完全相同。PRS内部MSVT源标量normalizer和SCL九带4–40Hz处理保留，是模型内部差异，不声称所有网络内部变换一样。EEGNet官方接口需要`B,C,T,1`，其他两者外部`B,1,C,T`，仅轴重排，无信号数值改变。

阶段1基线每被试平均三seed指标，PRS保持固定单系统。给逐人ACC/κ、每seed结果、SD、校正−原始增量，另列PRS与各基线的同口径差。被试块bootstrap50,000次、seed20261121、配对95%百分位区间与升/降/平；不能把9×3当27人。跨零写“无法区分”；下限>0但均值ΔACC<1pp写“方向一致、幅度小”；上限<0写“有害”。ACC/κ分别报告，仅两者下限均>0才称此配对两指标都提高。多基线区间是逐对、非同时区间，不作全家族确认优胜声明。

历史PRS与新基线的配对结果为探索性参照；被试bootstrap不消除PRS开发选择偏差。72.9167%候选、完整PRS多分支不纳入。不得用源NLL或目标最高seed替代整体ACC/κ。未来正式运行前仍须固定真实试次ID与输入/normalizer元数据，完成各臂源预检；阶段0合成通过不替代这些检查。

## 3. 本轮逐项解决的配置

### EEGNet：batch与核长的证据边界

官方仓库vlawhern/arl-eegmodels，提交`4a512e503198db2010848813ead9afbf8cd54c97`。8,2架构、F1=8,D=2,F2=16、跨被试dropout=.25、Adam、CE、500轮、源val_loss最小检查点。原论文没有明确公布MI专用batch；不能把未公开值说成已查到。R2事先固定**batch16**，依据作者官方示例，但明确这是协议补足，不称论文MI原始默认。

原SMR采用128Hz、32点约.250秒；匹配PRS的250Hz输入后，固定**核长64点约.256秒**以保留时间支持，不再采用R1暂拟的32点。此选择仅由采样率和公开结构决定，未读真实数据或试过目标分数，也不做核长扫参。共同raw接口不追加论文原来4Hz高通，因此本比较是匹配协议适配，不称逐字复现原SMR预处理。

不增加LR scheduler或提前终止；训练上限500轮，每轮只看source-val-loss，strict更低才替换best，并列保留最早；未来恢复同一best权重。

### EEGNeX：监控量固定为论文accuracy

仓库chenxiachan/EEGNeX，提交`044d7fb2a5b953c7004f30fe45db40d1ce57af5c`。原论文3.3明确监控验证accuracy，故R2采用**val_accuracy / max**，不沿notebook的val_loss。Adam lr.001、batch128；200轮上限来自官方notebook，不能说论文原文明确了200轮。

LR plateau：factor.5、patience5、min_delta1e-4、cooldown0、min_lr0；early stopping：patience20、min_delta0、baseline=None、restore_best_weights=True；checkpoint按val_accuracy strict更高保留最早。所有监控只用source-val。LR的min_delta与best/ES严格改善阈值不同，保留框架明确值，不含混称“同一个提高”。

沿官方`EEGNeX_8_32`结构，只去掉画图和函数内compile副作用；没有改卷积、池化、BN、dropout。**官方代码的BN默认axis=-1在channels_first卷积块上是时间末轴，已如实保留**，未偷偷修成通道轴。参数量71188由这一确切实现产生，不能对外称所有论文实现都应相同。若未来研究修正该轴，需新协议，本轮不做。

### ATCNet：回到2022训练配方，排除后加L2

原论文作者上传稿III-C（PDF第7页）和2022官方`main.py`同时明确Adam **lr=.0009、batch64、1000轮、patience300**。旧稿.001是后续代码配置，R2纠正。官方仓库固定2022提交`cd702831b1310476507dde3a10a9fc4dcd0d3cbd`，n_windows5、MHA、pool7等按该训练入口传参。

不采用2023代码的`ATCNet_`及conv L2=.009、dense L2=.5。先前对该新版结构完成的合成测量作为已废止工程profile保留，不进入R2预算。选择旧代码基于来源年份/论文训练配方，未看真实结果，不是挑更快或更准的profile。

另有初始化原文/代码差异：论文称Glorot uniform，旧TCN函数四处写he_uniform。R2明确按论文将这四处**kernel_initializer改为glorot_uniform**，通过AST记录，非偷偷改结构；其余作者层结构与max-norm约束保留。没有添加全局weight decay或后来的L2。所有这些是待用户核对的公开适配，不冒称原仓库逐字未改。

LR根据source-val_loss：factor.9、patience20、min_delta1e-4、cooldown0、min_lr.0001。ES与checkpoint只看source-val_accuracy/max，ES patience300/min_delta0，恢复最早best；不得把test作为validation，也不得照原入口跨目标挑run。

## 4. epsilon、weight decay、BN与环境锁

实际独立Conda：`E:/BCI_CV/.conda/prs_stage0_tf210`，Python3.8.20、TensorFlow2.10.0、Keras2.10.0、NumPy1.23.5；CUDA11.2、cuDNN8.1环境及二进制哈希见ENVIRONMENT_LOCK.json。新环境克隆自既有专用TF GPU环境，没有改当前bci；bci的222个包名/版本清单前后哈希相同。PyCharm可选该环境python.exe；此轮未改IDE设置。

EEGNeX原README为TF/Keras2.8，本机原生Windows GPU profile使用2.10，**属于显式版本适配，不称原环境逐位复现**。官方TensorFlow文档说明原生Windows GPU止于2.10；不因此给所有框架升级到最新。Conda显式构建/MD5清单、pip-only精确版本、77个实际发行包版本、运行时源码和CUDA/cuDNN关键DLL SHA均存档。重建须核对这两层，不能把含file://构建路径的原始pip freeze直接称可安装锁文件。这个TF环境只登记为神经基线环境；因果校正与评分继续沿用原钉住实现及其数值环境，不因克隆环境中的SciPy版本改变而替换求解器。本轮没有运行校正或评分。

三者Adam都固定beta1=.9、beta2=.999、epsilon=1e-7、amsgrad=False、decay=0；此旧式Adam没有解耦weight_decay参数，不另加decay。约束与L2不是同一概念：保留作者max-norm，不把新ATCNet的L2混进旧版。CE from_logits=False、label_smoothing0、SUM_OVER_BATCH_SIZE，后端epsilon=1e-7。

BN epsilon=.001、momentum=.99、center/scale=True；具体axis、trainable、initializer、约束、注意力LayerNorm epsilon1e-6等逐层记录在三个MODEL_CONFIG文件中，均绑定TF/Keras2.10源码SHA。固定float32、TF32关闭、JIT关闭、不混精度、默认channels_last，再按模型自身明确的data_format运行。种子固定但**未开启全算子确定性**，不声称跨驱动bitwise相同。实测与预算对应这一profile；更换版本/设备/确定性策略要另核验，不能直接套用时间。

## 5. 历史五专家源回放门槛：仅登记、不回放

按本轮用户明确指定，R2之后五专家及其完整五者平均的源fixture回放采用**最大绝对概率差≤2e-5，rtol=0**；逐组件、逐面板记录，另要求判决变化0、顺序/类别/normalizer与来源绑定一致。差异大于门槛即不可执行，不替代。最大两类间隔≤4e-5的近并列试次必须单列，即使判决未变也不能隐去数值风险。

理由：预登记为跨GPU/卷积后端、float32算术与概率聚合顺序差异的工程绝对误差预算，量级远小于1%的概率变动；加“零判决变化＋来源/输入绑定”防止仅靠宽误差容许语义错误。**数值由用户事先指定，不是本轮用真实fixture估出或用旧失败成绩挑出的新阈值；阶段0没有数据支持其普适性。**概率容差本身不证明训练隔离或泛化。

这只登记R2的**五专家**新预检合同，不追溯修改旧完整PRS45格、旧2e-6 oracle、E/OpenBMI PLAN或历史失败状态，不把旧失败改成通过。未来要回放仍须另有真实源侧读取授权；本轮未读fixture、归档概率或检查点，状态是“未运行”。

## 6. 阶段0实测与预算更新

RTX4060 Laptop、8192MB标称/驱动报告8188MiB；driver560.94。每模型独立新进程，仅合成随机张量；3步预热、20步计时反向（含梯度检查、Adam更新、约束）、另5步计时eval。每步以.numpy()同步GPU；不报合成准确率。参数与显存是这一实现/输入/batch的实际值。

| 模型 | batch | 总参数 | 反向步中位ms | eval步中位ms | 峰值TF分配MiB |
|---|---:|---:|---:|---:|---:|
| EEGNet | 16 | 3524 | 3.128 | .750 | 327.91 |
| EEGNeX | 128 | 71188 | 94.929 | 28.241 | 3766.65 |
| ATCNet（2022＋论文初始化） | 64 | 115172 | 36.429 | 6.712 | 2391.60 |

以完整81fits、固定最大epoch预算计算（不是早停预测）：train_steps=ceil(1728/batch)，val_steps=ceil(576/batch)。纯计算中位估计为27×epochs×(train_steps×train_median+val_steps×eval_median)/3600；另列P90。实际数据管道、权重保存、调度/验证额外开销没有获准测量，规划区间用1.5×中位至4×P90，并加实测预热×27；这些乘数是明确的未实测裕量，不是置信区间或承诺。

| 组件 | 更新后GPU小时（约） | 证据/限制 |
|---|---:|---|
| EEGNet完整九折×3seed | 2.07–6.33 | 合成计算＋未测开销裕量 |
| EEGNeX完整九折×3seed | 3.33–8.95 | 同上；不预测早停轮数 |
| ATCNet完整九折×3seed | 11.79–35.21 | 1000轮最大上限，非预计一定跑满 |
| 三基线训练 | 17.19–50.49 | 81fits，未包含任何真实数据探针 |
| 基线推理/保存预留 | 1–6 | 延用未测宽预留，非本轮实际推理耗时 |
| 历史PRS推理预留 | .25–2 | **未测、不读取模型**，不可包装成实测 |
| 阶段1全部预算 | **约18–59** | 精确计算见BUDGET_ESTIMATE.json；CPU偏置另预留1–8CPU小时，未测 |

这是本机计算条件下的规划修正，不是训练ETA、收费上限或实际数据性能证明。TF峰值allocated不等于驱动总占用；cuDNN预热曾尝试较大workspace后回退，最终均成功，警告保留。未核实其他卡型吞吐，不按PPU标称算力换算。

阶段2当前不做，原135组件fits、约135.75–1086GPU小时仍仅是未核完整配方的旧占位，不以这三基线合成速度更新PRS训练成本。文献臂当前不做，其旧成本不进入阶段1总预算。预算上限与生产卡仍null，等用户明确。

## 7. PPU核查与工程失败披露

通过本聊天内置浏览器、官方入口恢复控制，实际打开既有PPU Jupyter工作区，新建独立终端，仅执行框架metadata检查；看到Python3.10.13、tensorflow_available=False、torch_available=True。该PPU不能直接运行本TF官方profile；没有上传真实数据、读取旧RESULT/标签或启动模型任务，没有擅自换成简化PyTorch基线。未创建付费实例。后续若要PPU分流，先另核验其TF后端或登记有依据的移植；不把当前CPU/GPU预算直接套给PPU。

全部失败保留：克隆首轮Windows路径解析、离线缓存缺失、缓存目录配置；克隆未结束时预检缺numpy.version；脚本编码别名、配置name重复、EEGNet输入轴错误。前述失败均在有效合成optimizer更新前终止；最后按固定版本对三模型完整重跑。早期成功的EEGNeX与新版ATCNet各23步，最终三模型各23步：**累计115次合成optimizer更新，其中69次属于最终锁定profile；正式训练fits为0**。新版ATCNet成功profile因来源不匹配而废止，数值仍保留，不混进最终测量。没有因真实评分修复、挑配置或排除被试。

访问审计覆盖合成worker的Python open调用与明确拒绝规则；实际日志无真实数据打开、无拒绝事件。它不是OS级完整系统文件审计，不据此虚称底层DLL所有访问均被捕获。静态代码只抽取官方模型定义，不执行含load_data/np.load的训练入口。完整每步时间、源码/脚本SHA与失败索引存档；PUBLIC文件只含协议、代码、依赖和合成元数据，无真实概率/标签/EEG/权重。

完成环境安装后仅定向清理本轮下载的72个包压缩归档、约1.41GiB；包名/字节/SHA保留，独立环境、源代码、模型/研究资产及解包缓存未删。bci包清单未变；旧科学门槛保持未通过/未运行。

## 8. 结束条件与公开字节核验

阶段0现在完成；R2只供核对。正式训练、真实源侧回放、目标推理、评分与任何E/OpenBMI读取继续禁止。缺省预算/卡型不得自行填写成授权；下一步是用户核对R2并明确后续执行范围，不自动进入阶段1。

公开包UTF-8无BOM、LF，目录.gitattributes为`* -text`。SHA256SUMS.json登记**Git提交中的确切字节**及长度，排除自身循环；提交后按完整commit匿名下载清单与全部文件逐字节核验。父R1包原字节不改；提交回执与清单自身SHA另存。SOURCE_VERSIONS.json区分上游Git blob与本地执行脚本/归档文件的哈希对象，不能再用API文本相同替代字节相同。

主要来源：[EEGNet原文](https://arxiv.org/pdf/1611.08024)、[EEGNeX原文3.3](https://arxiv.org/html/2207.12369v4)、[ATCNet作者稿III-C](https://www.researchgate.net/profile/Hamdi-Altaheri/publication/362491847_Physics-informed_attention_temporal_convolutional_network_for_EEG-based_motor_imagery_classification/links/62ffa4bbaa4b1206fac197bd/Physics-Informed-Attention-Temporal-Convolutional-Network-for-EEG-Based-Motor-Imagery-Classification.pdf)、[ATCNet2022 main.py](https://github.com/Altaheri/EEG-ATCNet/blob/cd702831b1310476507dde3a10a9fc4dcd0d3cbd/main.py)、[TensorFlow Windows GPU边界](https://www.tensorflow.org/install/pip#windows-native)。
