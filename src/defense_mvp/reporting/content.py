"""Controlled Chinese report, slide copy and narration from one fact registry."""
from .core import FAMILIES, FIELDS, LABELS, CASE_LABELS, narrative_guard, script_seconds


def compose(registry, data):
    r=registry; cfg=data['cfg']
    a,b=[f+'.overall.' for f in FAMILIES]
    def result(stem):
        return f"W/L/T/U = {r[stem+'wins']}/{r[stem+'losses']}/{r[stem+'ties']}/{r[stem+'uncertain']}，n={r[stem+'total']}；tie-aware {r[stem+'tie_aware_win_rate']}，95% CI [{r[stem+'bootstrap_lower']}, {r[stem+'bootstrap_upper']}]"
    conclusion=(f"约束式 N=4 相对 N=1 有描述性正向点估计，但 CI 跨 0.5；相对 Linear N=4 未观察到差异。"
                "当前证据不足以支持显著或稳定优势。工程贡献是可复现的候选选择、盲评、统计与身份审计。")
    limits=(f"只有两位评审，其中一位是开发者参与者，采用同机配合式盲评。只有 {r['sample_clusters']} 个 sample clusters，区间较宽；"
            f"一致性较低，overall agreement {r['agreement.overall.diagonal']}/{r['agreement.overall.n']} = {r['agreement.overall.observed_agreement']}，"
            f"kappa {r['agreement.overall.cohen_kappa']}。CPU F/P/T/Q 是代理指标，{r['qualitative_candidates']} 个对象转换候选未量化。")
    metrics=[
        ('F 指令忠实度代理','前景内变化与目标色支持度的几何平均；local 只计新增目标色','颜色出现不能证明目标物体或正确子部位出现'),
        ('P 非目标保持代理','1 减 mask 外输入与候选的绝对误差','前景内部非目标破坏可能漏检'),
        ('T 时序一致性代理','1 减相邻编辑残差变化；裁剪到单位区间','没有光流或运动补偿'),
        ('Q 视觉质量代理','梯度保留、正常曝光和亮度稳定性的几何平均','低层图像特征不能替代感知质量判断')]
    stages=['导入与 checksum','F/P/T/Q 代理','N=1/2/4 嵌套子集','三方法选择','双人盲评','D4 冻结统计','D5 报告初稿']
    report=['# 指令视频编辑候选选择与盲评系统：D5 报告初稿','',
            '## 摘要','',conclusion,'',
            '## 问题与范围','',
            f"同一输入的随机候选质量存在差异，本系统研究怎样在固定候选池中进行可复现选择。"
            f"真实输入为 {r['samples']} 个 sample、{r['candidates']} 个既有 AnyV2V 候选。"
            f"{r['primary_samples']} 个颜色/局部编辑任务的 {r['scored_candidates']} 个候选完成 CPU 定量评分；"
            f"{r['qualitative_samples']} 个对象转换任务的 {r['qualitative_candidates']} 个候选只作 qualitative_only 能力边界。"
            "本阶段没有生成视频、训练模型或新增效果测量。",'',
            '## 系统与身份审计','','![系统流程](figures/system-flow.svg)','',
            '原始媒体、帧序列、配置、候选角色及产物清单逐级绑定 SHA。D5 在通过独立 D4 验证后读取机器事实，'
            '保留稳定数据和运行回执，失败输出保留，成功目录不覆盖。','',
            '## F/P/T/Q 与约束式选择','',
            '| 维度 | 计算含义 | 边界 |','|---|---|---|']
    report.extend('| '+' | '.join(row)+' |' for row in metrics)
    report += ['', 'mask 来自 DAVIS 前景对象，按非零类别索引解码。local 的 mask 不是背包、头盔或车灯的专门分割。', '',
        '三方法为 N=1 baseline、equal-linear N=4 与 constrained Pareto/max-min N=4。工程设计保留 random、'
        'equal-linear、constrained-pareto 在 N=1/2/4 的完整选择记录；N=1 时三方法选中同一候选。', '',
        '排序先用子集内部稳定 rank-percentile。线性方法取四维等权平均，允许维度补偿。约束式方法要求 F 不低于中位数、'
        'P 不低于下四分位数，然后求 Pareto 非支配前沿，优先最大化最弱维度，其次几何平均，最后按候选 ID 稳定决胜。'
        '若可行集为空，按 min(F,P)、T、Q 和 ID 回退。', '',
        f"D2 共 {r['fallback_n2']} 次 Pareto fallback，全部在 N=2。它是工程现象，不是两个正式盲评 family 之外的新比较组。",'',
        '## 双人盲评与保守聚合','',
        f"方法、seed、分数与路径在评审界面隐藏，位置方向独立平衡。两位评审各完成 {r['human_pairs']} 个实际观看比较。"
        f"正式分母是 {r['records']} 个唯一 comparison = {r['human_pairs']} 个 human_pair + {r['automatic_ties']} 个共享 automatic tie。"
        '媒体相同的自动平局仅计一次，不伪造成两份人答，也不进入 agreement/kappa。', '',
        '双方同一 decisive 保留该结果；decisive 与 tie 聚合为 tie；方向相反或任一 uncertain 聚合为 uncertain。'
        'tie 与 uncertain 在 tie-aware 中均计半分，但原始计数始终分开。主表保留全部比较，不做事后删题或子组检验。','',
        '## 正式主结果','',
        f"{LABELS[FAMILIES[0]]}：{result(a)}。",'',f"{LABELS[FAMILIES[1]]}：{result(b)}。",'',
        '![描述性区间](figures/overall-ci.svg)','',
        '![四类结果组成](figures/outcomes.svg)','',
        '| 比较 | 字段 | W | L | T | U | n | tie-aware | decisive（诊断） | 95% CI | 有效/无效 bootstrap |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for f in FAMILIES:
        for field in FIELDS:
            stem=f+'.'+field+'.'
            vals=[LABELS[f],LABELS[field]]+[r[stem+k] for k in ('wins','losses','ties','uncertain','total','tie_aware_win_rate','decisive_win_rate')]
            vals += [f"[{r[stem+'bootstrap_lower']}, {r[stem+'bootstrap_upper']}]",f"{r[stem+'valid_bootstrap']}/{r[stem+'invalid_bootstrap']}"]
            report.append('| '+' | '.join(vals)+' |')
    report += ['', f"CI 使用 {r['sample_clusters']} 个 sample clusters、{r['bootstrap_iterations']} 次预冻结 bootstrap。"
        '每次整体重采样任务，不把比较或字段当独立样本。区间仅描述任务级小样本不确定性，跨半分不能转写为效果证明。', '',
        f"补充 decisive 诊断为 {r[a+'decisive_win_rate']} / {r[b+'decisive_win_rate']}，只在胜负子集上计算，不能替代主胜率。",'',
        '[原始精度主表](tables/main-results.csv)','',
        '## 一致性与 Bradley–Terry','',limits,'',
        '![双人一致性](figures/agreement.svg)','',
        f"五字段 exact agreement 为 {r['exact.numerator']}/{r['exact.denominator']} = {r['exact.rate']}。"
        '四类 canonical 值分别保留，自动平局没有进入一致性分母。', '',
        f"BT 状态 ok，只使用 overall 的 {r['bt.edges']} 条 decisive 边。中心化 ability："
        f"Proposed N=4 {r['bt.constrained-pareto-n4']}、Linear N=4 {r['bt.equal-linear-n4']}、N=1 {r['bt.constrained-pareto-n1']}。"
        'Proposed 与 Linear 相同；边少、估计脆弱，不解释为稳定总体排名。', '',
        '[一致性完整表](tables/agreement.csv)','',
        '## 确定性案例','',
        '案例规则在查看正式媒体前冻结。成功、失败、不确定均按指定 family 内稳定键取首项，缺类明确 unavailable。'
        '定性边界按任务 ID 取首项并显示全部候选，不赋予胜负。所有定量页同时显示输入、Proposed 和 comparator。', '',
        f"所有方法统一使用已验证 {r['protocol.frame_count']} 帧序列的索引 {r['protocol.frame_first']}、{r['protocol.frame_third']}、"
        f"{r['protocol.frame_twothirds']}、{r['protocol.frame_last']}，对应首帧、三分之一、三分之二与末帧。"
        '完整图像不裁切，页面展示缩放保持比例，原始帧像素不改动；静态帧不能替代整段视频评估。','']
    for i,item in enumerate(data['cases']):
        state={'win':'正式聚合为 Proposed win','loss':'正式聚合为 Proposed loss','uncertain':'正式聚合为 uncertain','qualitative_only':'对象转换未量化，不参与主结果'}[item['kind']]
        report.append(f"- [{item['label']}](cases/case-{i+1}.html)：{state}；{item['status']}。")
    report += ['', f"[案例总览](cases/index.html)；完整 D4 失败索引共 {r['failure_case_count']} 条，内部 trace 保留反查关系。"
        '本报告不使用评审 notes 补充故事，不根据图像观感改换样例。', '',
        '## 成本与复现','',
        f"E0 历史 {r['candidates']} 候选生成 runtime 合计 {r['cost.e0_generation_runtime_sum']} s；报告过的 peak VRAM 最大 "
        f"{r['cost.e0_generation_peak_vram_max']} MB。D2 metrics elapsed {r['cost.d2_scoring_total_elapsed']} s，"
        f"按全部验证候选为 {r['cost.d2_scoring_per_candidate_elapsed']} s/candidate。D4 compute {r['cost.d4_analysis_compute_elapsed']} s。",'',
        f"D2 selection timer 为 {r['cost.d2_selection_elapsed']}，不以估算补齐。评审 A/B current-view server elapsed 为 "
        f"{r['cost.d3_reviewer_A_current_view_elapsed_sum']} / {r['cost.d3_reviewer_B_current_view_elapsed_sum']} s，含停顿、后台和恢复，"
        '不能解释为主动观看时间或精确工时。','',
        '[成本、状态与来源](tables/costs.csv)；[事实注册表](report-data.json)；[输入身份](input-manifest.json)。', '',
        '使用 `python -m defense_mvp.reporting report` 指定完整 D4/D2 输入、冻结配置与新输出根；'
        '`verify-report` 重建稳定报告内容并验证图、案例和 Slides 语义。命令和依赖见回执。PPTX保留实际SHA，'
        '内部时间戳不承诺字节级重建。报告/表/图的稳定输出通过跨路径重建验证。', '',
        '## 威胁、结论与后续','',limits,'',conclusion,'',
        '未来研究可增加任务与独立评审、改进语义指标，并在新协议下验证；这些未在本阶段实施。'
        'D5 交付报告与 Slides 初稿。D6 的展示冻结、录屏和计时演练尚未启动。']
    report += ['', '## 机器事实来源摘要', '',
        'D4 主表 SHA-256：`'+r.entries[a+'wins']['source_sha256']+'`。', '',
        'D4 summary SHA-256：`'+r.entries['records']['source_sha256']+'`。', '',
        f"两 family 的共享自动平局分别为 {r['auto.'+FAMILIES[0]]}/{r['auto.'+FAMILIES[1]]}；计入主分母，不进入一致性。"]
    report_text='\n'.join(report)+'\n'
    # Each section describes the same fact set; numbers are inserted only through the registry.
    speeches=[
        '今天介绍的是基于约束式多目标排序的指令视频编辑候选选择与盲评系统。问题来自一个很具体的场景：同一条编辑指令，生成模型可能给出外观不同的候选。怎样选择，怎样验证选择是否符合人的偏好，是本系统的研究对象。'+conclusion+'因此答辩会同时展示结果和证据的边界，评价重点也包括流程能否重建、偏差能否保留，以及结论能否回到正式产物。',
        f"本系统复用既有审计输入，共 {r['samples']} 个任务和 {r['candidates']} 个真实候选。每个任务的候选池固定，整个研究不额外生成视频。"
        f"其中 {r['primary_samples']} 个颜色或局部编辑任务的 {r['scored_candidates']} 个候选完成定量评分；另外 {r['qualitative_samples']} 个对象转换任务的 {r['qualitative_candidates']} 个候选只作能力边界。"
        '这种划分来自指标能够支持的测量范围。动物类别是否真的转换，无法靠颜色和梯度可靠回答。所以定性候选保持未量化状态，不进入主表，也不能借用它们的画面来扩大效果结论。',
        '系统从只读媒体导入开始，核对视频、帧序列与候选身份，然后完成代理评分、嵌套子集设计和选择。评审只看匿名化输入与候选，统计阶段再恢复方法方向。最后报告消费已经验证的机器事实。每一层都保存配置和摘要，关联的是具体候选与具体媒体，而不只是一串文件名。输出采用不可覆盖目录，失败会保留诊断。这样做的意义是让报告上的数字能回到主表，让案例中的图片能回到原帧，而不是仅凭一张完成截图宣布实验可信。',
        '四维指标分别描述指令相关变化、非目标区域保持、时序残差稳定和低层视觉质量。忠实度代理使用前景内变化与目标色支持，局部任务关注相对输入新增的颜色。保持度在前景外计算，时序项关注相邻编辑残差，质量项组合梯度、曝光和亮度稳定。它们都可以在本地中央处理器上复现，但每一项都有明确盲区。例如前景中出现红色，不能证明背包正确出现；前景内部的非目标破坏可能逃过保持指标。代理只能提供排序信号，语义与感知评价仍要交给人。',
        f"选择设计使用嵌套 N=1/2/4 候选子集。N=1 是基线；N=4 比较等权线性与约束式方法。"
        '线性平均允许高保持补偿低编辑。约束式方法先在子集秩分上设置忠实度中位数和保持度下四分位门槛，再保留四维非支配候选，优先提高最弱维度，最后用几何平均和固定身份顺序决胜。'
        f"D2 已记录 {r['fallback_n2']} 次空集回退，全部发生在 N=2。这个现象原样保留，它说明小子集门槛会冲突；不能把回退数量包装成额外的人评比较，也不能看到正式结果后再调门槛。",
        f"两位评审分别完成 {r['human_pairs']} 个人工比较。加上 {r['automatic_ties']} 个共享自动平局，得到 {r['records']} 个唯一聚合比较。"
        '自动平局来自方法选中了同一媒体，所以只保留一个系统事实，避免重复计数。人工界面隐藏方法和分数，方向独立平衡。双方同向才保留明确胜负；胜负与平局组合保留平局；方向相反或任一不确定则保留不确定。这是事先冻结的保守规则。它会降低明确胜负的数量，却避免揭盲后主观裁决。评审包含开发者参与者，所以这里是同机配合式盲评，不能推及一般评审群体。',
        f"先看全部比较的总体偏好。对 N=1，{result(a)}。对线性 N=4，{result(b)}。"
        f"区间来自 {r['sample_clusters']} 个任务整体重采样的 {r['bootstrap_iterations']} 次 bootstrap。"
        '两组区间都跨 0.5。相对基线出现描述性正向点估计，相对线性未观察到差异。平局与不确定虽然在主分数中都记半分，图表始终分列原始数量。只保留明确胜负会产生另一种分母，所以 decisive 只能作为补充诊断，不能放大为主要效果。',
        '案例页同时展示成功、失败和不确定，选例依据在打开媒体前已经固定。每类按稳定身份键取第一项，不因画面好看或效果强而换例。输入、约束式结果与对照使用同样的四个归一化帧位置。成功只代表该比较的正式聚合偏向约束式方法，失败说明同样的流程也会选出不被偏好的结果，不确定则保留证据分歧。静态帧是方便核查的切片，不能代替整段时序结论。另有完整定性边界页，展示固定对象转换任务全部候选，明确不赋予胜负。',
        f"结果还受到一致性与成本口径限制。overall agreement 为 {r['agreement.overall.observed_agreement']}，kappa 为 {r['agreement.overall.cohen_kappa']}，一致性较低。"
        f"BT 只依赖 {r['bt.edges']} 条明确胜负边，Proposed 与 Linear 的 ability 相同，因此估计脆弱。"
        f"D2 指标 elapsed 为 {r['cost.d2_scoring_total_elapsed']} 秒，选择计时为 unavailable。"
        '历史生成耗时与本地统计耗时来自不同阶段，不能混成整体加速比。评审页面累计时间包括停顿和后台，也不是精确观看工时。可复现记录能帮助解释这些限制，却不能消除小样本或低一致性本身。',
        f"最后回到结论。在这 {r['sample_clusters']} 个定量任务上，约束式选择相对基线有描述性信号，区间跨 0.5；相对线性未观察到差异。"
        '当前可以交付的是完整的选择、盲评、统计和审计系统，以及诚实保留负面与不确定结果的报告初稿。未来若增加任务、扩展独立评审或引入语义评价，需要另立协议，不能在当前结果上事后调整。后续展示阶段只做排版冻结、录屏和讲稿演练，不改变实验分母、指标或案例。这样的完成标准不依赖一个好看的胜率，而依赖每个结论与输入证据保持一致。']
    script='# D5 答辩讲稿初稿\n\n'+'\n\n'.join(f"## 第{i+1}页 {cfg['slides']['titles'][i]}\n\n{text}" for i,text in enumerate(speeches))+'\n'
    slides=[
        {'lead':'基于约束式多目标排序的\n指令视频编辑候选选择与盲评系统','body':['相对 N=1 有描述性正向点估计，CI 跨 0.5','相对 Linear N=4 未观察到差异'],'footer':'Defense MVP · D5 初稿'},
        {'lead':f"{r['samples']} 个任务 / {r['candidates']} 个真实候选",'body':[f"{r['primary_samples']} 个定量任务 / {r['scored_candidates']} 个候选",f"{r['qualitative_samples']} 个对象转换任务 / {r['qualitative_candidates']} 个候选",'颜色与局部编辑进入主表','对象转换保持 qualitative_only'],'footer':'复用已审计 E0 候选，每个任务固定候选池'},
        {'flow':stages,'body':['配置与媒体 SHA 逐级绑定','匿名评审后恢复方法方向','失败诊断保留，成功目录不覆盖'],'footer':'D1–D4 正式事实只读；D5 仅报告'},
        {'metrics':metrics,'footer':'DAVIS 前景 mask；local 没有目标子部位分割'},
        {'body':['子集秩分保持固定排序','F ≥ 中位数，P ≥ 下四分位数','Pareto 前沿内优先最大化最弱维度','几何平均与候选 ID 稳定决胜'],
         'lead':'等权线性允许维度补偿\n约束式先筛门槛，再处理折中',
         'footer':f"N=1/2/4 嵌套设计；{r['fallback_n2']} 次 fallback 均在 N=2，不是额外盲评组"},
        {'lead':f"{r['human_pairs']} 人工聚合 + {r['automatic_ties']} 自动平局 = {r['records']} 唯一比较",'body':['两位评审，方法与分数隐藏，位置方向独立平衡','同向胜负保留；decisive + tie 保留 tie','方向相反或任一 uncertain 保留 uncertain','自动平局不进入 agreement / kappa'],'footer':'同机配合式盲评，含一位开发者参与者'},
        {'figure':'overall-ci','body':[LABELS[FAMILIES[0]],result(a),LABELS[FAMILIES[1]],result(b)],'footer':f"all-42；{r['sample_clusters']} clusters，{r['bootstrap_iterations']} bootstrap；描述性区间均跨 0.5"},
        {'case_labels':CASE_LABELS[:3],'body':['同一稳定键取首项，统一四帧位置','输入、Proposed 与对照同时展示；静态帧仅辅助核查'],'footer':'成功/失败来自正式聚合；不确定保留分歧。完整帧与定性边界见报告案例页'},
        {'figure':'agreement','body':[f"overall agreement {r['agreement.overall.observed_agreement']}，kappa {r['agreement.overall.cohen_kappa']}",
             f"BT 仅 {r['bt.edges']} 条 decisive 边；Proposed = Linear",f"D2 metrics {r['cost.d2_scoring_total_elapsed']} s；selection unavailable",
             f"两位评审、{r['sample_clusters']} 个任务；CPU 指标是代理"],'footer':'一致性较低、CI 较宽，BT 估计脆弱；页面elapsed不是精确工时'},
        {'lead':'描述性信号需要更多独立证据','body':['相对 N=1 有正向点估计，但区间跨 0.5','相对 Linear N=4 未观察到差异','工程贡献：选择、盲评、统计和身份审计可重建','后续研究须扩展任务与评审，并另立协议'],'footer':'当前为 D5 初稿；展示冻结、录屏与演练属于后续 D6'}]
    for i,slide in enumerate(slides):
        slide.update(index=i+1,kind=cfg['slides']['order'][i],title=cfg['slides']['titles'][i],notes=speeches[i])
        if data.get('evidence_status')=='synthetic-engineering-only': slide['footer']='SYNTHETIC 工程布局测试，非研究证据'
    if data.get('evidence_status')=='synthetic-engineering-only':
        report_text='> SYNTHETIC 工程测试材料，非研究证据\n\n'+report_text
        script='<!-- SYNTHETIC engineering only, not research evidence -->\n'+script
    narrative_guard(report_text,r)
    narrative_guard(script,r)
    timing=script_seconds(script,cfg)
    recording='''# D6 录屏路径方案（D5 仅编排）

本阶段没有录制、计时演练或最终交付 manifest。预定录屏时长60–90秒，D6需另行接续。

| 时段 | 展示 | 安全与降级 |
|---|---|---|
| 0–15秒 | 冻结配置与已通过的 checksum/verifier 回执 | 展示公开摘要，命令过慢用已保存回执 |
| 15–35秒 | 既有盲评界面的安全练习截图或隔离练习界面 | 隐藏地址栏、会话路径与身份，不打开正式作答会话 |
| 35–50秒 | 三方法选择定义与已冻结选择摘要 | 不重新评分或选择，页面失败用报告图 |
| 50–75秒 | 自动报告主表、CI、固定失败/不确定案例 | 使用本地静态页，读数包含分母和局限 |
| 75–90秒 | 一句话结论及工程复现入口 | 保留描述性、宽CI与低一致性说明 |

D6实际录制前核查截图没有会话令牌、私有映射或原始答案。若无安全盲评截图，
使用已有practice专用fixture页面进行安全截图准备；不读取正式答案，不重启正式服务。
现场演示失败时使用D6冻结的录屏和最终Slides/PDF副本；此处不创建这些最终产物。
两次计时演练、最终PDF和交付清单都留在D6。
'''
    return {'report':report_text,'script':script,'recording':recording,'slides':slides,'timing':timing,'metrics':metrics,'flow':stages,'conclusion':conclusion}
