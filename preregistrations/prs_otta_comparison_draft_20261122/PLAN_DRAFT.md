# OTTA同骨干对比：待核对草案

日期：2026-11-22（Asia/Shanghai）。状态：DRAFT_NOT_EXECUTABLE。仅授权文档、公开提交与字节核验；不授权训练、推理、标签读取、环境安装或冒烟。所有旧PLAN、数据隔离与历史文件保持原字节。本草案不是旧OpenBMI/E计划的修订。

## 1. 问题、选择与边界

问题：在同一源训练骨干、同一IV2a-T时间流上，无标签输出偏置相对于有公开实现的在线BN适应/熵最小化是否有收益？这是开发队列上的探索性匹配比较，不是新的独立确认，也不能由此宣称跨库泛化。

选择Wimpff官方eeg-otta的两个方法，直接保留其TTAMethod缓冲与返回语义：

|方法|固定代码与许可证|保留定义|
|---|---|---|
|BN-1 / norm_test|martinwimpff/eeg-otta @ e71e0aba60a2c60d908eddc4b74ee9b11f0dc320；MIT|model.eval后仅BN2d.train；冻结所有梯度；当前及此前最多32试次的批统计；不作梯度更新|
|EntropyMinimization（EM，无对齐配置）|同一提交；MIT|model.eval，全部参数可训练，BN关闭running stats；32试次缓冲，每32次到达进行一次条件熵梯度更新；返回更新前同次forward的最后一个试次logit，不重新预测当前试次|

官方配置均支持alignment=False。本草案两臂固定False，buffer_length=32；EM Adam lr=0.0005，betas=(0.9,0.999)，eps=1e-8（torch2.0.1 Adam默认，执行前静态绑定），weight_decay=0。没有边际熵项、伪标签筛选、额外更新或扫参。norm_test不需要optimizer。EM是Wimpff的无对齐配置，不称完整论文最佳路线复现；其全参数更新不能称Tent。

不纳入Tent：官方DequanWang/tent @ e9e926a668d85244c66a6d5c006efbd2b82e83e8，MIT；确有公开实现，但其BN仿射参数更新及train/dropout语义与本次选定EM不同。为限制比较规模，本轮不加第三种方法。不纳入T-TIME：其源EA、多模型集成、增量EA及自适应正则不能用单一熵头代替；本草案不作T-TIME复现声明。

来源：[Wimpff论文](https://arxiv.org/abs/2311.18520)、[官方固定提交](https://github.com/martinwimpff/eeg-otta/tree/e71e0aba60a2c60d908eddc4b74ee9b11f0dc320)、[Tent固定提交](https://github.com/DequanWang/tent/tree/e9e926a668d85244c66a6d5c006efbd2b82e83e8)、[T-TIME论文](https://arxiv.org/abs/2412.07228)。本轮仅静态阅读，不运行原入口。

## 2. 同骨干、源训练与阶段1的关系

采用eeg-otta原生BaseNet，而非把TensorFlow EEGNet权重移植成PyTorch。现有阶段1EEGNet是TensorFlow实现，不能直接供所选PyTorch方法使用；本草案需新增同一BaseNet源训练27个fit，四臂共享每折每seed的完全相同检查点。不复用官方预训练权重，其训练/会话边界未按本文核验。阶段1只作历史研究背景与粗成本参考，不与本轮BaseNet构成同权重或同架构比较；不据历史成绩选择seed。

IV2a四分类，S1–S9逐被试严格LOSO，T会话、22通道、250Hz、提示后[0,4)秒1000点；同本文既有试次ID、时间顺序、滤波和normalizer规范。每fit仅其余8人的T作源训练/源验证；每源被试每类75/25分层（54/18），1728/576；拆分seed=20261121+100*held，模型seed=42/43/44。归一化标量均值/总体标准差仅源train拟合。normalizer、过滤代码与试次ID清单必须在执行版绑定哈希，当前缺失即阻断；不能用原repo数据入口代替本文预处理。

骨干结构严格使用固定提交configs/bcic2a_loso_basenet.yaml的model_kwargs：40个长度25时间滤波器、空间扩张1、平均池75/stride15、dropout0.5、ch_dim16、第二时间核15、池8/stride8、dropout0.5、4类。BN保留torch2.0.1默认eps=1e-5、momentum=0.1，不冒称与阶段1TF BN完全等价。源Adam lr0.001、weight_decay0、label_smoothing0.4、batch64、1000epochs、20epoch warmup+官方余弦scheduler；不早停，固定训练至1000，选源val_loss严格最小的最早epoch。该权重选择规则是本文源侧协议，不冒称原作者checkpoint回调默认。scheduler源文件与依赖完全锁定前不可执行。

原train_source_model.py末尾自动trainer.test，run_adaptation.py会通过原数据模块评分；二者禁止直接执行。需标签隔离的独立编排层，只复用原模型/适应类及核心forward，不自动打开目标标签/E。源侧y仅在未来单独训练授权后可读；目标y只在输出锁定门禁后可读。本轮任何y均不读。

## 3. 四臂与时间语义

N：无适应，源检查点eval，源BN running stats，无EA、无偏置。

B：上述norm_test，缓冲最多32条，当前条到达后入缓冲，仅输出最后一条；无未来，无全目标批量AdaBN，无梯度，dropout关闭。

M：上述EM，相同buffer；t=32,64,…,288更新，共每流9次；其它到达只forward。BN使用当时缓冲批统计；在更新点返回optimizer.step之前的当前logit，更新影响随后试次。不能为提高成绩重算当前输出或将全参数更新改成仅BN。

C：仅在N的原始概率上应用历史冻结因果偏置，原始0..t含当前，前20条不修正；不叠加在B/M上。四类目标1/4，clip=1e-9，lambda=0.1+20/n，L2=lambda*mean(b²)，零和偏置约束/参数化及softmax变换沿用钉住实现；L-BFGS-B maxiter150、gtol1e-8，其余保持原SciPy1.15.3默认。生产公式/实现文件及SHA仍须执行前逐字绑定，不允许重新选求解器或容差。依赖均衡类别先验，不是纯零校准。

每臂×held×seed重新加载原检查点；独立重置BN状态、参数、optimizer、buffer和随机数，不能跨人/seed/方法积累。顺序按可核验原trial_id，不按类别重排。所有臂评同样288条，包括warmup。不得因低置信度跳过试次。EM虽无标签仍有测试时参数更新成本，不称零训练成本。

## 4. 统计、输出与披露

每seed每人分别先适应/校正再计算ACC与κ；主表先取同被试三seed指标均值，再九人均值，不先平均概率。逐seed结果、逐人结果、seed间九人均值的样本SD(ddof=1)全部报告。主要对比C−B、C−M，辅以各臂−N；配对被试bootstrap 50000次、rng20261121、95%百分位区间，报告升/降/平，不将27个seed×人当独立样本。区间跨零统一“无法区分”；下限>0且均增益<1pp为“方向一致、幅度小”；上限<0为“有害”。ACC与κ都给区间，二者在均衡四类下并非独立证据；探索性多重比较不宣布家族显著胜者。不据结果剔人/选seed/改规则。

同时记录每臂forward/backward次数、更新时间、每试次延迟分布、峰值显存与GPU占用小时；失败和中断完整记录。单fit中断整体重跑，不续epoch，完成fit保留。实际资源与热停止须执行前另授权，旧80GPU小时不自动成为本草案新预算。

## 5. 标签门禁：当前未实现、未验收，是硬阻断

沿用LESSONS_AND_FUTURE_RULES.md（SHA256 245c91e916f7fcd8f47cca02dcab0080b1abff986401a1f75f1a4d4ccb7505a9）。目标x-only与y物理/权限隔离；不能挂载可读x/y同包后声称未评分。可信保管方在获授权的计划/准备阶段预记label SHA，本轮不打开标签临时计算。必须全部4臂×9折×3seed输出锁定，公开仅哈希，保存服务器提交/推送回执，再匿名下载固定提交逐字核验，之后评分进程才可取得只读标签。公开提交未核验、网络失败、哈希不符、缺输出均fail closed，必须在任何label open前拒绝运行；不允许本地清单降级。

当前仅有文档规则与公开文件校验脚本，没有经负向测试验收的OS隔离及评分启动门禁。需未来另授权工程实现和纯合成门禁测试，确认拒绝路径不触及标签。Python文件访问hook不能代替OS权限隔离。历史阶段1标签先于公开输出哈希的缺口须保留，不能靠本草案补成预先锁定；IV2a-T已开发曝光，本研究仍探索性。

## 6. 成本估计（没有运行，不能当实测ETA）

建议估算设备仅本机RTX4060 Laptop；没有授权使用PPU/付费资源。独立Conda prs_otta_torch，Python3.10、torch2.0.1、Lightning2.0.7、braindecode0.7（原pyproject），其它传递依赖尚未锁定；不动bci/TF环境。PyCharm配置未来随环境登记。

|臂|新增源训练GPU小时|推理/适应GPU小时（27流）|依据与不确定性|
|---|---:|---:|---|
|共享BaseNet检查点|7.5–60，共享一次|不适用|27000epochs×假设1–8秒/epoch÷3600；非BaseNet实测，I/O与降频可超范围|
|N|0（复用共享）|0.02–0.2|7776单试次forward，尚未实测|
|B|0（复用共享）|0.05–0.5|7776窗口forward，235440试次等价前向；无反向|
|M|0（复用共享）|0.1–1.0|同上前向，243次32样本更新，共7776反向样本等价；未实测|
|C|0（复用共享）|额外GPU约0；复用N|CPU偏置约0.1–2小时，非实测；输出逐流求解|

合计GPU约7.67–61.7小时（不含未来环境验收、失败重跑及不可预见超时），不是预算承诺/上界。窗口计数：每流sum(1..32)+256*32=8720；27流235440。source每epoch27个训练batch和9个验证batch。源训练占主成本。若未来授权，先仅源侧计时与合成接口验收再更新预算，不能先看目标成绩决定算法或成本方案。若预算不足，须新草案确认，不能偷偷降epoch/seed。

## 7. 执行前阻断与停止线

1. 用户未确认本草案，训练/环境/目标推理/标签权限均未授权；必须停止于文档。
2. 独立依赖锁、scheduler/Adam默认与所有核心源码哈希、模型BN/输出/梯度语义静态绑定未完成；无可用的本协议BaseNet27套权重。
3. 本文源预处理、trial顺序、源split/normalizer哈希及严格held排除验证需授权准备；不调用可能读E的官方数据模块。
4. x-only导出、预记标签哈希的保管流程、OS拒绝规则及公开哈希启动门禁尚未实现/验收。标签不可读直到通过。
5. 缓冲最后条输出、9次更新、无跨人状态、无未来、原源码梯度集合的合成检查，以及源侧回放均待另授权；失败即不可执行，不改核心凑通过。
6. 原校正实现与SHA绑定、原源码MIT声明保留、实际卡型/总预算/热停止/实时看板ETA及访问日志规范须执行版补齐；不得用未知值冒充冻结常数。

完成本次公开提交后等待核对；不触发任何上述步骤。本草案不评价哪臂胜出，不改历史成绩，不涉及E、IV2b或OpenBMI目标。
