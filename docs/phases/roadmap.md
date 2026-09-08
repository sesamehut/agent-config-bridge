# 路线图

路线图按风险递增推进：先定稿源树声明、行为约定和保真度分类，做只读的哨兵与同步
计划；再从技能这种原生等价配置面开始落盘；随后处理规则与钩子投射，最后打包
分发。

产品产物按[分发模型](../implementation/distribution-model.md)声明的目录落地；
CLI、npm package、插件清单与插件制品门控到 M5，CI 门禁是 M6 工作。

各里程碑的收口记录（交付内容、检查命令与证据计数）见 [`closure/`](closure/)；
路线图只记录规划，不记录状态。

## M1：源树声明与只读哨兵

M1 是只读阶段。目标是确定源树形状、行为约定文本和报告口径，让后续落盘建立在
清楚的输入和分类规则上。

要完成：

- 定稿源树布局与条目约定（markdown + frontmatter 加目录约定，含意图记录）。
- 起草注入两个 host 的行为约定文本：两侧同构，常驻指令加 hook 提醒。
- 起草哨兵检查流程与同步计划报告格式（含保真档位）。
- 起草工具映射知识的初始结构（带采集日期）。

完成标准：

- 能扫描一个示例项目，报告源树与各投射面的一致性状态。
- 报告状态集封闭，与 [report-spec](../../skills/bridge-sentinel/references/report-spec.md)
  的口径一一对应，夹具比对按该口径逐一验收。
- 没有落盘能力；所有结果只停留在报告与同步计划。

收口记录见 [closure/m1.md](closure/m1.md)。

## M2：技能投射与采纳（原生等价档）

技能是第一块落盘配置面。目录结构清楚，Claude Code 和 Codex 都消费 `SKILL.md`，
适合验证快路径、文件集所有权和哨兵比对。

要完成：

- 实现技能母本到 Codex 项目级技能目录（`.agents/skills/`）的投射。
- 快路径约定在技能面落地：编辑母本后同一工作单元内更新副本。
- 实现漂移仲裁：副本被手改后，无歧义时采纳回母本或按源重投射，冲突时报告
  并等用户选择。

完成标准：

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

收口记录见 [closure/m2.md](closure/m2.md)。

## M3：入口与规则投射（结构 / 语义降级档）

规则在技能之后处理，因为它开始涉及降级投射与 LLM 语义映射。

要完成：

- `CLAUDE.md` 共享内容与 `.claude/rules/` 分片投射进 `AGENTS.md` 受管区块。
- 受管区块直接改动的反向采纳。
- path-scoped 分片的适用性前言渲染。
- host 自指内容的投射改写约定；Claude-only 段落的注释标记。
- 三种起点的引导流程，重点是 Codex 起点：既有 `AGENTS.md` 收编为源树。

投射与反向采纳的机制细节见[同步模型](../implementation/sync-model.md)。

完成标准：

- 共享规则只维护一份，并已投射、验证到两侧项目载体；作用域语义在 Codex 以
  适用性前言保留。live host discovery / activation 仍需后续集成验证。
- 手改 `AGENTS.md` 受管区块的内容能正确回到对应源分片，两侧重新一致。
- `AGENTS.md` 写入以完整 planned image 逐字节携带受管区块外的 manual zone；
  strict path 只有在完整 expected preimage 与 mutation 由同一原语绑定时才声称
  `manual-zone-preserved`，guarded path 必须报告
  `manual-zone-guarded` / `guarded-patch-non-cas` 及 host call 内的 residual race。
- Codex 起点项目可经逐段确认完成收编，无静默覆盖。

收口记录见 [closure/m3.md](closure/m3.md)。

## M4：钩子意图与双侧投射

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
- Codex 项目级 hooks 的信任加载与逐 hook 重新信任：用一次交互式 `/hooks` TUI
  会话验证「首次信任后无 bypass 也能运行、改动字段后变为 Modified」的完整流程，
  并现场确认状态落点；trust identity 的字段构成与状态落点的源码层核验见
  [Codex 能力面核验](../research/codex-capability-surface.md)。

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

收口记录见 [closure/m4.md](closure/m4.md)。

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
