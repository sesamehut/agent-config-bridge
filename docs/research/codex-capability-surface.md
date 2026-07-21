# Codex 能力面核验

采集日期：2026-07-07；2026-07-08 复核增补（见同名小节）。主要来源为 Codex
官方文档（developers.openai.com/codex）与 openai/codex 仓库的 issue /
discussion 追踪。进入实现前需按本文档日期重新核验。

这份核验梳理 Codex 的项目级配置能力面。结论：hooks、项目级技能、命令规则与
项目指令（`AGENTS.md`）都是原生机制，投射就是把内容写进各 host 的原生位置。

## Hooks：原生支持，已 GA

来源：[developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks)、
[config-reference](https://developers.openai.com/codex/config-reference)。

- **状态**：实验版随 CLI v0.114 引入（约 2026-03），GA 约 2026-05-14；采集日
  的 changelog（0.140.0 / 0.141.0，2026-06）中为稳定维护特性。feature flag
  `[features] hooks = true` 默认开启。
- **事件模型**（10 个生命周期事件）：`SessionStart`、`SubagentStart`、
  `PreToolUse`、`PermissionRequest`、`PostToolUse`、`PreCompact`、`PostCompact`、
  `UserPromptSubmit`、`SubagentStop`、`Stop`。10 个事件在 Claude Code 侧全部
  同名存在，无 Codex 独有事件；Claude Code 另有约 20 个独有事件（`SessionEnd`、
  `Notification`、`FileChanged` 等），挂在其上的钩子意图没有 Codex 原生承载面。
- **PreToolUse 拦截范围**：可拦截 Bash、apply_patch 文件编辑和 MCP 工具调用，
  matcher 为正则；官方定位为 guardrail 而非完整 enforcement boundary——复杂
  shell 调用与 WebSearch 等非 shell / 非 MCP 工具不被拦截
  （[openai/codex#20204](https://github.com/openai/codex/issues/20204)）。
- **配置形式**：`hooks.json`（与 Claude Code hooks 同族 schema：事件 →
  matcher → `{type, command, timeout, statusMessage}`），或 `config.toml` 内联
  `[[hooks.<Event>]]` 表；`commandWindows` 字段做 Windows 命令分支（Codex
  独有，Claude 未文档化）。
- **配置层级**：用户级 `~/.codex/hooks.json`；**项目级
  `<repo>/.codex/hooks.json`**（也可写在项目 `.codex/config.toml`）；插件自带
  `hooks/hooks.json`；企业 `requirements.toml`。多层命中的 hook 全部执行，
  高层不覆盖低层。
- **信任机制**：项目级 `.codex/` 层只在项目被信任后加载；非受管 hook 首次运行
  前需要用户审阅信任，且信任绑定 hook 内容哈希——**hook 被改动后需要重新信任**。
  CLI 内 `/hooks` 命令可查看 / 信任 / 禁用。
- **协议**：command hook 从 stdin 读 JSON（session_id、cwd、事件名、model、
  permission_mode 等），可返回 JSON 控制续行 / 提示（`continue`、`stopReason`、
  `systemMessage`）；exit code 2 + stderr 表示阻断。PreToolUse 支持
  `permissionDecision: "allow" | "deny"`（`"ask"` 解析未实装）、`updatedInput`
  输入重写与 `additionalContext` 注入，PermissionRequest 返回
  `decision.behavior`，与 Claude 同形——Claude 式 deny hook 在 Codex 原生
  可表达。目前只有 `type: "command"` 会执行：`prompt` / `agent` 处理器"解析但
  跳过"，`async: true` 的处理器被整体跳过（不退化为同步执行）。
- **对 Claude 的刻意兼容**：插件 hook 除 `PLUGIN_ROOT` / `PLUGIN_DATA` 外还
  注入 `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA`（官方文档明言 "for
  compatibility"）——Codex 有意镜像 Claude Code 的 hook schema。
- **已知 bug（与本项目直接相关）**：
  [openai/codex#17532](https://github.com/openai/codex/issues/17532)（采集日
  仍 open，报于 CLI 0.120.0）：写在项目 `.codex/config.toml` 里的 hooks 配置
  可能不触发交互式 `SessionStart` / `Stop`。投射目标应优先
  `.codex/hooks.json`，并在实现时用当前 CLI 版本实测。

## notify：被 hooks 取代的窄机制

来源：[config-advanced](https://developers.openai.com/codex/config-advanced)。

`notify` 在事件发生时调外部程序，但只有一个事件（`agent-turn-complete`），且
**仅用户级生效**——官方明确项目级配置不能覆盖 notify 键。生命周期自动化应走
hooks，notify 不作为投射目标。

## Rules（execpolicy）：命令审批的项目级规则

来源：[developers.openai.com/codex/rules](https://developers.openai.com/codex/rules)。

- `.rules` 文件用 Starlark 编写 `prefix_rule(pattern, decision, ...)`，decision
  为 `allow | prompt | forbidden`；多规则命中时最严者胜；shell 链
  （`&&`、`;`、`|`）逐段评估。
- 位置：用户级 `~/.codex/rules/`，**项目级 `<repo>/.codex/rules/`**（同样受
  信任门槛）。`codex execpolicy check` 可离线测试。
- 与 `approval_policy`（`untrusted | on-request | never`）同属执行语义。这与
  Claude 的 permissions 规则在语义上是对应物，且两侧都是文件化配置面——
  维持"声明不同步"；两侧映射面都已存在，可作未来映射立项候选。

## 技能：项目级与用户级都支持，注意目录是 `.agents/skills`

来源：[developers.openai.com/codex/skills](https://developers.openai.com/codex/skills)。

- 格式：`SKILL.md` + YAML frontmatter（`name`、`description`）+ 可选脚本 /
  资源，与 Claude 技能同构；可选 `agents/openai.yaml` 供 Codex app 展示与
  调用策略。
- **发现位置**：从 CWD 向上到仓库根逐级扫描 `.agents/skills/`；用户级
  `$HOME/.agents/skills/`；管理员级 `/etc/codex/skills`。**当前官方路径是
  `.agents/skills`，不是 `.codex/skills`**（后者见于第三方博客，属早期实验
  布局，以官方文档为准）。
- CLI / IDE 扩展 / app 三个表面都支持；显式（`/skills`、`$` 提及）或按任务
  隐式触发。

## AGENTS.md：项目指令加载机制

来源：[guides/agents-md](https://developers.openai.com/codex/guides/agents-md)、
[config-reference](https://developers.openai.com/codex/config-reference)。

- **发现链**：项目根由 `project_root_markers`（默认 `.git`）从 cwd 向上定位，
  随后从项目根到 cwd 逐目录收集指令文件；每目录按 `AGENTS.override.md` →
  `AGENTS.md` → `project_doc_fallback_filenames` 取第一个命中，**每目录至多
  一个文件**。全局层另读 `~/.codex/AGENTS.override.md`（否则 `AGENTS.md`）。
- **拼接语义**：全部命中文件按根到 cwd 顺序原样拼接（全局指令在前），层级间无
  替换 / 遮蔽；指令链按环境 cwd 构建（2026-07-08 更正，原记"会话启动时构建
  一次"），cwd 之下与旁系目录不扫描，也不随编辑位置动态加载。
- **预算**：`project_doc_max_bytes` 是项目指令链的总预算（默认 32 KiB），超出
  截断；设 0 关闭项目指令加载。
- **无内嵌语义**：文件按原始字节拼进 prompt，不解析 frontmatter，不支持 glob /
  条件作用域；**HTML 注释也不剥离**（与 Claude 相反）——受管区块标记在 Codex
  侧进入模型上下文并占用预算，应保持精简。
- **没有分片机制**：Codex 没有 `.claude/rules/*.md` 的等价物（官方
  [customization](https://developers.openai.com/codex/concepts/customization)
  页枚举的模型面只有 AGENTS.md / Memories / Skills / MCP / Subagents）；嵌套
  AGENTS.md 是唯一原生多文件指令形态。规则分片注入 `AGENTS.md` 受管区块就是
  投射到原生指令面，path-scoped 语义走适用性前言。

## 其余机制速记

- **Automations**（[app/automations](https://developers.openai.com/codex/app/automations)）：
  Codex app 专属的定时任务（支持 cron 表达式），在本机后台 worktree 运行；
  CLI / IDE 无此机制。属调度自动化，与 hooks 的事件自动化互补，MVP 不涉及。
- **Custom prompts 已废弃**（[custom-prompts](https://developers.openai.com/codex/custom-prompts)）：
  官方建议改用技能。
- **Local Environments**（app）：worktree 创建时执行 setup 脚本，配置存于项目
  `.codex/` 并可入库。
- Codex app 设置面板的「编码」区（钩子 / 连接 / Git / 环境 / 工作树）与上述
  文件机制一一对应；hooks 定义本身是文件，**可随仓库共享**。

## 项目级配置面汇总

Codex 读取的项目级配置：`AGENTS.md`（含根到 cwd 链上的嵌套文件与
`AGENTS.override.md`）与 `.agents/skills/`（注意根目录是 `.agents` 不是
`.codex`）；受信任门槛的 `.codex/` 层——`config.toml`（不可覆盖 provider /
auth / notify 等机器本地键）、`hooks.json`、`rules/*.rules`、`agents/*.toml`
（项目级 subagent 定义，仅作用于该 subagent 会话）。

## 2026-07-08 复核增补

采集日期：2026-07-08。来源同上（官方文档与 issue 追踪复查）；哨兵观察项与
注记的口径见
[report-spec](../../skills/bridge-sentinel/references/report-spec.md)。

- **项目指令预算是合并预算，截断发生在文件中部且无提示**：
  `project_doc_max_bytes`（默认 32768 字节）是项目根到 cwd 整条指令链的合并
  预算，按根在前的顺序消耗；越过剩余额度的那个文件被从中间截断，TUI 无任何
  提示，其后的文件整体跳过。全局层 `~/.codex/AGENTS(.override).md` 不计入该
  预算、前置拼接。config-reference 上按逐文件预算的表述已过时。另：显式设
  `project_doc_max_bytes = 0` 会关闭整个项目指令面，哨兵对此报观察项。
- **`AGENTS.override.md` 是同目录遮蔽**：每目录第一个命中生效，根目录存在
  override 时它完整取代根 `AGENTS.md` 进链——整个规则投射面静默失效。哨兵将
  其作为一级发现报告。官方文档对该文件是否建议 gitignore 仍无说明。
- **SKILL.md 解析面**：Codex 只解析 `name`（可选，缺省取目录名，上限 64
  字符）、`description`（必填非空，缺失则技能静默不可发现）与
  `metadata.short-description`；未知 / Claude-only frontmatter 键被发现流程
  忽略（官方刻意保留的修复路径），但技能被调用时随正文原样呈现给模型。Claude
  动态令牌（`$ARGUMENTS`、`${CLAUDE_*}`、反引号执行行、`@file`）在 Codex 是
  惰性字面文本——不执行、不替换。UTF-8 BOM 会破坏 frontmatter 解析
  （[openai/codex#13918](https://github.com/openai/codex/issues/13918)，采集日
  仍 open），技能静默不可发现。纯空白的项目指令文件会被跳过。
- **技能列表元数据预算**：注入的技能列表（name + description + 路径元数据）
  约有上下文 2% / 8000 字符的预算，完整 SKILL.md 只在选中时加载——投射的
  `description` 应保持精炼。
- **`.codex/skills/` 是迁移前布局**：旧路径对当前 CLI 大概率不可见；哨兵对
  仓库中残留的该目录报观察项。2026-07-08 再次确认官方项目级路径是
  `.agents/skills/`。
- **`[[skills.config]]` 开关可让已写入的技能失活**：`[[skills.config]]`
  （path、enabled）条目与 `[skills] include_instructions = false` 都可能让
  写入的技能"已写入、不生效"；项目级过滤是否被遵守受多个 open bug 影响
  （openai/codex#20210、#24237、#14161、#16012）。
- **`.agents/skills` 的信任门控目前无文档**：信任门控此前是对旧
  `.codex/skills` 布局确认的，对当前路径官方未说明。这是技能行"已写入、待
  host 信任"常驻注记的依据之一，M2 写侧工作前必须实测复核。
- **`.codex/hooks.json` 顶层形态已钉定、待实测**：本仓库钉定其顶层为事件名键
  （无包装对象），与 Claude hooks 值同族（事件 → matcher 分组 → 处理器）。
  该形态未经真机核验，任何 M2 hooks 写侧工作开始前必须实测；夹具按钉定形态
  编码，若被证伪则夹具与期望文件一并更新。

## 对设计的影响

- **钩子投射目标是项目级 `.codex/hooks.json` 声明键**：两侧 hooks 为同族
  schema，事件名与结构高度对应，映射近乎机械。只有超出 Codex 承载能力的意图
  才落回常驻指令（语义降级）：Claude 独有事件、非 command 处理器、`async`
  后台钩子、`permissionDecision: "ask"`、工具输出重写。
- **技能投射目标确定**：Codex 侧受管副本写入 `.agents/skills/<name>/`。
- **信任门槛进入生效模型**：投射写入 `.codex/` 后并不立即生效——项目需被
  信任，且改动过的 hook 要用户重新信任。同步计划应把"已写入、待 host 信任"
  如实呈现，这不是漂移。
- **execpolicy 是权限映射的候选面**：Claude permissions 与 Codex rules 两侧
  都是文件化配置面，未来立项时可直接评估；MVP 维持声明不同步。

## 实现前需要复核

- issue #17532 状态：项目级 `config.toml` 内联 hooks 是否已修复；实测
  `.codex/hooks.json` 在当前 CLI 的触发行为。
- `.codex/hooks.json` 顶层形态实测（事件名键、无包装对象的钉定形态）——必须
  先于任何 M2 hooks 写侧工作。
- Codex 对 handler 上 `statusMessage` 字段的容忍度：决定写侧是否在 Codex 面
  附加 `[bridge:<id>]` 强化标记（所有权推导不受影响）。
- `.agents/skills` 路径是否仍是官方项目级技能目录（该路径经历过迁移；
  2026-07-08 已再次确认，写侧实现前再复核一次）。
- `.agents/skills` 的信任门控：对当前路径官方未说明（旧 `.codex/skills` 布局
  曾确认受门控），M2 写侧工作前实测。
- `[[skills.config]]` 项目级过滤相关 open bug（#20210、#24237、#14161、
  #16012）状态。
- hooks 的 `prompt` / `agent` 处理器与 `async` 是否已实装（影响可映射的
  意图范围）。
- 信任流程的实际交互成本（首次信任、哈希变更重信任）对快路径体验的影响。
- 受管区块与投射内容对 `project_doc_max_bytes`（默认 32 KiB 合并预算）的
  占用；警戒阈值的标定留到有真实投射体量后进行。
- `AGENTS.override.md` 的 gitignore 定位（官方仍无说明；根目录 override 遮蔽
  整个投射面已定为哨兵一级发现，剩余悬而未决的只有 gitignore 定位）。
- UTF-8 BOM frontmatter bug（#13918）是否修复——修复前 BOM 技能在 Codex
  静默不可发现。
