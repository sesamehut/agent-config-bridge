# 同步模型

## 模型目标

Bridge 让项目级智能体配置只维护一份，同时允许用户从 Claude Code 或 Codex 会话
发起修改。源采用 Claude 形态只是容器选择；编辑入口、证据要求和决策权对两个 host
对称。总体分层见[架构概览](../architecture/overview.md)。

M4 在技能、entry / rules 之外开放 hooks：

```text
.claude/skills/<name>/   canonical source Git tree
          ⇅ adoption / projection
.agents/skills/<name>/   managed Codex projection Git tree

CLAUDE.md or .claude/CLAUDE.md        canonical entry
.claude/rules/<path>.md                canonical rule shard
          ⇅ adoption / deterministic render
AGENTS.md managed block                managed Codex projection

.claude/rules/hooks.md                 canonical hook intent document
          ⇅ adoption / projection
.claude/settings.json hooks key        managed Claude projection
.codex/hooks.json hooks key            managed Codex projection
AGENTS.md hooks/<id> block             semantic degradation only
```

写面到此覆盖完整 MVP 的三类配置面。CLI、npm package、plugin manifest 与
distribution payload 仍由 M5 门控。

## 两个 skill、两种权限

M4 继续把观察与写入严格分层：

- [`bridge-sentinel`](../../skills/bridge-sentinel/SKILL.md) 读取当前 repo carrier，
  报告一致、漂移、占用和 blocker。它不查询历史来选择写入方向，当前二树的 diff
  shape 只可作为 evidence；source 存在时的已接入 carrier drift 建议
  `reconcile`，copy-only S4 无论项目是否接入都保守报告
  `adoption-candidate` / `annex-or-keep`。Codex loadability 另读 resolved config
  与 exact safe root carrier 形成 live activation evidence；该域不授予 ownership。
- [`bridge-sync`](../../skills/bridge-sync/SKILL.md) 是唯一写侧入口。它从 Git
  可达历史逐 unit 重建最近可证明的一致受管 baseline，再生成
  [`sync-plan/v3`](../../skills/bridge-sync/references/sync-plan-spec.md)。完整计划经
  确认后才写入。

因此 Sentinel 不会仅凭“projection 多了几行”宣判 `adopt`，也不会仅凭行替换宣判
`conflict`。写侧方向来自共同 baseline 与显式所有权证据，精确算法见
[`reconciliation/v3`](../../skills/bridge-sync/references/reconciliation-spec.md)。

## 版本化 covenant

bootstrap 安装
[`covenant/v3` source](../../templates/covenant/claude-rules-bridge.md) 与
[`AGENTS.md` block](../../templates/covenant/agents-md-covenant-block.md)。二者绑定：

- `covenant/v3`
- `source-tree/v5`
- `report/v5`
- `reconciliation/v3`
- `sync-plan/v3`

covenant 正文不再提任何 milestone：它直接声明 hook intents 住在
`.claude/rules/hooks.md`、两个原生 hooks carrier 各自承载哪一侧、gate 与
side-effect 必须先有 `enabled-by` 记录，并写明提交进仓库的 hook 会在每个 clone
上运行、Bridge 的分类是评审元数据而不是沙箱。因此 M5 / M6 不需要再动 covenant，
只有 tuple 本身变化才需要。

只有两个 half 都已 tracked、schema 合法、与精确模板一致且版本相同，项目才是
`onboarded`。写侧按“path / type safety 与 trackability → pair coherence →
tuple version → reachable history”的优先级处理；后面的 version 标签不能覆盖前面的
blocker。任何技能计划之前先应用下表：

| 当前 carrier | 可达历史 | 状态 | 可选动作 |
|---|---|---|---|
| 两 half 都不存在 | 无有效历史，或历史证明已显式完成 offboard | `no-baseline` | `create` |
| 两 half 都不存在 | 历史证明当前 tuple，且未证明完成 offboard | `offboarding` | 明确 `restore` 或 `offboard` |
| 两 half 都不存在 | 历史只证明旧 / 异版 tuple，且未证明完成 offboard | `contract-migration` | 明确 `migrate` 或 `offboard` |
| occupied half 存在 unsafe path / type、只存在一个 half，或 untracked 形状不是下一行的 exact both-untracked current pair | 任意，不先解释 tuple | `blocked` | `repair`，direction=`user-decision` |
| 两 half 都存在、安全、为 current exact templates，且两者都 untracked | 任意 | `blocked` | 零写入 `resolve-blocker`，direction=`user-decision` |
| 两 half tracked，但 malformed / modified 或 tuple 声明互不一致 | 任意 | `blocked` | `repair`，direction=`user-decision` |
| 两 half tracked、彼此一致，且为闭集 {v1, v2} 中某个 exact archived tuple | 任意 | `contract-migration` | `migrate` |
| 两 half 都 tracked 且为当前精确 tuple | 存在 reachable archived-tuple ownership，但没有合格的闭集 transition commit | `contract-migration` | 完成 `migrate`；bytes 可能已无需再写 |
| 两 half 都 tracked 且为当前精确 tuple | 无 legacy ownership，或闭集 archived→current transition 已 reachable | `unchanged` | `unchanged` |

`repair`、`restore`、`migrate`、`offboard` 都以 covenant source、`AGENTS.md`
block 与 preserved manual zone 为同一不可拆 decision closure，不能只改一个 half；
这不承诺跨文件原子性。新建文件不会自动变成 tracked：Bridge 不 stage，因此
bootstrap 写成功后仍按真实 index 状态报告 onboarding，直到用户自行记录该 half，
不能虚报 `onboarded`。

这里有一个明确的时间边界：同一 live operation 从“两 half 都不存在”开始，并完成
两个 strict create、verify 与 journal close 后，其 post-write 结果仍绑定起始快照，
保持 `bootstrap-required` / `no-baseline` / `create` / `applied`；两个新文件仍各自
报告 `untracked-files-included`，但不能追加 `covenant-anchor-anomaly`。journal
关闭后的下一次调用是独立 fresh scan；若两个 exact carrier 仍是 untracked，则
header 是 `blocked`，只选择
`closure/decision/onboarding/covenant` 的零写入 `resolve-blocker`：
baseline 与 annotations 均为 `-`，direction=`user-decision`，
authorization=`not-applicable`，outcome=`blocked`。两个 carrier 各自同时报告
`covenant-anchor-anomaly (untracked)` 与 `untracked-files-included`，且没有
Capability profiles / Write capabilities 行。

例如 untracked source half 与 tracked companion 都声明同一旧版精确 tuple 时，
本轮先是 `blocked` / `repair`，不是 `migrate`。Bridge 不能替用户 stage；用户使
pair 变成 tracked 且精确后，重新扫描才可生成独立 migration closure。

版本升级是显式 `migrate`，不能伪装成普通 drift。archived pair 是封闭两成员集合
{`covenant/v1`, `covenant/v2`}，各自一跳到当前 tuple，不链式迁移；它们只作一次性
迁移 evidence，runtime 只支持 v3/v5，不保留双读兼容。`AGENTS.md` block
外的 manual zone 在上述每类写入前记录快照，写后逐字节验证。

迁移先从 reachable legacy DAG 推导完整 legacy-owned set，并为每个 unit 保留全部
ancestry-maximal candidate OID。`sync-plan/v3` 的独立 Migration candidates table
按 `(unit, oid)` 排序列全候选：唯一 candidate 才同时进入 Migration decisions 的
`legacy baseline`；多个不可比 candidate 时该标量为 `-`、relation=`ambiguous`，
不能按时间、first parent 或用户口头选择折叠。

当前已满足 v5 relation 的唯一候选 unit 自动 `carry-forward`；missing / unsafe /
ambiguous / non-converged unit 阻断整次迁移。ambiguity 必须由 durable、reachable
Git transition 先解析，不能基于任意一个 candidate 确认 repair 或 release。
covenant pair 与 carried set 必须由同一个 reachable transition commit 闭合；该
commit 为 carried units 重新建立 current baseline，即使 unit bytes 本身没变。
Bridge 不 commit，所以 worktree 已是 v3/v5 但 transition 尚未 reachable 时，仍报告
`migration-transition-uncommitted`，不能静默丢失 legacy ownership。

legacy-owned set 只含 M3 就存在的 unit 类：`entry`、`rules/<id>` 与
`skills/<name>`。v2→v3 迁移永远不携带 hooks unit，因为 `reconciliation/v2`
禁止一切 hook 写入，没有可达 v2 commit 能证明 hook baseline。声称拥有 v2 时代
baseline 的 `hooks/*` unit 是越界写入的证据，按 `blocked` / `resolve-blocker`
处理，不得 carry。hooks 只能在迁移之后走普通 `no-baseline` / `create` 通道进入。

## entry / rules 单元与固定 render

`entry` 只在 root `CLAUDE.md` 与 `.claude/CLAUDE.md` 恰好存在一个时成立；两者
并存没有默认 precedence，直接阻断。rule unit 来自 `.claude/rules/**/*.md`，排除
immutable covenant 与 `hooks.md`，id 是 `rules/<relative-path-without-.md>`。

每个 unit 使用 `source-tree/v5` 固定 render：

1. rule shard 剥离合法 `paths` frontmatter；
2. 剥离连续、受控的 `bridge:intent` HTML comments；
3. 减除配对的 `bridge:claude-only` 区段；
4. 拒绝 shared region 中 code span / fence 外的任意 active `@path` import；
5. 应用 normalization N；
6. 对合法 scoped rule 加 exact `pv2` applicability preamble。

Bridge 不做 projection-time 自由 LLM rewrite，也删除旧 `mode=semantic` 逃生路径。
shared prose 必须先变为 host-neutral source edit；真正 Claude-only 段落用注释减除；
真正 Codex-only 指令留在 `AGENTS.md` manual zone。projection-side 出现 host 自指或
其他不可逆编辑时，LLM 只能提出 source candidate，计划必须同时展示 candidate 与
确定性 rerender，取得 `semantic-review-required` 明确确认后才写。

### `paths` 不得静默扩大

frontmatter 不存在表示 unscoped；一旦存在，`paths` 必须是非空、唯一、有序 string
list。invalid bracket、empty / unsafe path、duplicate、exact universal
`**` / `**/*`，以及无法证明落在每 rule 共用 1,000 expanded patterns / 4 MiB
UTF-8 expansion budget 内的 pattern 都阻断。Bridge 不把 invalid、no-op 或
over-budget pattern 当作无前言正文；也不按当前仓库是否有 match 猜测 no-op。

### Codex target eligibility

写前必须证明 root `AGENTS.md` 真正处于可加载位置：

- root `AGENTS.override.md` 不得 shadow；
- effective root markers 必须证明当前 repo root；
- 新建 `AGENTS.md` 不得静默 shadow 当前已选 fallback；
- effective `project_doc_max_bytes` 必须大于零，且 exact planned full-file UTF-8
  bytes 不得超限。

这些事实来自独立 live activation input：完整解析 effective root markers、
`project_doc_fallback_filenames`、`project_doc_max_bytes`，并按 exact root child
检查 override / AGENTS / configured fallback。候选即使 untracked / ignored 也要
检查，但只有 safe regular file 才读取；其 bytes 不进入 ownership。配置、carrier
type、fallback selection 或 budget 无法确定时，必须报 unresolved 并阻断，不能用
“可能是默认值”放行。

达到正预算七分之八是需确认 warning。Bridge 不修改 `.codex/config.toml`、
override、fallback 或 root markers 来制造通过。任何实际 `AGENTS.md` 写入后，用户
必须启动新的 Codex run/session 再验证；不依赖 current-main refresh 行为。

### manual zone 与 reverse adoption

解析器把 `AGENTS.md` 分为 well-formed managed blocks 与全部间隔 byte spans。只有
历史证明或本轮明确 annex 的 block 受管；其余 bytes，包括 blank lines、comments、
Codex-only prose 与未选择 block，都是 protected data。

正向投射把所有 selected block changes 一次合成 full-file desired image。每条 path
由 `capability-profile/v1` 选择版本化协议：已证明的 `strict-replace/v1` 绑定完整
preimage；否则 eligible 现有 UTF-8 text file 可用 `guarded-patch/v1`，从全部变化
求一个唯一 exact contiguous region，执行完整 preflight、单次 exact-literal
replacement 与完整 postverify。新建只用 `strict-create/v1`。

conflict block 与 manual spans 在完整 pre/post image 中保持原字节，即使 region
跨过它们也不得改变。guarded path 必须同时报告 `manual-zone-guarded` 与
`guarded-patch-non-cas`：检查可以过滤/发现 stale value，却不能关闭 host call
内部竞态，也不能保证并发 manual edit 未被覆盖。详细边界见
[写入协议 ADR](../architecture/write-protocol.md)。

reverse adoption 先剥离 exact `pv2` preamble，再用 render origin map 把修改 hunk
映回 shared source spans。frontmatter、intent comments 与 claude-only sections
是 protected islands。跨 island、free-form preamble 或 host 自指产生歧义时，必须
进入上面的 semantic review，不做自动猜测。

## 三种起点

- **空项目**：创建最小 source、current covenant pair 与 rendered blocks；新文件
  未 tracked 时如实保持 bootstrap / blocked。
- **Claude 起点**：现有唯一 entry 与 safe rule shards 是 source candidates；
  既有 AGENTS 内容默认全部 manual。
- **Codex 起点**：把既有 AGENTS 精确分段，逐段确认
  `shared-entry`、`shared-rule`、`manual` 或 destructive `discard`，并在独立
  destination 字段记录 `entry` 或 `rules/<id>`。禁止整文件自动 annex；source
  creation 与同一 span 替换为 rendered block 是一个 closure。

默认 Claude `/init` 不是 onboarding 底座，不能假定它会读取 `AGENTS.md`。

## 技能同步单元

canonical unit 是 root 直属 `.claude/skills/<name>/` 的完整 Git tree，包括
`SKILL.md`、`bridge-intent.yaml`、scripts、references、assets，以及源中明确写入的
`agents/openai.yaml`。投射复制完整 relative file set、blob bytes 与可保真的 Git
mode：

- 不从 `SKILL.md` 派生 `agents/openai.yaml`；
- 不写项目或用户 `skills.config`；
- empty directory 不属于 Git tree；
- symlink、gitlink、junction / reparse point、special file、case-fold collision
  与 path escape 都是 blocker。

Git-tree identity 固定比较 relative path、entry type、raw bytes 与 mode。机械层
用 `git-tree-manifest/v1` 给出这四层 evidence：

- tracked current entry 同时记录 `HEAD` / index mode；POSIX 且
  `core.filemode=true` 时再探测 worktree executable bit，以捕获 unstaged
  mode-only change；
- historical entry 直接读取所选 Git tree 的 mode；
- relevant untracked entry 没有 index mode；可靠 POSIX probe 读取其 prospective
  `100644` / `100755`，probe 不可用时平台仍能证明普通 Git-add default
  `100644`。

Windows、`core.filemode=false` 或 probe 不可用时，已 tracked entry 仍可用 index
证明 Git mode，但不能证明 worktree-only mode claim。普通 untracked regular file
以 prospective `100644` 安全进入 create、source addition 与明确采用 `100644` 的
annex 计划，不再因平台本身被阻断。只有已选写入方向要求 target 变成无法可靠设置的
mode（尤其 tracked / history / explicit intent 要求 `100755`）时才产生
`mode-limited`。pending `annex-or-keep` 与 `keep` 都是零写，不触发方向性 mode
要求。旧的 filesystem `compare-trees` 只承诺 paths + bytes，不能单独声称
Git-tree 等价。

## 钩子意图与双侧投射

canonical source 是 `.claude/rules/hooks.md`。它没有 frontmatter、被 Claude
无条件加载，每个条目以 `## hook: <id>` 开头，正文是固定的五条 prose bullet 加
恰好一个 `yaml` 机器字段块。完整字段表、封闭 lint 与 render 细节由
[`source-tree/v5`](../../skills/bridge-sentinel/references/source-tree-spec.md)
持有，逐类意图的档位表与 host 事实在
[hooks 映射知识](../../knowledge/hooks.md)，示例文档是
[`templates/hook-intents.example.md`](../../templates/hook-intents.example.md)。
示例只是范例，任何流程都不安装它。

### unit 身份

一个 hook 意图对应三个 plan unit：`hooks/<entry-id>/source`、
`hooks/<entry-id>/claude` 与 `hooks/<entry-id>/codex`。source unit 是意图条目
本身，两个 host unit 分别是它在对应 carrier 上的投射。这样 `enabled-by` 追加、
意图修复与反向采纳都能独立可见、独立授权、独立取 baseline。报告侧仍以
`hooks/<entry-id>` 加一列 host 组织行；两套 key 各自成立，谁也不派生谁。

`hooks/<id>/source` 的 baseline 值是条目的 normalized 机器字段模型加五条 prose
bullet；`hooks/<id>/<host>` 的 baseline 是「source 模型 + 该 host owned 组的
normalized handler 模型」这一对，absence 同样是取值。比较发生在字段层，因此重新
格式化意图文档或 carrier 都不会使 baseline 失效。

### class 与显式启用闸门

每个条目必须声明 `class`：`reminder`、`observation`、`gate` 或 `side-effect`。
Bridge 从不由命令字符串推断副作用，class 是作者声明的评审元数据。

`class` 为 `gate` 或 `side-effect` 且 `enabled: true` 时，source 里必须已有覆盖
当前命令的 `enabled-by` 日期记录，Bridge 才投射。缺记录时条目仍 schema 合法：
计划给出一个 selected 的零写 decision closure，action 是 `opt-in-or-skip`，
annotation 是 `decision-required; opt-in-required`，由 hook opt-in gate 拦住。
用户确认后先经 `closure/hooks/source` 追加记录，依赖它的 carrier closure 才正常
投射。首次向 `.claude/settings.json` 写 hook 前，意图文档还必须带一条文件级
`bridge:hooks-shared-execution` 确认注释，缺它同样是 closure 级 blocker。

两道闸门都落在 source 里，因此它们是 PR 中可评审的 diff，并被每个 clone 继承。
它们都不是执行边界：提交进仓库的 hook 会在每个 clone 上运行，Bridge 的分类是
评审元数据而不是沙箱；Claude Code 即使在你从未信任过的目录里也会使用 settings
文件里的 hook，`claude -p` / SDK 会话尤其如此（这类会话不显示信任对话框，交互式
会话则把 settings 文件里的 hooks 扣到对话框被接受为止），所以任何能向本仓库提交
的人都能在同事机器上执行命令。计划的 Evidence 与报告的 runtime hedge 必须逐字
带上规范里 byte-pinned 的这段声明。

### 两个原生载体与降级路径

每个 target 声明自己的 surface 与 tier：

| host | surface | tier | carrier | 写入 |
|---|---|---|---|---|
| claude | `settings-json` | `native` | `.claude/settings.json` 的 `hooks` 键 | owned span |
| claude | `intent-doc` | `semantic` | `.claude/rules/hooks.md` 自身 | 零写 |
| claude | `none` | `declared-unsynced` | 无 | 零写 |
| codex | `codex-hooks-json` | `native` | `.codex/hooks.json` 的 `hooks` 键 | owned span |
| codex | `agents-md` | `semantic` | root `AGENTS.md` 的 `hooks/<id>` 区块 | `closure/agents-md` |
| codex | `none` | `declared-unsynced` | 无 | 零写 |

Claude 侧的降级是零写的：`.claude/rules/hooks.md` 本身就是 Claude 的常驻指令，
条目正文已经是那句常驻指令。Codex 侧的降级才需要在 root `AGENTS.md` 写一个受管
区块，它与 entry / rule 区块合入同一个 `closure/agents-md`，共用同一份
manual-zone 保护与 `project_doc_max_bytes` 预算。

降级只在两个条件同时成立时合法：`class` ∈ {`reminder`, `observation`}，且该
event 由 dated registry `shared-events/2026-09-07` 证明在该 host 上没有原生承载
面。`gate` 与 `side-effect` 的效果是运行期否决或真实副作用，散文不能假装它；违反
是 `degradation-ineligible`。Claude 不读 `AGENTS.md`，所以 `agents-md` 只在 Codex
target 合法，`intent-doc` 只在 Claude target 合法。

`.codex/hooks.json` 是 Codex 唯一写目标。若同层 `.codex/config.toml` 还声明了
inline `[hooks]` 表或 legacy `hooks =` 指针键，两种形态会在同一层合并成两个不同
的位置 trust key 却共享同一个 normalized hash，hook 因此跑两遍；检测到就阻断
`closure/hooks/codex`（且只阻断它）。检测声明为浅字节扫描而不是 TOML 解析，无法
证明不存在时同样阻断。`.claude/settings.local.json` 不是写目标，只作只读
`local-hooks-present` 观察。

closure 与顺序：`closure/hooks/source`、`closure/hooks/claude`、
`closure/hooks/codex` 各写一条 path；后两者与 `closure/agents-md` 在
`closure/hooks/source` 被选中时依赖它，但三个 carrier closure 之间没有依赖边，
以免推迟一段散文说明就让可执行的 hook 不可执行。先后由步骤顺序保证：
`.claude/rules/hooks.md`、`AGENTS.md`、`.claude/settings.json`、
`.codex/hooks.json`。Bridge 不承诺跨 carrier 原子性，因此单侧被阻断时会发出需
确认的 `hook-projection-asymmetric`；只有 `class: gate` 例外，它是全有或全无：
一侧被阻断或不可用时，把兄弟 carrier closure 强制为 `not-selected` 零写，被阻断
的那一侧仍保持 `selected` / `not-applicable` / `blocked` 及其 unavailable Write
capabilities 行，因为半边生效的强制比不强制更糟。

### 档位与 declared-unsynced

hook 行的 tier 集合是 `native | semantic | declared-unsynced`，`structural` 保留
且对 hook 行非法。tier 是声明值，Bridge 只校验不推导：把 registry 证明在该 host
非原生的 event 声明成 `native` 是 `tier-unsupported-event`；registry 采集日之后
新增的未知 event 名仍然合法，但带 `event-unverified` 注记。

`declared-unsynced` 同时进入 plan 的 state registry 与 tier registry，是独立状态
而不是 `unchanged` 的别名或一条 warning。它让「这一侧有意不投射」可序列化，例如
Claude 的 `PermissionRequest` `decision` 是字符串而 Codex 是对象，Codex 的
`permissionDecision: "ask"` 仍未实装，一份脚本不可能同时服务两侧。

### 计划要为每个 hook 解释什么

`## Hook tiers` 表逐 unit 给出档位与理由，行集必须与计划的 hook unit 集完全相同，
每行 tier 必须与 Units 表一致。reason 取自封闭 registry（例如
`shared-event-command`、`claude-only-event`、`degraded-standing-instruction`、
`decision-not-portable`、`opt-in-pending`）。理由不能只写在 Evidence 里，因为期望
比对会忽略 Evidence 与 notes。

`## Hook adoption decisions` 表处理 carrier 侧的未知占用，是 Codex 起点分段表的
JSON 对应物：每个未知 handler 都带一个可定位到具体 event、matcher 组与组内位置的
定位串，以及 `adopt` / `keep` / `discard` 处置与确认状态，`discard` 需要单独的
破坏性确认；确认 `adopt` 会在 source 新建条目，五条 prose bullet 必须由用户提供，
Bridge 不代写 Purpose 或 Failure policy。反向采纳只覆盖该 host 的声明字段集；
`event` 永不采纳（换 event 就是换组，等于一次可证明的受管删除加一次新建），改动能
映回共享标量时必须先展示另一侧 carrier 的重渲染 bytes，否则落到 per-host override
并要求 `override-reason` 与显式确认。

两张表的精确列、定位串文法与 reason registry 的完整取值由
[`sync-plan/v3`](../../skills/bridge-sync/references/sync-plan-spec.md) 拥有，本文
只述结论，不复制 schema 文本。

### JSON 受管键写入

两个 hooks carrier 都是 JSON，但 protocol token 不变：现有文件用
`guarded-patch/v1`，新建只接受 `strict-create/v1`，而后者在两个 host 上当前都
`unavailable`，所以 carrier 缺失时该 closure 阻断，并在 Evidence 里给出需要用户
自己粘贴的精确 bytes。postimage 的求法有独立名字 `json-owned-span/v1`：只编辑
owned `(event, effective matcher)` 组的 byte span，其余字节逐字节复制，禁止整
文件反序列化再序列化。幂等律、最小成员 span 编辑、append-only 数组顺序与封闭
validator 失败 id `hooks-carrier-composition` 见
[写入协议 ADR](../architecture/write-protocol.md)。

ownership 只从意图文档推导：对 host `h`，owned 组恰好是 `targets.<h>.surface`
为 JSON carrier 的合法条目的 `(event, effective-matcher(h))` 对。carrier 里的其他
组、非 `command` 的 handler 类型、语义改变键与未声明键都是 unmanaged occupancy，
只报告、只走 `annex-or-keep`，绝不删除。语义相等即为 `unchanged`：字节不同也不
产生 Write capabilities 行，只发信息性 `hook-format-preserved`。

### Codex 逐 hook 信任的后果

Codex 把逐 hook 信任写进用户 `config.toml` 的 `[hooks.state."<key>"]`，key 是
`<source>:<Event>:<groupIndex>:<handlerIndex>`，按位置编址（2026-09-07 源码核验，
见 [Codex 能力面核验](../research/codex-capability-surface.md)）。由此有四条后果：

- Bridge 只 append，永不重排或移动既有元素，owned 与否都一样。删除同一 event 里
  的非末元素会让后续元素改位，必须发需确认的 `codex-trust-reindex`；被清空的
  event member 整体删除（trust key 按 event 分段，其他 event 不重排），`hooks`
  对象清空后保留 `"hooks": {}`。
- trust identity 哈希的是 timeout 归一化之后的 normalized config，`event`、
  `matcher`、`command`、归一化 `timeout`、`statusMessage`、`async` 与归一化
  `additionalContextLimit` 都在其中。任一项变化都会把该 hook 变成 Modified 并停止
  运行，所以计划必须在确认前用 `codex-hook-retrust-required` 指名哪个
  `(<Event> group=<i> handler=<j>)` 会变暗。
- `commandWindows` 不在 identity 里，这是一个盲区：只替换 `commandWindows` 时旧的
  trusted hash 依然有效，Windows 分支已经换了代码却不需要重新信任。Bridge 对这类
  计划发信息性 `codex-trust-blind-change`。
- 因为 `statusMessage` 在 identity 内，`[bridge:<id>]` 标记在 Claude 侧总是写，在
  Codex 侧只在创建 handler 时写；Bridge 不在已收敛的 Codex handler 上增删改它。

项目未被信任时 Codex 根本不加载 `.codex/` 层，未信任的 hook 在 `codex exec` 里
被静默跳过且没有任何提示。这是 live activation 事实而不是 repo bytes 事实：写后
只在 Codex 行、且只在 post-write 结果里带 `awaiting-host-trust`，并提示用户在
Codex 中运行 `/hooks` 复核信任。项目信任本身是 live activation input，解析为
`untrusted` 或 hooks feature 关闭时另有对应观察项。

### 两个 host 的 Windows shell 不同

2026-09-07 在同一台 Windows 机器上实测：Claude 用 bash（Git Bash）执行
`command`，Codex 用 pwsh（7.6.5）执行 `commandWindows`，且 Windows 上只有
`commandWindows` 分支会跑。因此共享的 `command` 必须在 bash 与 PowerShell 下都
成立（普通程序调用加简单参数），否则条目必须带 per-host 分支。
`targets.codex.commandWindows` 选的是命令文本，`targets.claude.shell` 选的是
解释器，二者不是映射对，Bridge 不从一个派生另一个。`commandWindows` 与 effective
`command` 不同的 handler 必须发需确认的 `platform-branch-divergence`：Windows 与
POSIX 跑的是不同代码，用户必须看见。

Codex 的项目级 hook 不注入任何环境变量，而 Claude 会注入
`${CLAUDE_PROJECT_DIR}` 一类占位符，所以引用路径占位符的命令不可能是同一个共享
字符串。同理，输出 JSON 信封的 hook 必须是提交进仓库的脚本文件：内联命令行的
引号处理会破坏信封。hook 是否真的执行是观察到的行为而不是保证，任何 Bridge 状态
都不得读作运行期保证。

## 当前快照与 Git 输入

写前 current snapshot 由三类信息组成：

1. `git ls-files --stage` 与 `git-tree-manifest/v1` 选出的 tracked worktree
   路径、type、bytes、HEAD / index / 可用 worktree mode evidence 与 tracked
   deletion；
2. `git ls-files --others --exclude-standard` 选出的 relevant non-ignored
   untracked regular files；
3. 仅用于警告的 ignored path 列表。

relevant untracked 文件进入计划与本次 current comparison，但 Bridge 不
`git add`、不 stage、不 commit。ignored 文件不属于 canonical Git tree，不进入
baseline，也不读取或复制；若技能确实依赖它，用户需先把它变成有意的
non-ignored source input。manifest 会把 probe 不可用时的普通 untracked mode
明确标成 prospective platform default `100644`，不会伪装成已有 tracked tree。
若对应 tracked source / history 或用户明确要求 executable `100755`，再做
direction-aware comparison；target 无法设置时以 `mode-limited` 阻断。疑似
secret、credential、private key 或 generated payload 直接阻断复制。

所有 unrelated dirty changes 保留。计划显示 scoped 影响与 out-of-scope dirty
摘要，但 Bridge 不 stash、reset 或清理它们。

## 所有权不是路径猜测

完整 project covenant 只声明 Bridge 的所有权模型，不会把每个同名 target 自动
收编。某 projection 只有在以下任一条件成立时才受管：

- 用户在本轮明确确认 `annex`；或
- `HEAD` 可达 Git 历史证明一次 ownership-establishing transition，且后续到
  baseline 的所有权连续。

证明需组合 valid contract、canonical source、projection path history、transition
后的 carrier relation，以及与 create / projection / adoption / annex 一致的
commit / diff evidence：skills 是两个 complete Git trees 的 path/type/raw-bytes/mode
parity；entry/rules 是 raw source 与 deterministic rendered block pair。
`bridge-intent.yaml` 与 commit message 可以补强，但 intent 本身绝不授予 ownership。

因此 master 缺失而 copy 存在时，Sentinel 的 S4 在 `onboarded` 与
`not-onboarded` 两种项目状态下都只能给出 `adoption-candidate` /
`annex-or-keep`。只有 Sync 找到连续 ownership 与 unique baseline 后，才能把它
仲裁为受管的 source-side deletion；project covenant 本身不是删除授权。

无 baseline 时不猜方向：

- valid source + absent / empty target 可以计划 `create`；
- 任何 non-empty target，包括无 `SKILL.md`、看似手写副本，或与 source 恰好相同的
  副本，都是 `annex-or-keep`；
- `annex` 是明确所有权转换；`keep` 仅本次零写，不生成 ignore manifest、不等于
  同步成功，同路径问题仍需 relocate / replace / abort。

## baseline：按 unit 从可达 DAG 重算

Bridge 不保存 hash、归因数据库或独立 snapshot。每次运行按 unit 从 Git 重算：

1. 只枚举 `HEAD` 可达 commit，不看其他 refs、reflog 或时间戳。
2. candidate 必须处于当前 contract tuple且当时 unit ownership 有效；skills 要求
   source / projection complete Git tree 的 paths、types、raw bytes、modes 相同，
   entry/rules 则要求 raw source 与唯一历史 block 满足 deterministic render relation，
   hooks 要求意图条目模型与该 host owned 组的 normalized handler 模型成对。
3. 若 candidate `x` 是 `y` 的祖先，则 `y` 比 `x` 新。
4. 取 ancestry-maximal candidates。
5. 恰好一个 maximal candidate 才是 baseline `B`；零个是 `no-baseline`；多个互不
   可比较 maximal candidates 是 merge-DAG ambiguity，阻断并请用户裁决。

算法不按 author date、commit date 或 wall-clock 选边。旧 contract 下的 identical
pair 不是普通当前 baseline，只能进入 migration。唯一跨 tuple 的入口是上面的
closed-set archived→current transition commit：它为 carried units 生成 current
candidates，之后 runtime baseline selection 只读 v3/v5。

## baseline 决策表

以 absence 也作为 tree value，比较 current source `S`、projection `P` 与同一
baseline `B`：

| 关系 | 状态 | 计划动作 |
|---|---|---|
| `S = B`, `P = B` | `unchanged` | `unchanged` |
| `S != B`, `P = B`, S 存在 | `source-only` | `update` |
| S 缺失，`P = B` | `source-only` | `delete`（source → projection） |
| `S = B`, `P != B`, P 存在 | `projection-only` | `adopt` |
| `S = B`, P 缺失 | `projection-only` | `delete`（projection → source） |
| `S != B`, `P != B`, `S = P`，intent 完整 | `unchanged` | 无写 |
| `S != B`, `P != B`, `S = P`，required intent 缺失 | `intent-missing` | 补 source intent 并重投射 |
| `S != B`, `P != B`, `S != P` | `both-changed` | `conflict` |

只有两侧自同一 baseline 出现不同 current trees，才是 `conflict`；不自动三方 merge。
`reproject` 仅用于用户确认 projection-side 差异是 accidental / mechanical、应由
source 覆盖的决策，不能从当前 diff shape 自动推出。

## intent 记录

每个受管技能必须有 `bridge-intent.yaml`，且作为完整 tree 的一部分逐字节投射；
entry / rule 使用 render 时剥离的 strict `bridge:intent` HTML comments；hook 条目
使用条目内的 `intent` 列表。hook 的 `enabled-by` 是另一件事：它记录的是对
`gate` / `side-effect` 命令的启用授权，绝不能与动机记录互相顶替，采纳一个
`gate` / `side-effect` 条目被手改的 `command` 还必须取得新的 `enabled-by`，陈旧
授权不得跨越改过的命令行。以下情况追加日期与单行动机：

- 首次 create / onboarding；
- annex 或 projection-side adopt；
- semantic source update；
- rename（记录 old / new name 与动机）。

`unchanged` 与 byte-for-byte mechanical reproject 不追加。若两侧已手工收敛到同一
semantic change、但没有新记录，计划先向用户取得或提出动机，再在 source 追加并
机械重投射。记录只作 evidence，不覆盖 baseline 或 ownership 判定。

## delete、rename 与破坏性边界

自动收敛 delete / rename 的前提是 unique baseline 证明目标曾受管。无 baseline
时，missing path 只是 absence，new path 只是 unknown occupancy。

rename 是 old / new 跨 unit 的不可拆 dependency closure，只接受用户明确 rename intent 或可靠 Git
path history；不按 similarity score 猜测。新 identity 必须合法，new source 追加
rename intent，old target 的所有待删路径必须有 ownership 证明，destination 必须
absent / empty 或经明确 annex。任一成员 conflict / blocked，整个 rename closure
零写。各路径按 conditional operation 顺序执行，不承诺跨文件原子性；若同一 live
operation 内的补偿遇到并发改动或自身失败，必须报告 `partial`。

delete 后 unit-local intent carrier 也消失，因此 tombstone 动机必须由用户后续 commit /
diff evidence 或未来显式 covenant 机制承载；Bridge 本身不 commit。

## 计划、确认与物理批次

每次写前输出完整 `sync-plan/v3`，包含所有相关 unit、baseline、direction、action、
exact path、untracked / ignored、compatibility warnings、dirty scope 与 blocker。
Write capabilities table 按执行顺序列出每个 path 的 forward / inverse protocol；
contract migration 另用 Migration candidates table 列出每个 unit 的全部 maximal
legacy OID；含 hook 行的计划另有 `## Hook tiers` 与 `## Hook adoption decisions`
两张表，空时渲染 `- (none)`。

决策按 unit 做，授权与执行按稳定 closure id 聚合。Units table 必须为每行序列化
closure、`selected|not-selected` 与 per-closure authorization；Closures table 必须
列出 sorted members、dependencies、selection、authorization、outcome。partial batch
通过 `not-selected` 明确表达，不能藏在 Evidence prose：

- covenant source + `AGENTS.md` block 不可拆；
- 所有 selected `AGENTS.md` block changes 聚合为一个 desired image，再由已序列化
  的 strict 或 guarded replace protocol 单次修改该 path；未选或 conflict blocks
  与 manual spans 原字节参加完整 pre/post image；
- rename 的 old / new units 不可拆。

每次写都需确认完整 scoped plan。conflict、annex / replace、migration、offboarding
及破坏性决策还需明确选择。只有 `selected` 且 authorization=`confirmed`、其依赖也
selected+confirmed 的 closure 可执行；conflict / blocked / not-selected closure
零写。若确认前 relevant bytes 改变，必须重新扫描与出计划。

formal validator 的 context 显式记录 operation lifecycle、live untracked paths 与
派生 temporal context。empty-bootstrap 的同操作 post 与独立 fresh scan 只能由
公开 starting-tree bytes、render operations、capability operations、decision、
live Git tracking state 和 lifecycle 区分；validator 不读取 expectation、golden
plan 或 result alias 决定有效性。

执行在第一个 `failed` / `partial` closure 停止；因前序失败或 dependency closure
未执行而跳过的后续 closure 标为 `not-attempted`。它不同于写前 evidence gate
选出的 `blocked`，也不同于已经开始执行的 `failed`。

apply blocker 使用 sync-plan/v3 的 closed registry，不能只写进 prose。除 covenant、
activation、entry/rule schema、marker、history、migration 与 write capability
外，`mode-limited`、`sensitive-or-generated-blocked`、`unsafe-tree-entry`、required
ignored input 与 definite skill loadability failure 也一律阻断。M4 新增三道
gate：hook source（`intent-doc-anomaly`）、hook carrier（`hooks-carrier-unusable`、
`codex-inline-hooks-conflict`）与 hook opt-in（`hook-opt-in-required`、
`hook-acknowledgement-missing`）。

“任一行命中即禁止 apply”仍是全局默认，只有 write capability、hook carrier 与
hook opt-in 三道 gate 例外：它们的禁止范围收敛到命中行所在 closure 及其依赖
closure，互不依赖的其他 selected closure 仍可执行。被这样阻断的 closure 保持
`selected`、authorization=`not-applicable`、outcome=`blocked`，绝不改写成
`not-selected`。

## 写入协议、失败补偿与事后 rollback

执行前解析 `capability-profile/v1`，绑定 host/version、tool surface、platform 与
filesystem assumptions；任何未证明项默认 unavailable。strict token 是
`strict-replace/v1`、`strict-create/v1`、`strict-delete/v1`。create、delete、
rename、mode change 与 inverse operation 只接受对应 strict 能力；缺失时用
`conditional-write-unavailable` 阻断。

现有安全 UTF-8 text file 的 replace 可在 strict replace 缺失时选择
`guarded-patch/v1`。old region 必须非空、覆盖全部 changed bytes、在完整 preimage
中唯一，并由 adapter 做一次 exact-literal、non-fuzzy、非 `replace_all` 替换。无法
形成 region 或没有 adapter 时用 `guarded-patch-unavailable` 阻断。preflight
full-image equality、单次 patch 与 postverify full-image equality 都必须执行，但
guarded 明确不是 CAS。

fixture-only 的 retained-root-child fault mutation 按 platform 单独解析。POSIX
retained leaf handle 与 link count 不能在同目录 rename/replacement 后证明当前
root-child 名称仍指向该 leaf；缺少与同一次 mutation 绑定的 name-to-leaf 证明时，
该 mutation 保持 declarative-only，`apply-fault` 在改目标前 fail closed。Windows
不继承这一 POSIX 降级，其能力继续由独立的 handle/name/reparse/filesystem
attestation 决定。

selected closure set 首次写入前，在 repo 外新建 access-safe operation-local journal。
journal 绑定 opaque operation id、resolved repo、starting HEAD、exact confirmed plan
SHA-256、selected closure ids / dependencies / authorization、每条 path 的 step、
forward / inverse protocol、capability binding、pre/intended/applied value，以及
guarded region offset 与 exact old/new region；lifecycle 是
`prepared|executing|compensating|verified|partial|closed`。只保留本次 live
operation 的精确 journal path，禁止扫描 broad temp directory 寻找旧 journal。

全部步骤完成后依次：

1. 重读所有受影响路径；
2. 用 Git manifest 机械比较 source / projection 的 paths、types、bytes、modes；
3. 如涉及 covenant，验证 exact templates 与 `AGENTS.md` manual-zone snapshot；
4. 运行 scoped `git status --short`、scoped `git diff`、`git diff --check`；
5. 输出 post-write outcome 与剩余 warning。

entry/rule closure 在任何 mutation 前先计算完整 AGENTS desired bytes 并重验所有
source 与 full preimages；canonical source 先写，AGENTS carrier 最后写。每次 host
call 后立即重读完整 path。guarded call 后若等于 planned postimage 就继续；仍等于
preimage 且本轮尚无 mutation 是 `failed`；任何第三值，或此前已有 mutation，则为
`partial`。

same-operation compensation 默认不可用。首写前必须为每个逆操作证明 strict
protocol：replacement→strict replace、create→strict delete、
delete→strict create。缺一项就报告需确认的 `strict-compensation-unavailable`，
允许 forward guarded plan 继续，但禁止 optimistic reverse。只有 inverse 全部
strict 且 live journal 仍打开时才逆序执行；完整恢复并验证后是 `compensated`。

若补偿条件被拒绝、恢复失败、journal 不可用，或最终无法证明 pre-write closure，
则停止并报告 `partial`，保留 evidence，后续 / dependent closure 为
`not-attempted`。协议保证止于所选 host operation 与底层 filesystem；Bridge
不实现 lock、跨文件事务、crash durability，也不把 guarded patch、atomic rename
或 advisory lock 描述为 CAS。

`applied` 后 journal 转为 `closed`，不授予之后或跨 session rollback。用户提出
rollback 时必须从 current bytes + reachable Git 重建新计划并重新确认；用户确认
不能用任意 evidence 替代 ownership、baseline 或 prior bytes。Git 无法重建精确旧值
就明确不可 rollback，只能另行按正常门禁计划 annex 或 destructive decision。完成
新的 write-protocol 流程后才是 `rolled-back`。不得扫描旧临时 journal，也不得
用 blanket `git restore` / reset / stash 擦除失败或覆盖用户原有、并发 dirty
changes。

## 四条兼容性轴

技能投射机制 tier 仍是 `native`，但以下轴正交：

1. Agent Skills format；
2. 两 host runtime loadable；
3. 当前 release validator profile；
4. behavior portability。

Claude-only frontmatter、dynamic content 与 `allowed-tools` 在两 host 可加载时允许原样
byte-copy，但标 `behavior-degraded`；identity、YAML、确定加载失败与 path safety 才
是 blocker。Codex skill carrier 不使用 `awaiting-host-trust`；repo bytes 只证明
carrier，live activation 仍是 unknown，写后建议 fresh session / restart 再做
discovery smoke test。事实依据见
[Codex 能力面核验](../research/codex-capability-surface.md)与
[host 上下文核验](../research/host-context-loading.md)。
