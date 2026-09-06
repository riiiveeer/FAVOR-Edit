# D5 可追溯报告与 Slides 初稿施工方案

协议：`defense-report-v1`；日期：2026-09-05；环境：本地 Windows CPU-only。

## 现场与停止点

接手 HEAD/origin/main 为 `9f1f3c565ff133c7559635b0c48d52ca5b2ab511`。
既有 DEVLOG 发布回执、根 tar/sidecar 保留。D4 完整 verifier 重验 passed，临时回执与正式
回执 SHA 相等；21 个 D4/D2/config pins、6 个内部 inventory、42 个比较角色和60个视频身份通过。
提示词 D2 表中的 SHA256SUMS 是简称，实际文件为相应大写前缀清单，摘要相同。

本阶段只生成 D5 草稿。D6 展示冻结、录屏、两次计时演练和最终交付 manifest 尚未启动。
不操作服务器、DATA4 或 GPU，不修改、重新评分、选择、标注或聚合 D1–D4。

## 实现边界与接口

D4 的 source_evidence 锁定 defense_mvp 顶层文件与 pyproject/uv.lock。为保留验证能力，D5
全部实现放在 `src/defense_mvp/reporting/`，不改顶层 CLI 和依赖锁；模块 CLI 为：

```text
uv run python -m defense_mvp.reporting report --aggregate <dir> --analysis <dir> --d4-verification <file> --selection <dir> --metrics <dir> --design <dir> --ingest <manifest> --config configs/defense_mvp/report-v1.yaml --output <new-root> --runtime-python <bundled-python> --runtime-node <bundled-node> --runtime-modules <bundled-node_modules> --slides-skill <installed-skill>
uv run python -m defense_mvp.reporting verify-report <same-input-options> --report <root> --output <new-file>
```

原 D3/D4 verifier 仍原样运行到独立 Temp 回执，内部处理原始记录仅用于复验，报告代码只消费
已验证聚合的公共投影，不读取 D3 答案、notes、private mapping 或会话。D5 自有 source identity
覆盖整个 reporting 子包、配置与测试，绑定实际 Git HEAD 和文件 SHA。源码摘要不依赖输出路径。

## 事实注册与叙事

唯一主事实来自 D4 aggregate/analysis/verification，辅助事实来自已锁定 D2。每项注册 raw、
display、digits、unit、source、pointer、source_sha256；CSV 保留原始精度。受控叙事模板共享
同一注册表，verifier 重建稳定输出并比较，检查全部链接与数字。报告公开副本由同一 artifact
文件生成并复制其非敏感 tables/figures，案例链接指向本地忽略产物，发布回执记录副本 SHA。

主表保留两 family × 五字段 all-42 的 W/L/T/U、n、tie-aware、decisive、CI 及有效/无效
bootstrap 次数；manual-only 不替换正式分母。agreement 五字段与 exact-vector 分开，manual
n=32，automatic tie 不进入。BT 仅11条 decisive 边，Proposed 与 Linear 相同且估计脆弱。
成本保留单位和 unavailable，不把 current-view elapsed 写成主动观看时间。

主结论为：相对 N=1 有描述性正向点估计且 CI 跨0.5，相对 Linear N=4 未观察到差异。
小样本、低 agreement、两位评审含开发者、CPU 代理和15个未量化候选必须显式出现。
不新增检验、阈值、子组或研究测量，不从评审 notes 编造可见现象。

## 展示协议与媒体 gate

版本化 `report-v1.yaml` 固定颜色、字体 fallback、显示精度、1600×900白底160DPI图、CI轴0–1、
agreement/kappa轴−1–1、参考0.5、图例四类分开。采用 bundled Python Matplotlib 生成 SVG/PNG；
中文字体明确查找，缺失硬失败。系统流程只表达步骤，不表达伪造性能。Slides 复用图表 PNG
（任务明确要求），所有标题、正文和必要数值为可编辑文本，流程用原生对象。

查看正式帧前先用 synthetic fixture 验证：win/loss/uncertain 均在指定 family 的 human_pair
中按 `(family,sample_id,trial_id,replicate,comparison_id)` 取首项；缺类显式 unavailable。
loss/uncertain 必须反查全部9条 D4 failure index。定性 sample 按 sample_id 取首项，展示该任务
全部5候选且按 candidate_id 排序，避免再挑候选。公共页仅“成功/失败/不确定/定性边界案例1”。

帧位置 first、1/3、2/3、last；索引为 floor((n−1)×position+0.5)，正式16帧得到0/5/10/15。
所有方法索引一致；只复制原帧像素，展示缩放保持比例。内部 trace 记录comparison、role、
candidate、媒体/帧SHA与索引，留在忽略 artifact。输出页面不复制逐题原答或评审信息。
病例只陈述正式聚合与范围，不凭单帧推断整段结论。

## 报告、Slides、讲稿

报告覆盖摘要、问题/范围、系统、指标/算法、盲评/聚合、主结果、一致性/BT、四类案例、
成本/复现、威胁、结论。图为system-flow、overall-ci、outcomes、agreement两种格式。
10页中文初稿顺序由配置固定：结论、范围、系统、指标、算法、盲评、结果、案例、局限、下一步。
Slides 使用 presentations skill 的 bundled Node @oai/artifact-tool，导出PPTX、finalizer校验、
重新导入最终PPTX逐页PNG渲染，保存layout、SHA和QA回执。全页contact sheet及逐页视觉检查。
没有可用 bundled LibreOffice时不启用桌面LibreOffice，也不承诺草稿PDF。

讲稿一页一节，中文有效字符与数字/英文词计数，260有效字符/分钟，静态总时长300–420秒。
数值必须是注册事实/协议常量引用，不加入新结论。录屏方案60–90秒，包括校验、盲评安全
展示、三方法选择、报告主表和故障降级；本阶段不录制或演练。

## 输出、验证和发布

先 fixture，再正式 `artifacts/defense_mvp/DEFENSE-MVP-D5-v01/`。整个根 staging 后no-replace，
失败保留诊断并使用v02，不覆盖v01。报告、表、图、案例trace、slide-data、输入/source manifest、
receipt、PPTX、渲染、contact-sheet、讲稿/录屏方案均在清单中。PPTX不宣称字节级重建，验证
其页数、文本、图像和语义及实际SHA；时间/平台隔离于receipt。D5 verification是阶段回执，
不实现D6顶层最终manifest。

测试矩阵覆盖：pin/status/cardinality/角色/媒体/unknown inventory；事实精度/单位/undefined；
叙事红线；SVG/PNG尺寸/字体/参考线/四类；案例排序扰动/缺类/方向/帧对齐/媒体SHA；
PPTX/10页渲染/讲稿时长/数值；no-replace/失败诊断/重建/tamper/source drift/链接/隐私。
最终源码运行D5、Defense、全仓pytest、compileall、CLI/config smoke、D3/D4/D5 verifier、
输入前后checksum、格式与视觉验收、git diff --check及staged路径/大小/NUL/敏感载荷守卫。

每个可验证开发/测试/失败/决策/运行步骤后立即写DEVLOG。正式媒体gate前完成fixture测试，
记录配置SHA、21个输入pin和下一条命令，先审计提交及普通push冻结实现。正式验收后生成D5
回执和总计划状态，只暂存显式allowlist。artifacts、媒体、PPTX/PDF、案例图、原答、tar/sidecar
均不提交。最终push回执允许是唯一未提交tracked增量。

## 冻结前工程验收补充

最终定向测试为49 passed，58.39秒；包含实际bundled PPTX生成/重新导入渲染、逐fact来源指针
核验、稳定文件跨路径重建、重新计算清单后的篡改拒绝和PPTX正文数字篡改拒绝。完整Defense
和最终全仓结果另随DEVLOG/实现回执记录，不能用定向数量替代。

本机bundled Artifact Tool为2.8.59，中文采用已验证Microsoft YaHei。没有可用bundled
LibreOffice，因此D5只交PPTX及逐页PNG，不额外引入PDF工作流。实际PPTX已通过skill finalizer
的package/layout/font/first-party import检查。它们不等于在桌面PowerPoint中实测。

bundled Windows canvas在输出全部渲染后有原生析构崩溃。工程保留了前三次synthetic失败，
最终采用显式完成握手：renderer写完并等待，父进程核验PPTX和全部PNG SHA后终止空闲辅助进程，
回执记录受控关闭策略和原始退出码；超时或缺文件硬失败。不得把异常退出自行忽略为成功。

整个成功D5根的SHA256SUMS固定覆盖所有生成文件。后续仅允许no-replace追加
`visual-qa.json`和`verification.json`阶段回执；独立verifier检查其内容身份且拒绝其他未登记
文件。视觉回执绑定具体PPTX和10张PNG，不能复用其他版本的验收。公开文档导出只改相对
链接，其余讲稿/表/图为字节副本，`d5_generated/public-export.json`保存生成关系。
