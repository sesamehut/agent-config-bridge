# 同步模型

## 模型目标

同步模型支撑一个核心体验：用户在 Claude Code 与 Codex 之间等权重切换，项目级
技能、规则和钩子只维护一份，并在两个工具里都以各自可达的最高保真度生效。源是
一棵 Claude 形态的声明式源树，其余 host 可见配置是投射；源树、编辑入口对称与
反向采纳的设计见[架构概览](../architecture/overview.md)。

## 从状态对齐到行为约定

Bridge 不建同步引擎。同步由三条路径组成：

### 快路径：编辑即传播

行为约定注入到两个 host，两侧同构：常驻指令加 hook 提醒。Claude 侧是常驻规则加
`settings.json` hooks，Codex 侧是 `AGENTS.md` 常驻指令加 `.codex/hooks.json`
hooks。约定内容：凡涉及项目级智能体配置的改动，

1. 落进源树对应位置（入口指令、规则分片、技能母本、钩子意图文档），同时按
   意图记录格式记下改动动机与日期（记录形式见
   [source-tree-spec](../../skills/bridge-sentinel/references/source-tree-spec.md)）。
2. 在同一个工作单元内更新所有受影响投射面。
3. 提交时源与投射一起入 git。

同步单元因此就是一次提交。常规路径上不存在跨提交漂移，也就不需要独立维护
"上次同步基线"。

### 哨兵：漂移检测

约定遵从是概率性的：长会话、context 压缩、注意力被主任务占据都可能让 agent 忘记
收尾；用户也可能直接手改投射面，或经 `git pull` 带入外部改动。哨兵负责发现：

- **检查内容**：投射面与源树的一致性——技能副本逐字节比对，`AGENTS.md` 受管
  区块与源内容比对，`settings.json` 与 `.codex/hooks.json` 的声明键与钩子意图
  比对。
- **判定口径**：一致 / 漂移是（源字节，投射字节）的确定性纯函数——按固定模板
  重渲染源内容，应用固定的归一化集，再逐字节比对。渲染管线与归一化集的规范定义见
  [source-tree-spec](../../skills/bridge-sentinel/references/source-tree-spec.md)，
  状态判定规则见
  [report-spec](../../skills/bridge-sentinel/references/report-spec.md)。
  LLM 只执行检查清单并撰写报告的自由文本部分，从不判定一致与否；语义等价的
  判断属于仲裁，不属于哨兵。
- **建议去向表驱动**：漂移行的建议去向由差异形状决定——仅新增 → 采纳回源，
  仅删减 → 按源重投射，两者兼有 → 冲突（形状定义见
  [report-spec](../../skills/bridge-sentinel/references/report-spec.md)）。
- **触发位置**：两侧都可挂 hook（`Stop` / `SessionStart` 等会话事件、提交前），
  常驻指令的收尾自查作为补充；两侧都可由用户显式调用。
- **行为边界**：哨兵只报告，不修复。

### 仲裁：语义修复

哨兵报告漂移后，修复由 LLM 主导：

1. 用 `git log` / `git blame` 收集证据：改动来自哪个方向、何时发生、动机为何
   （源树条目的意图记录也是证据）。
2. 核实每处漂移的语义性质：投射面上的新意图、约定遗漏、还是外部引入。哨兵
   报告中的状态与建议去向（采纳回源 / 按源重投射 / 冲突）已由差异形状表驱动
   给出，证据只影响采纳时的回写落点与执行叙述，不改动这两列。
3. 无歧义的修复自动执行，修复计划作为报告产出并随写入入 git；`conflict` 与收编
   决策不自动处理，由用户选择。

仲裁不做三方合并，也不要求基线存在；基线若可从历史定位，只是证据之一。

## git 作为确定性底座

git 底座与封顶论证见[架构概览](../architecture/overview.md)。实现侧要求：源树
与投射面都入 git，真正进 `.gitignore` 的只有 Bridge 工具侧的构建中间产物；行为
约定失败的最坏结果是暂时漂移，失败代价被 git 封顶。

## 完备投射与保真度阶梯

源树每个语义单元必须到达每个 host，档位取该 host 可达的最高保真度；四档定义见
[架构概览](../architecture/overview.md)。本节按配置面展开。

### 技能：原生等价

两个工具都消费以 `SKILL.md` 为核心的技能目录。`.claude/skills/<name>/` 是母本，
整体复制到 Codex 的项目级技能目录 `.agents/skills/<name>/`。选 copy 而非 symlink，出于 Windows 权限、插件打包和
git diff 稳定性考虑。副本整体归 Bridge 所有（按文件集声明），哨兵做逐字节比对；
落在副本上的直接改动经仲裁确认归属后逐字节回写母本。

### 入口指令与规则：结构降级加语义降级

- `CLAUDE.md` 是人工维护的源入口，其中共享内容由 skill 投射进 `AGENTS.md` 受管
  区块。默认投射是固定管线的逐字渲染（管线定义见
  [source-tree-spec](../../skills/bridge-sentinel/references/source-tree-spec.md)）；
  host 自指内容的唯一规范排除路径是源侧的 claude-only 注释标记减除，仅面向
  Claude 的段落渲染时整段剔除（host 事实见
  [host 行为核验](../research/host-context-loading.md)）。LLM 改写式投射不是
  渲染模式：被改写过的投射与逐字渲染结果比对必然呈现为漂移，交仲裁处理（M2+）。
  声明了非默认渲染模式的受管区块获得独立状态"语义映射区块（逐字校验不适用）"，
  不做字节比对，留待仲裁按需核验（见
  [report-spec](../../skills/bridge-sentinel/references/report-spec.md)）。
- `.claude/rules/*.md` 每个分片投射为 `AGENTS.md` 受管区块内的独立小节，带来源
  标注：身份不丢，反向归因有据。
- path-scoped 分片（frontmatter `paths`）投射时渲染显式适用性前言，大意是
  "以下规则仅在处理匹配文件时适用"（固定句式模板与版本标记见
  [source-tree-spec](../../skills/bridge-sentinel/references/source-tree-spec.md)）。
  Claude 靠加载器机械限定作用域，Codex 靠模型注意力限定——语义降级但生效。
- 受管区块内的直接改动是常规输入而非错误：来源标注给出回写目标分片，反向采纳
  做逆向语义映射——适用性前言还原为 `paths` frontmatter；没有明确目标分片的
  新增内容由 LLM 判断落点（入口、既有分片或新建分片）。
- `AGENTS.md` 受管区块外是人工区，放真正只给 Codex 的内容；人工区不参与自动
  回源。用户想让 Claude 也遵守某段人工区内容时，动作是把它挪进源树。

### 钩子：意图为源，双侧投射

钩子意图文档（`.claude/rules/hooks.md`）是源，写清触发点、目的、命令、环境
要求和失败策略。它投射到两侧的承载面：

- Claude 侧：`settings.json` 中声明过的 hooks 键（按键声明所有权）。
- Codex 侧：项目级 `.codex/hooks.json` 中声明过的键（同为按键声明）。两侧
  hooks 是同族 schema，大部分意图都能原生承载；超出对方 hooks 能力面的意图
  才降级为 `AGENTS.md` 常驻指令（语义降级），并在同步计划里如实标注档位。

声明键的登记处就是意图文档本身：某 host 上归 Bridge 所有的键集合，从意图文档中
面向该 host 的模式有效条目直接推导，不另设清单文件（条目格式与推导规则见
[source-tree-spec](../../skills/bridge-sentinel/references/source-tree-spec.md)）。
投射出的 handler 可以附带一个 `[bridge:<id>]` 前缀的 `statusMessage` 标记，
只作人类可读的所有权强化，从不承担归属判定（标记语法与孤儿键的归因规则见
spec 文件）。

Codex 只在项目被信任后加载 `.codex/` 层，且改动过的 hook 需要用户重新信任
（host 事实见 [Codex 能力面核验](../research/codex-capability-surface.md)）。
信任状态无法从仓库字节观察，因此"已写入、待 host 信任"不是漂移、也永远不是
可由夹具检测的状态，而是 Codex 侧报告行的常驻注记（注记规则见
[report-spec](../../skills/bridge-sentinel/references/report-spec.md)）。

意图文档以规则片段形式存在，Claude 会把它读进上下文——读到的是意图说明，满足
源树"被 Claude 读取时无害或有益"的双重角色约束。高副作用钩子默认要求显式启用，
让自动执行面的扩大成为用户可见的选择。

### 执行语义：声明不同步

Codex 审批 / 沙盒规则（`approval_policy`、`.codex/rules/` execpolicy）的执行点
在 host 运行时，不在模型上；用常驻指令复述会伪装成安全边界。这类语义声明为
Codex 所有、不投射（第 4 档）。Claude 权限规则与 Codex execpolicy 规则语义上
存在对应物，且两侧都是文件化配置面，属于未来映射知识的立项候选，MVP 不做。

## 所有权声明

所有权不依赖在内容里做标记，按三种粒度声明：

- **文件集**：技能受管副本整体归 Bridge；源树归用户与快路径共同维护。
- **区块**：`AGENTS.md` 只有受管区块归 Bridge，由 `bridge:managed` 注释标记对
  圈定（标记语法见
  [source-tree-spec](../../skills/bridge-sentinel/references/source-tree-spec.md)）。
  Codex 不剥离 HTML 注释，受管标记会进入模型上下文并占用项目指令预算，标记
  保持精简（见 [host 行为核验](../research/host-context-loading.md)）。
- **键**：`settings.json` 与 `.codex/hooks.json` 只有声明过的 hooks 键归
  Bridge。JSON 无法内嵌注释标记的问题在按键声明下不存在。

## 同步计划与报告分类

每次传播（正向投射或反向采纳）都产出同步计划，逐单元报告：

- `create` / `update` / `unchanged`：常规投射状态。项目级接入判定每次扫描整体
  计算一次（判定条件见
  [source-tree-spec](../../skills/bridge-sentinel/references/source-tree-spec.md)）：
  已接入项目缺失的投射是漂移、按源重投射（对应 `create`）；未接入项目的缺失是
  "未投射（待引导）"而非漂移——哨兵仍只报告，不执行引导。
- `adopt`：投射面上的新意图采纳回源树，反向传播的常规状态。
- 保真档位：原生等价 / 结构降级 / 语义降级 / 声明不同步。
- `conflict`：源树与投射面同时携带不同新意图，需用户选择。
- 收编或保留：目标位置已有看似人工维护、不在声明范围内的内容，先问用户。
- 无源单元：显式的空面行。某检查面没有任何源单元时，报告仍为该面输出一行，
  空面不静默。

无歧义单元自动执行，计划即报告；`conflict` 与收编单元等用户决定（护栏见
[架构概览](../architecture/overview.md)）。

## 项目引导（三种起点）

工具等权重要求三种起点获得同等对待：

- **全新项目**：skill 生成源树骨架与各投射面。
- **Claude 起点**：已有 `CLAUDE.md` / `.claude/`，直接声明为源树并生成投射面。
  已有 `AGENTS.md` 时，其内容经确认后收编进源树或保留在人工区。
- **Codex 起点**：已有 `AGENTS.md`，skill 提议把内容收编为源树（入口加分片），
  再把 `AGENTS.md` 重建为受管投射加人工区。收编前出计划，逐段确认去向。

任何起点都不允许静默覆盖既有人工内容。

## 已知代价

- **Codex 侧上下文成本**：Claude 按需加载的 path-scoped 规则在 Codex 以
  `AGENTS.md` 常驻方式全量加载，并与全部项目指令共享总预算。投射时可对长分片
  做保义压缩，默认保持接近逐字以保可审计性。
- **注意力限定弱于加载器限定**：scoped 规则在 Codex 可能被误用于无关文件。失败
  是行为噪音而非数据损坏，被 git 封顶原则覆盖。
- **约定遵从与语义映射是概率性的**：正向投射与反向采纳都依赖 LLM 判断，靠哨兵
  与仲裁兜底；稳定性随 host 与模型版本波动，风险由计划报告、声明式所有权和
  git 自检压低。
