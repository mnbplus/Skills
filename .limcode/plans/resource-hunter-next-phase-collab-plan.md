## TODO LIST

<!-- LIMCODE_TODO_LIST_START -->
- [ ] M0：收口 clue/follow-up 通用语义与来源准入/fixture 模板  `#m0-semantic-baseline`
- [ ] M1：完成 PanSearch 接入可行性判定，并在满足条件时做低影响接入  `#m1-pansearch`
- [ ] M2：完成 Dalipan transport hardening，并把 detail/url 设计为可选增强  `#m2-dalipan-hardening`
- [ ] M3：补最小精度硬案例回归包，建立后续来源接入固定清单  `#m3-precision-and-admission`
- [ ] 发布前复核 changed source 的 fixture、有限 live probe、排序语义与兼容入口  `#release-gate-next-phase`
<!-- LIMCODE_TODO_LIST_END -->

# resource-hunter 下一阶段开发协作计划

## 来源文档 / 规划依据

本计划基于以下当前状态文档与本轮子agent分析整理：

- `skills/resource-hunter/STATUS.md`
- `skills/resource-hunter/NEXT_ACTION.md`
- `skills/resource-hunter/README.md`
- `skills/resource-hunter/SKILL.md`
- 本轮子agent输出：`项目理解专家`、`架构规划师`、`测试验收工程师`

## 目标

在**仅限 `skills/resource-hunter`**、**success-first retrieval 优先**、**不依赖官方 API / API key / 登录态** 的前提下，开启下一阶段开发，并把工作重心从“已完成的发布收口”切换到“半成熟高价值能力收口”。

本阶段优先目标：

1. 评估并推进 `PanSearch` 从研究证据走向诚实、低风险的运行时接入。
2. 加固 `Dalipan` 当前匿名搜索路径，并把 follow-up/detail 能力设计为可选增强，而不是主流程前置依赖。
3. 为同名异年等硬案例补一组最小精度回归，避免扩源后把 `clue` 结果抬得过高。
4. 建立后续“一条条探测、一条条接入”的来源准入与验收模板，降低扩源时的回归风险。

## 非目标

以下内容不在本阶段主线内：

- monorepo 范围清理或统一改造
- 大规模重写 `engine.py` 或重构成全新插件系统
- 依赖 cookie、登录、官方 API、私有 key 的来源接入
- 在证据不足时把 `PanSearch` / `Dalipan` 包装成直链型 direct source
- 为了来源数量而集成高摩擦、强反爬、纯壳站、长期不稳定来源

## 子agent分工结论摘要

### 1. 项目理解 / 产品推进
- 当前最值得优先收口的不是继续撒网式扩源，而是两个“已证明确有产出但还未成熟”的点：
  - `PanSearch`
  - `Dalipan`
- 推荐顺序：
  1. `PanSearch` 接入评估与收口
  2. `Dalipan` follow-up / transport hardening
  3. 精度硬案例补强
  4. 再继续逐个探测新来源
  5. 最后再做 artifacts 展示噪音清理

### 2. 架构 / 实施路线
- 保持现有主干结构稳定：`intent.py` / `engine.py` / `adapters.py` / `ranking.py` / `rendering.py`
- 不为了新来源重写引擎，而是把来源复杂度关进来源自己的边界里。
- 推荐把复杂来源按三段处理：
  - transport / fetch
  - parser
  - normalizer
- 结果语义应尽量由结果字段驱动，而不是继续堆 `if source == ...` 特判。

### 3. 测试 / 验收
- 下一阶段不能只靠 live probe；要把关键站点行为固化成 fixture / 离线样本。
- 关键发布阻断项：
  - direct/actionable/clue 语义不回归
  - 单源失败不能拖垮整批
  - 不越过“无登录 / 无 key / 无官方 API”边界
  - changed source 必须做有限 live probe

## 总体执行策略

采用“**小步增强 + 明确决策门 + 可回滚接入**”路线：

- 先固化通用 clue/follow-up 语义和测试基线
- 再做 `PanSearch` 的影子接入 / 低影响接入
- 然后做 `Dalipan` 的 transport hardening 和可选 follow-up
- 最后补精度包与来源准入模板

推荐按 4 个里程碑执行，每个里程碑都具备：

- 明确目标
- 固定改动区域
- 对应测试层
- 回滚点
- Go / No-Go 判定

---

## 里程碑 M0：语义基线与验收模板收口

### 目标

在引入新来源前，先把“需要 follow-up 的结果”语义与测试基线收紧，避免 `Dalipan`、未来 `PanSearch`、未来 clue 来源持续新增 source-specific 特判。

### 主要任务

1. 梳理当前 `Dalipan` clue 语义落点：
   - `raw["delivery"]`
   - `raw["retrieval_role"]`
   - `raw["requires_follow_up"]`
2. 评估是否可把 `ranking.py` / `rendering.py` 中的来源特判逐步转向结果语义驱动。
3. 为 `PanSearch`、`Dalipan`、未来来源接入建立统一准入模板：
   - public / anonymous / no-login / no-key
   - 是否有稳定 canonical 字段或诚实 clue 字段
   - success / empty / blocked-or-drift 三类样本是否齐全
4. 规划 fixture 存放方式，区分：
   - durable fixture
   - 一次性 live probe artifact

### 涉及文件区域

- `skills/resource-hunter/src/resource_hunter/ranking.py`
- `skills/resource-hunter/src/resource_hunter/rendering.py`
- `skills/resource-hunter/tests/`
- `skills/resource-hunter/references/architecture.md`
- `skills/resource-hunter/references/sources.md`
- 如需新增准入/验收说明，可补充到 `references/usage.md`

### 测试策略

- 扩充/整理：
  - `tests/test_results.py`
  - `tests/test_precision.py`
  - `tests/test_source_expansion.py`
  - 必要时补 `tests/test_cli.py` 的 text/json 语义断言
- 重点验证：
  - `direct > actionable > clue` 不回归
  - token-only / follow-up-required 结果不会被误渲染成 final share URL

### 回滚点

- 仅回滚通用语义映射与渲染层调整
- 不涉及来源注册和主调度逻辑

### Go / No-Go

- Go：可以用结果语义统一表达 clue/follow-up 行为，且现有回归全绿
- No-Go：若抽象后导致大量 `source` 兼容破坏，则只保留最小文档与测试模板，延后通用化

---

## 里程碑 M1：PanSearch 影子接入与低影响上线判定

### 目标

验证 `PanSearch` 是否具备进入 runtime 的最低条件：不是“看起来有内容卡片”，而是能稳定提取**可发布的 canonical 字段**，或者至少能输出诚实且有价值的 clue 结果。

### 关键原则

- 优先使用稳定数据层，而不是 fragile DOM：
  1. `__NEXT_DATA__`
  2. `/_next/data/.../search.json`
  3. 最后才考虑页面卡片 DOM
- 查询参数以已验证的 `keyword=` 为准，不再默认按 `q=` 假设成功
- 如果拿不到稳定 canonical share 字段，不能把 `PanSearch` 包装成 direct source

### 主要任务

1. 固化 `PanSearch` 搜索契约：
   - 搜索参数
   - 数据入口
   - payload 主要字段位置
2. 设计内部边界：
   - transport/fetch
   - parser
   - normalizer
3. 提取可进入统一 `SearchResult` 的字段：
   - title
   - provider/source hint
   - detail path 或 canonical link
   - 可能的 clue 辅助字段
4. 增加“单条 follow-up 失败隔离”策略：
   - detail follow-up 单条失败不能拖垮整批结果
5. 按低影响方式接入：
   - 低优先级
   - 低预算
   - 默认不压过成熟 direct source
6. 设定 time-box 决策门：
   - 若稳定 canonical share 字段无法提取，则不进入默认 runtime，仅保留研究结果和测试证据

### 涉及文件区域

推荐优先考虑以下两种实现之一：

- 方案 A（推荐）：新增来源侧边文件，如 `src/resource_hunter/pansearch_source.py`
- 方案 B（保守）：先在 `src/resource_hunter/adapters.py` 中明确划分 `PanSearch` 专区

同时涉及：

- `skills/resource-hunter/src/resource_hunter/adapters.py` 或新的 `pansearch_source.py`
- `skills/resource-hunter/src/resource_hunter/engine.py`
- `skills/resource-hunter/src/resource_hunter/intent.py`
- `skills/resource-hunter/src/resource_hunter/retrieval_layers.py`
- `skills/resource-hunter/src/resource_hunter/common.py`
- `skills/resource-hunter/src/resource_hunter/core.py`
- `skills/resource-hunter/src/resource_hunter/precision_core.py`
- `skills/resource-hunter/tests/test_source_expansion.py`
- 必要时：`tests/test_results.py` / `tests/test_precision.py`
- 文档：`references/sources.md`、`references/architecture.md`、`README.md`（若真的上线）

### 测试策略

最小验收清单：

1. 正确参数 `keyword=` 可出样本结果
2. `__NEXT_DATA__` 解析成功
3. `_next/data` fallback 可用或已明确弃用原因
4. 缺字段 / 漂移 / 空结果时安全降级
5. follow-up 单条失败不拖垮整个 source batch
6. clue 结果不会在排序上压过成熟 direct source
7. text / JSON 输出中语义清楚，不误导用户
8. changed source 做有限 live probe

### 回滚点

- 直接取消 `engine.py` / `intent.py` / `retrieval_layers.py` 中的注册
- 保留 parser 代码但不启用
- 如涉及缓存语义变化，需同步评估 cache schema/version 回退方案

### Go / No-Go

- Go：稳定拿到 canonical 字段，或至少能稳定产出诚实 clue，且不扰乱 success-first 排序
- No-Go：只有内容卡片文本、没有稳定字段、无法诚实接入，则继续放在 research evidence，不进入默认 runtime

---

## 里程碑 M2：Dalipan transport hardening 与可选 follow-up

### 目标

把 `Dalipan` 从“可搜但 token-only”阶段推进到“更稳、更诚实、更好维护”的状态；重点不是强行升级为直链，而是先把公共搜索和后续解析彻底解耦。

### 关键原则

- public search 成功 ≠ detail/url 必须成功
- detail/url 应该是 optional enhancement，不应成为热路径硬依赖
- 若匿名 final-link 仍不可验证，应继续保持 `clue-only` 语义
- 不为上线而依赖默认关闭 TLS 校验或其他不安全绕过

### 主要任务

1. 拆分 Dalipan 内部能力边界：
   - public search
   - optional detail resolver
   - optional final-url resolver
2. 明确 transport hardening 范围：
   - headers / timeout / JSON decode / 受限响应识别 / SSL 失败策略
3. 把 detail/url 失败视为“能力受限”，而不是 source 整体不可用
4. 如匿名 final-link 可行，补充严格升级条件；如不可行，则继续稳态 clue-only
5. 在 ranking/rendering 中用结果语义表达状态，而不是持续追加来源名字特判

### 涉及文件区域

推荐优先考虑以下两种实现之一：

- 方案 A（推荐）：新增来源侧边文件，如 `src/resource_hunter/dalipan_source.py`
- 方案 B（保守）：继续在 `adapters.py` 内分区，但逻辑明确拆段

同时涉及：

- `skills/resource-hunter/src/resource_hunter/adapters.py` 或新的 `dalipan_source.py`
- `skills/resource-hunter/src/resource_hunter/ranking.py`
- `skills/resource-hunter/src/resource_hunter/rendering.py`
- `skills/resource-hunter/src/resource_hunter/engine.py`
- 如需更细错误分类，可评估 `skills/resource-hunter/src/resource_hunter/errors.py`
- 若 follow-up 结果需要缓存，再评估 `skills/resource-hunter/src/resource_hunter/cache.py`
- `skills/resource-hunter/tests/test_source_expansion.py`
- 视情况补充 `tests/test_results.py` / `tests/test_precision.py`
- 文档：`references/sources.md`、`references/architecture.md`、`README.md`

### 测试策略

最小验收清单：

1. public search 基线不回退
2. detail/url 受限时仅降级，不导致整源失败
3. 单条 follow-up 失败隔离成立
4. token-only 仍被标记为 `clue`
5. 只有真实匿名 final-link 成功样本满足条件时，才允许升级为 `actionable` / `direct`
6. changed source 做有限 live probe
7. 不依赖不安全的默认 TLS 绕过

### 回滚点

- 回退到当前稳定态：public search + token-only clue 输出
- 保留后续 resolver 边界但默认关闭

### Go / No-Go

- Go：transport 更稳，detail/url 失败不污染主流程，且 clue/direct 语义仍诚实
- No-Go：若为了打通 final-link 需要不安全或高摩擦路径，则停止升级，只保留现有 clue-only 路线

---

## 里程碑 M3：硬案例精度补强 + 来源准入流水线

### 目标

在完成高价值半成熟来源收口后，补一组最小精度包，并把未来来源接入变成更机械化、更低风险的流程。

### 主要任务

1. 选取硬案例建立最小回归包：
   - `The Merry Widow 1952`
   - 其他已知同名异年或语言别名案例
2. 复核扩源后排序/证据融合边界：
   - clue 不应压过 direct
   - 错年份不应被热度或来源数抬高
3. 形成来源接入固定清单：
   - 允许改动的固定落点
   - fixture 三件套要求
   - live probe 最小要求
   - 文档同步要求
4. 继续 one-by-one 探测新来源，但只纳入满足准入门槛的对象

### 涉及文件区域

- `skills/resource-hunter/tests/test_precision.py`
- `skills/resource-hunter/tests/test_results.py`
- `skills/resource-hunter/tests/test_intent.py`（如 source planning/budget 有调整）
- `skills/resource-hunter/references/architecture.md`
- `skills/resource-hunter/references/sources.md`
- `skills/resource-hunter/references/usage.md`
- 研究证据与长期保留样本的边界说明，可落到 `artifacts/live-tests/README.md`

### 测试策略

建议固定一组代表查询作为发布前回归基线：

- `Oppenheimer 2023 --4k`
- `Breaking Bad S01E01`
- `进击的巨人 Attack on Titan --anime --sub`
- `The Merry Widow 1952`
- 至少一个中文 alias / 旧片歧义案例

### 回滚点

- 回滚精度规则增量
- 对新来源只撤注册与优先级，不动引擎主干

### Go / No-Go

- Go：回归样本稳定、排序不回退、来源接入模板能减少未来扩源的非结构化改动
- No-Go：若精度补强导致整体召回明显倒退，则只保留问题样本与文档，延后规则增强

---

## 建议的 PR / 执行切分

### PR-1：语义基线与测试模板
- 目标：统一 follow-up/clue 语义表达，补准入模板与 fixture 方向
- 风险：低
- 回滚：容易

### PR-2：PanSearch 决策型接入
- 目标：完成可接入性判定；若满足条件再做低影响上线
- 风险：中
- 回滚：取消注册即可

### PR-3：Dalipan hardening
- 目标：search 稳定性提升，detail/url 完全可选化
- 风险：中高
- 回滚：恢复 token-only 稳定态

### PR-4：精度包 + 来源准入流水线
- 目标：把下一轮扩源变成标准动作，而不是临时 patch
- 风险：中
- 回滚：撤销个别规则与文档即可

---

## 发布前必过项

以下任一项不满足，则该阶段不应对外宣称完成：

1. 现有核心回归集继续全绿
2. 新增/强化来源具备 success / empty / blocked-or-drift 三类样本
3. 单源失败、单条 detail 失败不会拖垮整批结果
4. `direct > actionable > clue` 不回归
5. text / JSON 契约清楚，不误导用户把 placeholder 当 final URL
6. 不触碰登录态、私钥、官方 API 等硬边界
7. changed source 完成有限 live probe
8. `PanSearch` / `Dalipan` 的上线语义与真实能力完全一致

## 风险与应对

### 风险 1：PanSearch 只有卡片，没有稳定 canonical 字段
- 应对：time-box 后果断 No-Go，不强行集成

### 风险 2：Dalipan final-link 长期不是匿名能力
- 应对：停止“直链化执念”，继续稳定 clue-only 路线

### 风险 3：来源特判继续扩散到 ranking/rendering
- 应对：优先以结果语义字段表达，而非继续堆 source-name 特判

### 风险 4：live probe 证据过多、fixture 过少
- 应对：把 durable 样本沉淀为测试资产，把临时 probe 保持为研究材料

### 风险 5：扩源影响旧入口兼容
- 应对：所有执行阶段都必须复核：
  - `scripts/hunt.py`
  - `core.py`
  - `precision_core.py`
  - CLI / packaging / runtime 基线

## 执行顺序结论

推荐按以下顺序推进：

1. **M0 语义基线与准入模板**
2. **M1 PanSearch 决策型接入**
3. **M2 Dalipan hardening**
4. **M3 精度包与来源准入流水线**
5. 再进入下一轮 one-by-one 新来源扩展

这个顺序的核心理由是：

- 先控住语义和测试基线
- 再收口高价值半成熟来源
- 最后再继续扩源

避免“来源越多、结果越花、维护越乱”的失控路径。
