# 同步模型

## 模型目标

Bridge 让项目级智能体配置只维护一份，同时允许用户从 Claude Code 或 Codex 会话
发起修改。源采用 Claude 形态只是容器选择；编辑入口、证据要求和决策权对两个 host
对称。总体分层见[架构概览](../architecture/overview.md)。

M2 只开放技能写路径：

```text
.claude/skills/<name>/   canonical source Git tree
          ⇅ adoption / projection
.agents/skills/<name>/   managed Codex projection Git tree
```

规则与入口的一般投射留到 M3，hooks 意图与双侧投射留到 M4。M2 唯一会写规则 /
入口面的操作，是安装版本化 covenant 的 source half 与 `AGENTS.md` managed block；
这是 bootstrap 基础设施，不是提前开放一般规则投射。

## 两个 skill、两种权限

M2 把观察与写入严格分层：

- [`bridge-sentinel`](../../skills/bridge-sentinel/SKILL.md) 读取当前 repo carrier，
  报告一致、漂移、占用和 blocker。它不查询历史来选择写入方向，当前二树的 diff
  shape 只可作为 evidence；source 存在时的已接入 carrier drift 建议
  `reconcile`，copy-only S4 无论项目是否接入都保守报告
  `adoption-candidate` / `annex-or-keep`。
- [`bridge-sync`](../../skills/bridge-sync/SKILL.md) 是唯一写侧入口。它从 Git
  可达历史逐 unit 重建最近可证明的一致受管 baseline，再生成
  [`sync-plan/v1`](../../skills/bridge-sync/references/sync-plan-spec.md)。完整计划经
  确认后才写入。

因此 Sentinel 不会仅凭“projection 多了几行”宣判 `adopt`，也不会仅凭行替换宣判
`conflict`。写侧方向来自共同 baseline 与显式所有权证据，精确算法见
[`reconciliation/v1`](../../skills/bridge-sync/references/reconciliation-spec.md)。

## 版本化 covenant

M2 bootstrap 安装
[`covenant/v1` source](../../templates/covenant/claude-rules-bridge.md) 与
[`AGENTS.md` block](../../templates/covenant/agents-md-covenant-block.md)。二者绑定：

- `covenant/v1`
- `source-tree/v3`
- `report/v3`
- `reconciliation/v1`
- `sync-plan/v1`

只有两个 half 都已 tracked、schema 合法、与精确模板一致且版本相同，项目才是
`onboarded`。写侧按“path / type safety 与 trackability → pair coherence →
tuple version → reachable history”的优先级处理；后面的 version 标签不能覆盖前面的
blocker。任何技能计划之前先应用下表：

| 当前 carrier | 可达历史 | 状态 | 可选动作 |
|---|---|---|---|
| 两 half 都不存在 | 无有效历史，或历史证明已显式完成 offboard | `no-baseline` | `create` |
| 两 half 都不存在 | 历史证明当前 tuple，且未证明完成 offboard | `offboarding` | 明确 `restore` 或 `offboard` |
| 两 half 都不存在 | 历史只证明旧 / 异版 tuple，且未证明完成 offboard | `contract-migration` | 明确 `migrate` 或 `offboard` |
| occupied half 存在 unsafe path / type、partial，或任一 half untracked | 任意，不先解释 tuple | `blocked` | `repair`，direction=`user-decision` |
| 两 half tracked，但 malformed / modified 或 tuple 声明互不一致 | 任意 | `blocked` | `repair`，direction=`user-decision` |
| 两 half tracked、彼此一致，且为可识别的旧 / 异版精确 tuple | 任意 | `contract-migration` | `migrate` |
| 两 half 都 tracked 且为当前精确 tuple | 任意 | `unchanged` | `unchanged` |

`repair`、`restore`、`migrate`、`offboard` 都以 covenant source、`AGENTS.md`
block 与 preserved manual zone 为同一原子 closure，不能只改一个 half。新建文件
不会自动变成 tracked：Bridge 不 stage，因此 bootstrap 写成功后仍按真实 index
状态报告 onboarding，直到用户自行记录该 half，不能虚报 `onboarded`。

例如 untracked source half 与 tracked companion 都声明同一旧版精确 tuple 时，
本轮先是 `blocked` / `repair`，不是 `migrate`。Bridge 不能替用户 stage；用户使
pair 变成 tracked 且精确后，重新扫描才可生成独立 migration closure。

版本升级是显式 `migrate`，不能伪装成普通 drift。`AGENTS.md` block 外的 manual
zone 在上述每类写入前记录快照，写后逐字节验证。

`templates/covenant/hook-intents.md` 仍是 M4 规划资产；M2 不安装、不合并、不启用
它。

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
后的完整相同 Git tree，以及与 create / projection / adoption / annex 一致的
commit / diff evidence。`bridge-intent.yaml` 与 commit message 可以补强，但 intent
本身绝不授予 ownership。

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
2. candidate 必须处于当前 contract tuple、当时 unit ownership 有效，且 source /
   projection 的完整 Git tree（paths、bytes、modes）相同。
3. 若 candidate `x` 是 `y` 的祖先，则 `y` 比 `x` 新。
4. 取 ancestry-maximal candidates。
5. 恰好一个 maximal candidate 才是 baseline `B`；零个是 `no-baseline`；多个互不
   可比较 maximal candidates 是 merge-DAG ambiguity，阻断并请用户裁决。

算法不按 author date、commit date 或 wall-clock 选边。旧 contract 下的 identical
pair 不是当前 baseline，只能进入 migration。

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
| `S != B`, `P != B`, `S = P` | `unchanged` | 无写；若缺 semantic intent record 则补记录并重投射 |
| `S != B`, `P != B`, `S != P` | `both-changed` | `conflict` |

只有两侧自同一 baseline 出现不同 current trees，才是 `conflict`；不自动三方 merge。
`reproject` 仅用于用户确认 projection-side 差异是 accidental / mechanical、应由
source 覆盖的决策，不能从当前 diff shape 自动推出。

## intent 记录

每个受管技能必须有 `bridge-intent.yaml`，且作为完整 tree 的一部分逐字节投射。
以下情况追加日期与单行动机：

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

rename 是 old / new 跨 unit 的原子事务，只接受用户明确 rename intent 或可靠 Git
path history；不按 similarity score 猜测。新 identity 必须合法，new source 追加
rename intent，old target 的所有待删路径必须有 ownership 证明，destination 必须
absent / empty 或经明确 annex。任一成员 conflict / blocked，整个 rename closure
零写。这里的“原子”指执行结束时 old / new 完整 closure 要么是 verified planned
value，要么经本轮自动失败补偿恢复为 verified pre-write value；若补偿遇到并发改动
或自身失败，必须报告 `partial`，不能继续声称原子成功。

delete 后技能内 intent 文件也消失，因此 tombstone 动机必须由用户后续 commit /
diff evidence 或未来显式 covenant 机制承载；Bridge 本身不 commit。

## 计划、确认与物理批次

每次写前输出完整 `sync-plan/v1`，包含所有相关 unit、baseline、direction、action、
exact path、untracked / ignored、compatibility warnings、dirty scope 与 blocker。

决策按 unit 做，物理写按 dependency closure 与共享文件聚合：

- covenant source + `AGENTS.md` block 不可拆；
- 所有修改同一个 `AGENTS.md` 的操作聚合并保护 manual zone；
- rename 的 old / new units 不可拆。

每次写都需确认完整 scoped plan。conflict、annex / replace、migration、offboarding
及破坏性决策还需明确选择。无歧义且独立的 closure 可在确认后执行；conflict /
blocked closure 零写。若确认前 relevant bytes 改变，必须重新扫描与出计划。
执行在第一个 `failed` / `partial` closure 停止；因前序失败或 dependency closure
未执行而跳过的后续 closure 标为 `not-attempted`。它不同于写前 evidence gate
选出的 `blocked`，也不同于已经开始执行的 `failed`。

## 写入事务、失败补偿与事后 rollback

每个已确认 physical closure 在首次写入前，都要在 repo 外安全 OS 临时目录建立
operation-local journal。对本轮可能修改的每条 exact path 记录 existence、type、
raw bytes 与 mode，并记录每一步 planned value。每次写都是 compare-and-swap：
写前重读并要求 current 等于 journal precondition（或本 closure 上一步精确写入
值），写后再记录本轮实际写入值。任何不相等都视为并发 / plan 外变化，停止且不
覆盖。

全部步骤完成后依次：

1. 重读所有受影响路径；
2. 用 Git manifest 机械比较 source / projection 的 paths、types、bytes、modes；
3. 如涉及 covenant，验证 exact templates 与 `AGENTS.md` manual-zone snapshot；
4. 运行 scoped `git status --short`、scoped `git diff`、`git diff --check`；
5. 输出 post-write outcome 与剩余 warning。

确认原计划已经授权同一 closure 的**自动失败补偿**，无需二次确认：mutation 开始
后若写入或验证失败，按 journal 逆序处理；每条恢复前必须证明 current 仍等于本轮
精确写入值，才可恢复 precondition（包括原先 absent / type / mode）。完整恢复并
验证后是 `compensated`；首次 mutation 前失败且 closure 证明未变是 `failed`。

若补偿 CAS 发现并发编辑、恢复失败，或最终无法证明 pre-write closure，则停止并
报告 `partial`，保留 evidence，后续 / dependent closure 为 `not-attempted`。这
是原子语义的明确极端失败边界，不做虚假保证。

`applied` 之后用户提出的 rollback 是另一项操作：只限本轮 journal paths，先用新
计划和新确认授权，并要求 current closure 仍等于 verified applied value；完成同一
验证流程后才是 `rolled-back`。不得用 blanket `git restore` / reset / stash
擦除失败，也不得覆盖用户原有或并发 dirty changes。

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
