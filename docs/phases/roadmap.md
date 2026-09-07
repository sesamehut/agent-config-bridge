# 路线图

## 当前状态

实现阶段已经完成 M1（源树声明与只读哨兵）、M2（技能投射与采纳）和
M3（入口与规则投射）。M4（钩子意图与双侧投射）正在收口：设计已定稿、契约 tuple
已整体升版，规范、机械层与夹具均已落地，收口计数记录在 M4 小节。产品产物继续按
[分发模型](../implementation/distribution-model.md)声明的目录落地；CLI、npm
package、插件清单与插件制品仍门控到 M5，CI 门禁仍是 M6 工作。

当前契约是
[`covenant/v3`](../../templates/covenant/README.md)、
[`source-tree/v5`](../../skills/bridge-sentinel/references/source-tree-spec.md)、
[`report/v5`](../../skills/bridge-sentinel/references/report-spec.md)、
[`reconciliation/v3`](../../skills/bridge-sync/references/reconciliation-spec.md)
与 [`sync-plan/v3`](../../skills/bridge-sync/references/sync-plan-spec.md)。它直接
替换上一版 runtime contract，不提供双读或隐式兼容路径；归档的 covenant v1 与 v2
bytes 组成封闭两成员集合，各自一跳迁移到当前 tuple，只用于识别一次显式
closed-set ownership migration。v2→v3 迁移永不携带 hooks unit，因为
`reconciliation/v2` 禁止一切 hook 写入，没有可达的 v2 时代 commit 能证明 hook
baseline。

M3 已交付：

- `bridge-sync` 的 empty / Claude / Codex 三种 onboarding 起点与逐 unit 决策；
- v1→v2 migration 对 reachable legacy-owned set 做闭合集 carry / repair / release，
  并在所需 Git transition commit 可达前保持
  `migration-transition-uncommitted`；
- entry 与 rule shard 的确定性 render、origin-map reverse adoption、`pv2`
  applicability preamble，以及歧义变更的 `semantic-review-required` 审阅；
- Units / Closures 的稳定 closure id、selected / not-selected、逐 closure
  authorization 与依赖闭合；Write capabilities 按 path 序列化 forward / inverse
  protocol，partial batch 必须直接进入序列化计划；
- migration 的独立 candidate table 按 unit 列出全部 ancestry-maximal legacy OID，
  ambiguous history 不再压缩成任意单个 baseline；
- root `AGENTS.md` 的单一 desired full-file image、manual-zone planned-byte
  protection、strict 或显式非 CAS 的 `guarded-patch/v1` exact-region 流程，以及
  source-first / carrier-last 顺序；create/delete/rename 与 compensation 仍只接受
  strict capability，不承诺跨文件事务；
- root discovery、override / fallback、budget、marker、rule paths、active import
  与未知 live activation input 等封闭 apply blockers，以及只在同一 live operation
  开放的 journal / compensation 生命周期。

M3 的隔离 fixture contract、真实 agent workflow replay、formal skill validator、
相对链接、docs inventory、twin-file、tuple 一致性与独立发布审计均已通过。写后
仍只要求用户在 fresh Codex run/session 验证 activation；这些仓库证据不声称
Claude Code / Codex live host 已发现或加载当前技能，也不把当前 session 的实现
观察当成 reload contract。

M2 收口时落地了四组边界明确的交付物；下列 v1/v3 名称是历史里程碑证据，
不表示当前 runtime 仍读取旧契约：

- `bridge-sentinel` 保持严格只读，并在 M2 收口于 `source-tree/v3` 与
  `report/v3`；
- `bridge-sync` 作为独立写侧入口，在 M2 以 `reconciliation/v1` 与
  `sync-plan/v1` 实现技能面的 Git baseline 仲裁、完整计划、确认、落盘与写后验证；
- `covenant/v1` 用 tracked、immutable 的 source half 与 `AGENTS.md` managed
  block 建立 versioned onboarding anchor；其 exact bytes 现只在
  [`templates/covenant/v1/`](../../templates/covenant/v1/)保留为 migration
  evidence；
- [`fixtures/m2-sync/`](../../fixtures/m2-sync/README.md) 提供 13 个隔离场景与
  22 项轻量 safeguards，覆盖正常投射、反向采纳、冲突、未知占用、路径与 mode
  护栏、DAG 歧义、失败边界和 covenant 生命周期。

13 个场景是 `baseline-dag-ambiguous`、`behavior-degraded`、
`conflict-zero-write`、`covenant-bootstrap`、`covenant-partial-blocked`、
`create-rerun`、`manual-copy-decision`、`multi-unit-batch`、
`occupied-and-links`、`projection-adopt`、`source-reproject`、
`untracked-ignore` 与 `write-verify-failure`。

### M2 检查命令与证据边界

仓库内稳定、可复现的机械检查不依赖构建或打包工具：

```text
python -B skills/bridge-sentinel/scripts/sentinel_mechanics.py self-test
python -B fixtures/m2-sync/fixture_harness.py self-test
git diff --check
```

第一条验证 Sentinel 的 normalization、diff shape、tree / mode inspection 与
expectation comparison。第二条验证全部 13 个 `bridge-sync-scenario/v1` 定义、
expected plans、post-state trees 和 22 项 safeguards；它是 fixture contract
self-test，不冒充 Bridge workflow 的执行结果。

本工作单元还对其中 12 个 agent-replayable 场景执行了真实 `bridge-sync` workflow
回放：transition 组 6/6 场景通过，7/7 次 plan + post-tree comparison 通过；
guard 组 7/7 branches 通过；`baseline-dag-ambiguous` 另行回放通过。
`write-verify-failure` 是唯一 declarative-only 场景，因为它要求在写入与验证之间
注入故障；其 plan、失败 post-state、fault checkpoint 和 fail-reviewably 约束由
fixture self-test 与 safeguards 验证，不能表述成已执行的 fault-injection smoke。

完整检查清单还包括：

- 两个 formal skill 均通过当前 Codex bundled validator，且
  `agents/openai.yaml` 满足界面字段约束；
- 仓库 JSON 可解析、markdown 相对链接可达、docs inventory 与目录一致；
- `CLAUDE.md` / `AGENTS.md` 保持镜像，covenant source / render bytes 与版本 tuple
  一致；
- 没有残留临时 `bridge-sync-*` worktree、nested `.git`、`__pycache__` 或越过
  milestone 的生成物。

这些证据验证的是仓库载体和 agent workflow。尚未执行 Claude Code / Codex live
host discovery 或 activation smoke；repo bytes 不能证明当前 host session 已加载
技能。

进入 M5 / M6 后，这份清单固化为发布前验证命令与 CI 门禁。

路线图按风险递增推进：先定稿源树声明、行为约定和保真度分类，做只读的哨兵与同步
计划；再从技能这种原生等价配置面开始落盘；随后处理规则与钩子投射，最后打包
分发。

## M1：源树声明与只读哨兵（已完成）

M1 是只读阶段。目标是确定源树形状、行为约定文本和报告口径，让后续落盘建立在
清楚的输入和分类规则上。

已交付：

- 定稿源树布局与条目约定（markdown + frontmatter 加目录约定，含意图记录）。
- 起草注入两个 host 的行为约定文本：两侧同构，常驻指令加 hook 提醒。
- 起草哨兵检查流程与同步计划报告格式（含保真档位）。
- 起草工具映射知识的初始结构（带采集日期）。

完成标准（已满足）：

- 能扫描一个示例项目，报告源树与各投射面的一致性状态。
- 报告状态集封闭，与 [report-spec](../../skills/bridge-sentinel/references/report-spec.md)
  的口径一一对应，夹具比对按该口径逐一验收。
- 没有落盘能力；所有结果只停留在报告与同步计划。

## M2：技能投射与采纳（原生等价档，已完成）

技能是第一块落盘配置面。目录结构清楚，Claude Code 和 Codex 都消费 `SKILL.md`，
适合验证快路径、文件集所有权和哨兵比对。

已交付：

- 技能母本到 Codex 项目级技能目录（`.agents/skills/`）的 complete-tree 投射。
- 快路径在技能面落地：编辑母本后，同一 confirmed work unit 内更新副本并做
  mechanical compare 与 scoped Git checks。
- 写侧仲裁从 `HEAD` 可达 Git DAG 逐 unit 重建 provable baseline；无歧义时采纳或
  重投射，两侧自同一 baseline 携带不同新意图时报告 conflict 并保持该 closure
  零写。
- 未知占用、无 baseline 副本、delete / rename、untracked / ignored、mode 与 path
  safety、部分批次、同一 live operation 失败补偿和后续独立 reverse-operation
  边界均进入完整计划与显式确认。

完成标准（已满足）：

- 用户只维护 `.claude/skills/` canonical tree；Bridge 生成 byte / mode
  可保真的 `.agents/skills/` carrier。是否已被 live host 发现仍需 fresh session
  或 restart 后另行验证。
- 看似人工维护的既有副本不被覆盖，Sync 停下来问 `annex` 还是 `keep`；`keep`
  不伪装成同步成功。
- 副本与母本自同一 proven baseline 同时携带不同新意图时报告 `conflict`，该 unit
  与依赖 closure 零写。
- source-only projection、proven projection-only adoption、no-baseline duplicate、
  delete / rename、untracked / ignored、path / mode safety、unrelated dirty
  preservation 与 failure reviewability 都有代表性 fixture contract；除明确标注的
  fault-injection 场景外，均有 agent replay 证据。

## M3：入口与规则投射（结构 / 语义降级档，已完成）

规则在技能之后处理，因为它开始涉及降级投射与 LLM 语义映射。

已交付：

- `CLAUDE.md` 共享内容与 `.claude/rules/` 分片投射进 `AGENTS.md` 受管区块。
- 受管区块直接改动的反向采纳。
- path-scoped 分片的适用性前言渲染。
- host 自指内容的投射改写约定；Claude-only 段落的注释标记。
- 三种起点的引导流程，重点是 Codex 起点：既有 `AGENTS.md` 收编为源树。
- M3 fixture matrix 已覆盖三起点、render/adopt round trip、manual-zone
  planned-image / guarded 证据与 strict capability gate、activation blockers、
  closed-set migration、closure
  authorization、DAG 冲突与 compensation unavailable。guarded final-preflight
  mismatch 另有 fixture-only 的独立进程 `arm-fault` / `apply-fault`、一次性
  receipt、完整树与零 Bridge 写验证；POSIX root-child target mutation 在缺少
  当前名称到 retained leaf 的绑定证明时仍是 declarative-only，并须在 mutation
  前 fail closed。Windows 能力继续按独立 platform attestation 判定，不因 POSIX
  限制而漂移。fixture-only adapter 证据与真实 `bridge-sync` workflow 回放结果
  在验收中分别记录。

投射与反向采纳的机制细节见[同步模型](../implementation/sync-model.md)。

### M3 检查命令与证据边界

稳定、可复现的仓库内检查为：

```text
python -B skills/bridge-sentinel/scripts/sentinel_mechanics.py self-test
python -B fixtures/m2-sync/fixture_harness.py self-test
python -B fixtures/m3-rules/fixture_harness.py self-test
python -B fixtures/m3-rules/journal_validator_tests.py --mode worker-matrix
python -B fixtures/m3-rules/journal_validator_tests.py --mode single
python -B fixtures/m3-rules/journal_validator_tests.py --mode concurrent
git diff --check
```

最终证据计数如下：

- M1 Sentinel self-test 为 36 checks；
- M2 为 13 definitions、12 agent-replayable、1 declarative-only 与 22
  safeguards；
- M3 matrix 为 41 scenarios、42 expectations 与 42 replay inputs；其中 39 个
  agent-replayable scenarios、40 个 replay inputs 已全部完成真实 workflow
  回放，`guarded-postverify-race` 与 `verify-failure-no-compensation` 两个场景
  保持 declarative-only；
- M3 main harness 为 809 checks：28 adapter、1 journal-suite gate、737 other
  contract checks 与 43 stale-recovery checks；
- journal worker matrix 为 11/11，single suite 为 66/66；concurrent gate 为
  2 workers、132 cases、2 unique session roots 与 2 successful cleanups。最终
  独立连续三轮 concurrent gate 都在首轮通过，没有 retry。

main harness 验证声明、受租约约束的 materialization、expected plan / exact tree、
adapter 与 journal contract，不执行 `bridge-sync`。39/39 scenarios 与 40/40
inputs 的真实 agent replay 是另一层独立证据；两类证据不得互相冒充。

平台能力边界保持显式：

- Windows fixture adapter 只在 retained handle / current name 证明成立时执行
  same-mode guarded-preflight mutation；mode change 在所有平台仍是
  declarative-only。
- POSIX retained root / leaf handles 不能把当前 root-child name 与 retained leaf
  绑定到同一 mutation，因此对应 target mutation 只验证声明，并在写目标前
  fail closed；该结论不外推为 Windows capability。
- Windows journal validator 可以保留 authority read，但当前不能证明
  handle-relative delete 与 cleanup revalidation，因此 product journal cleanup
  receipt 按设计 fail closed。测试进程对自身 exact session root 的 teardown
  与 concurrent gate 的 2/2 cleanup 是独立的 fixture-owned 边界，不能表述成
  product cleanup capability。
- M3 没有声称 executable physical strict delete。首个未来的 pre-untracked
  strict-delete 或 rename-delete 场景必须先从 authenticated payload 构造并绑定
  synthetic pre-worktree，再开放执行。

完成标准（已满足）：

- 共享规则只维护一份，并已投射、验证到两侧项目载体；作用域语义在 Codex 以
  适用性前言保留。live host discovery / activation 仍需后续集成验证。
- 手改 `AGENTS.md` 受管区块的内容能正确回到对应源分片，两侧重新一致。
- `AGENTS.md` 写入以完整 planned image 逐字节携带受管区块外的 manual zone；
  strict path 只有在完整 expected preimage 与 mutation 由同一原语绑定时才声称
  `manual-zone-preserved`，guarded path 必须报告
  `manual-zone-guarded` / `guarded-patch-non-cas` 及 host call 内的 residual race。
- Codex 起点项目可经逐段确认完成收编，无静默覆盖。

## M4：钩子意图与双侧投射（进行中）

钩子放在更后面，因为风险主要来自执行语义：触发时机、环境变量、权限和失败处理
在两个工具中都可能不同。2026-09-07 的设计定稿把这些差异全部落到可序列化的字段与
封闭 token 上，而不是散文承诺。

要完成：

- 定稿钩子意图文档模型：单元身份 `hooks/<entry-id>/{source,claude,codex}`、必填
  `class`、`enabled-by` 启用记录、per-target override 与 `override-reason`，以及
  文件级 `bridge:hooks-shared-execution` 确认注释。机制见
  [同步模型](../implementation/sync-model.md)钩子一节。
- Claude 侧投射到 `.claude/settings.json` 声明键；Codex 侧投射到
  `.codex/hooks.json` 声明键。两者的 postimage 由 `json-owned-span/v1` 求得：只
  编辑 owned span、数组只追加、语义相等即零写，规则见
  [写入协议 ADR](../architecture/write-protocol.md)。
- 超出目标侧 hooks 承载面的 `reminder` / `observation` 意图降级为常驻指令：Codex
  落到 root `AGENTS.md` 受管区块，Claude 落到意图文档自身（零写入）；`gate` 与
  `side-effect` 永不降级。
- 读侧 `report/v5` 补齐 hooks 决策表的散文面 H-case、外来 handler 与语义分歧
  case、`AGENTS.md` 孤儿降级块 case、新观察项与注记，并加上 Claude 与 Codex 两条
  runtime hedge。
- 写侧 `reconciliation/v3` 与 `sync-plan/v3` 补齐 hooks snapshot、baseline 取值、
  reconciliation 表、反向采纳规则、closure 与步骤顺序、封闭 warning 与
  apply-blocker registry，以及 `## Hook tiers`、`## Hook adoption decisions`
  两张表。
- 机械层新增七个封闭语法子命令（carrier 检视、span 定位、组渲染、整文件合成、
  意图扫描、handler 比较、降级渲染）并自检幂等律；夹具新增 `fixtures/m4-hooks/`
  场景矩阵与只读 H-case 项目，并把全部夹具 hook 命令换成不可执行的 no-op 围栏。
- 按 2026-09-07 复核改写映射知识：事件集与 Codex 独有 `Interrupt`、timeout 边界、
  handler 类型、trust identity 与状态落点、两个 host 的 Windows shell、matcher
  语法、exit code 与 stdout 交付语义（逐项清单见
  [Codex 能力面核验](../research/codex-capability-surface.md)）。
- Codex 项目级 hooks 的信任加载与逐 hook 重新信任：源码层已核验 trust identity
  的字段构成、`[hooks.state."<key>"]` 写入用户 `config.toml` 的位置化 key，以及
  未信任 hook 在 `codex exec` 中被静默跳过、加 bypass 标志才运行；仍缺一次交互式
  `/hooks` TUI 会话，用来验证「首次信任后无 bypass 也能运行、改动字段后变为
  Modified」的完整流程并现场确认状态落点。该项完成前不得作为实现依据。

完成标准：

- 高副作用钩子默认要求显式启用：`class` 为 `gate` / `side-effect` 且
  `enabled: true` 而缺少覆盖当前命令的 `enabled-by` 记录时，计划只给出零写
  decision closure，并被 hook opt-in gate 拦住。
- 声明不同步以独立状态呈现：`declared-unsynced` 同时进入计划的 state registry 与
  tier registry，不退化成 warning 或 `unchanged`。
- 同步计划能解释每个钩子在两个工具上的档位与理由：`## Hook tiers` 逐 unit 序列化
  class、surface、tier 与封闭 reason token，行集与 Units 表完全一致。
- 提交进仓库的 hook 会在每个 clone 上运行这一事实，在 covenant、计划 Evidence 与
  报告 hedge 中都按 byte-pinned 文本出现；Bridge 的分类是评审元数据而不是沙箱。
- 已收敛的 carrier 重新规划为零写：整棵树逐字节不变，两张 capability 表都是
  `- (none)`，只发信息性 `hook-format-preserved`。

明确推迟到后续里程碑或后续决策：

- 读取 Codex 逐 hook 信任状态 `[hooks.state."<key>"]`。写入文件已在源码层定位到
  用户 `config.toml`，但装机上尚未观察到真实写入；M4 只读项目信任这一有文档、可
  实测且改变同一批决策的信号。
- 在本仓库自身 carrier 上 dogfood 真实 hook：Claude 通常会在维护者自己的会话中途
  装载它（官方只承诺“通常被捕获”，并记录了漏捕后需重启的失败模式），三面示例
  覆盖改由 M6 的独立示例项目承担。
- Claude 的 `args` exec 形态、`mcp_tool` 作为第二种共享原生 handler 类型、
  `.codex/config.toml` 内联 `[hooks]` 与 `.claude/settings.local.json` 作为写目标、
  跨设置层重复执行的去重、skill / subagent frontmatter hooks、企业 managed hooks
  键，以及跨 carrier 原子性。这些要么会把写面扩进本仓库读不到的域，要么需要先补
  一次逐字复核。

### M4 检查命令与证据边界

M4 收口后稳定、可复现的仓库内检查为（下列各条均已可运行，计数取自同一轮完整
执行）：

```text
python -B skills/bridge-sentinel/scripts/sentinel_mechanics.py self-test
python -B fixtures/m2-sync/fixture_harness.py self-test
python -B fixtures/m3-rules/fixture_harness.py self-test
python -B fixtures/m3-rules/journal_validator_tests.py --mode worker-matrix
python -B fixtures/m3-rules/journal_validator_tests.py --mode single
python -B fixtures/m3-rules/journal_validator_tests.py --mode concurrent
python -B fixtures/m4-hooks/hooks_harness.py self-test
python -B fixtures/m4-hooks/hooks_harness.py check-hook-fence
git diff --check
```

M1 到 M3 的既有检查命令与计数全部保留在上面各自小节，不因 M4 重新基线化。M4 的
证据计数如下：

- M4 matrix 为 26 scenarios、27 expectations 与 27 replay inputs。两侧拆分单独
  记录：scenarios 拆成 25 个 agent-replayable 与 1 个 declarative-only
  （`partial-two-carrier`），replay inputs 拆成 26 个 agent 与 1 个
  declarative-only。`hooks_harness.py self-test` 为 281 checks，accounting 是
  plan 108、replay 108、cleanup 27、contracts 26、fence 8、routing 3 与
  matrix 1；另有 36 safeguards 与 27 coverage tokens；
- 加入七个 hooks 子命令后的 Sentinel self-test 为 63 checks；M1 收口记录的
  36 checks 仍作为里程碑证据保留，不重新基线化；
- M3 main harness 在 plan 文法扩展到 `sync-plan/v3` 后为 868 checks，等于 M3
  收口的 809 checks 加上两组显式新增检查：`_exercise_hook_section_contract`
  贡献 54 项 hook-section 检查（含 hook decision shape 与 carrier trust
  annotation timing 两个子组），`_formal_adversarial_plans` 为
  `## Hook tiers` / `## Hook adoption decisions` 增加 5 项 adversarial 拒绝
  （section missing、section misplaced、invented tier row、adoption file
  order、adoption carrier order）。accounting 为 adapter 28、
  hook_sections 54、stale_recovery 43、journal_suite_gate 1 与 other 742；
  adapter、stale_recovery 与 journal_suite_gate 逐项不变，other 只由上面
  5 项从 737 增长；
- journal 三条命令按 M3 小节的口径重跑，结果一致：worker matrix 11/11，single
  suite 66/66（22 个 failure id，session cleanup 通过），concurrent gate 为
  2 workers、132 cases（66 cases/worker）、2 unique session roots 与
  2 successful cleanups；
- `check-hook-fence` 对整棵夹具树断言每个 `command` / `commandWindows` 都匹配
  `^bridge-fixture-noop( [a-z0-9-]+)?$`：结构化扫描覆盖 173 个 carrier 文件、
  134 个值，byte-level 兜底扫描覆盖同样 173 个文件、139 个值（含不可解析的
  `fixtures/hooks-broken-json/.codex/hooks.json` 中的 2 个值），violations
  为 0。夹具 hook 永不执行，`--dangerously-bypass-hook-trust` 不出现在任何
  夹具或 CI 路径中。

证据边界：

- `bridge-live-operation-journal/v2` 按引用绑定，不由 M4 套件重新证明：M4
  self-test 以 `journal_binding: by-reference` 声明这一点，只断言所引用的契约
  token，journal 本身的证据仍由 M3 小节的三条 journal 命令承担。它的
  path-operations 字段与路径种类无关，`json-owned-span/v1` 没有新增 journal
  字段。
- 平台边界：Codex 在 Windows 上用 pwsh 执行 `commandWindows`，Claude 在同一台
  机器上用 bash（Git Bash）执行 `command`，因此共享命令必须在两种 shell 下都
  成立，否则条目必须带 per-host 分支。
- hook 是否真的执行属于观察结果而非保证（2026-09-07 有 1/7 次 `codex exec` 未触发
  任何 hook，原因不明）。任何 Bridge 状态都不得读作运行期保证。
- 上述检查验证的仍是仓库载体与夹具契约，不证明 Claude Code / Codex live host 已
  加载或已信任这些 hook；Codex 侧的信任仍需用户在 `/hooks` 中复核。

## M5：插件打包（skill 加薄包装）

等同步模型稳定后，再做插件产物。这样可以先验证入口、目录和写入策略，再固定发布
形态。

要完成：

- 把 skill、工具映射知识和薄包装脚本组装成 Claude / Codex 插件。
- 两侧技能入口与入库的 `plugin/` 边界目录产物，机制按
  [分发模型](../implementation/distribution-model.md)落地。

完成标准：

- 用户安装插件后获得配套 skill 与工具映射知识。
- 产物由允许清单生成，并经过密钥扫描。
- `plugin/` 入库但明确声明生成物属性：由上游组装，不手工编辑。

## M6：稳定化

最后阶段处理跨平台、可靠性和发布。这里维持既定范围，重点是把已经支持的配置面
做稳。

要完成：

- 补齐跨平台路径、换行；确保 git 操作在不同环境下行为稳定。
- 强化 `conflict` / 仲裁的 skill 行为与示例。
- 建立发布前验证命令和 CI 门禁（以文本 / 链接校验和版本一致性为主）。

完成标准：

- 示例项目覆盖技能 / 规则 / 钩子三类 MVP 配置面。三面覆盖由独立示例项目承担，
  绝不通过给本仓库自身的 hooks carrier 装载真实 hook 来达成。
- 快路径、哨兵与仲裁的 skill 行为稳定，落盘前确认与收尾自检可靠。
- 发布流程能复现生成产物。
