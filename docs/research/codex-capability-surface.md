# Codex 能力面核验

采集日期：2026-07-23。主要来源为 Codex 官方文档
（developers.openai.com/codex）、Agent Skills 官方规范与 openai/codex 官方
仓库实现。M2 技能结论只把官方文档和固定提交的实现作为事实依据；issue /
discussion 只保留为待复核线索，不承担公共契约。哨兵观察项与注记的口径见
[report-spec](../../skills/bridge-sentinel/references/report-spec.md)。

这份核验梳理 Codex 的项目级配置能力面。结论：hooks、项目级技能、命令规则与
项目指令（`AGENTS.md`）都是原生机制，投射就是把内容写进各 host 的原生位置。

## Hooks：原生支持，已 GA

来源：[developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks)、
[config-reference](https://developers.openai.com/codex/config-reference)。

- **状态**：实验版随 CLI v0.114 引入（约 2026-03），GA 约 2026-05-14；采集日
  changelog（0.140.0 / 0.141.0，2026-06）中为稳定维护特性；feature flag
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
- **配置形式**：`hooks.json` 顶层是带 `hooks` 键的包装对象（可选顶层
  `description` 字符串），`hooks` 内为事件名键，值与 Claude Code hooks 同族
  （事件 → matcher 分组 → `{type, command, timeout, statusMessage}`）；
  2026-07-08 曾记为裸事件名键，2026-07-23 按官方 reference 与
  `hook_config.rs`（`HooksFile`）证伪，夹具与规范按包装对象形态编码。也可在
  `config.toml` 内联 `[[hooks.<Event>]]` 表；`commandWindows` 字段做 Windows
  命令分支（Codex 独有，Claude 未文档化）。
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

## 技能：格式、运行时、校验器与行为可移植性分层

来源：[Codex skills 文档](https://developers.openai.com/codex/skills)、
[Agent Skills specification](https://agentskills.io/specification)、
[Claude Code skills 文档](https://code.claude.com/docs/en/slash-commands)，以及
openai/codex 固定提交 `44d76c6` 中的
[loader](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/core-skills/src/loader.rs)、
[显式注入路径](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/core-skills/src/injection.rs)、
[捆绑校验器](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/skills/src/assets/samples/skill-creator/scripts/quick_validate.py)
与
[skill config 取层逻辑](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/core-skills/src/config_rules.rs)。

这四层必须分别判断：

| 层 | 回答的问题 | M2 使用方式 |
|---|---|---|
| Agent Skills format | 一个 skill 在开放格式上是否合法 | 定义可共享的文件格式底线 |
| host runtime acceptance | 当前宿主实际上能发现、解析哪些 bytes | 作为带日期的实现观察，不扩张公共契约 |
| Codex bundled validator | 当前 Codex 自带创作工具会放行什么 | 作为 M2 写前校验门，不冒充 runtime parser |
| behavior portability | 同一份 bytes 在两侧是否产生同一语义 | 决定 portability lint 与人工判断 |

### Agent Skills format

- 一个 skill 是至少含 `SKILL.md` 的目录，可选 `scripts/`、`references/`、
  `assets/` 等资源；`SKILL.md` 是 YAML frontmatter 加 Markdown body。
- `name` 与 `description` 必填；`name` 最多 64 字符、使用小写字母 / 数字 /
  连字符、不得首尾或连续使用连字符，并应与父目录同名；`description` 非空且
  最多 1024 字符。
- `license`、`compatibility`、`metadata` 与 `allowed-tools` 是标准可选键。
  其中 `allowed-tools` 明确标为 experimental，规范也明确各 agent
  implementation 的支持可能不同；格式合法不能推出权限行为等价。
- 规范只定义 authoring format，不定义项目目录、宿主发现、用户配置、信任、
  调用策略或 Claude Code 的动态内容扩展。

### Codex 发现与生效

- **公开发现位置**：Codex 从 CWD 向上到仓库根逐级扫描 `.agents/skills/`；
  用户级为 `$HOME/.agents/skills/`，管理员级为 `/etc/codex/skills`。M2 只把
  `.agents/skills/` 当项目公共契约；即使某个当前 runtime 仍宽松接受旧
  `.codex/skills/`，也不把兼容实现当投射目标。
- CLI、IDE extension 与 app 都支持 skills；可通过 `/skills` 或 `$` 显式调用，
  也可由 `description` 匹配隐式调用。可选 `agents/openai.yaml` 承载界面信息、
  `allow_implicit_invocation` 与依赖声明。
- 技能列表只先放入 name、description 与路径元数据，预算最多为上下文的 2%，
  上下文大小未知时为 8000 字符；完整 `SKILL.md` 在选中后加载。因此
  `description` 应保持精炼。
- **repo bytes、discoverability 与 live activation 正交**：目录和副本存在只
  证明 bytes 已写入；出现在 host skill list 才证明被发现并通过 metadata
  解析；在当前会话被显式或隐式调用才证明 live activation。M2 的同步状态不能
  从任一层反推另外两层。
- Codex 的项目信任文档把门槛限定在项目 `.codex/` config / hooks / rules
  层；skills 文档没有把 `.agents/skills/` 发现绑定到该门槛。因而没有官方依据
  为项目 skills 合成 `awaiting-host-trust` 状态。真实调用仍应单独 smoke test，
  但“不确定”不是一个可以常驻输出的信任结论。
- `[[skills.config]]` 的官方写法位于用户级 `~/.codex/config.toml`；当前核心
  也只从 User 与 SessionFlags 层读取逐 skill 开关。它是用户本地的 live
  activation override，不是 repo 投射面：M2 不生成、不改写 config。既有用户
  override 可能使“已写入、已发现”仍未生效，应作为运行环境事实解释，而不是
  文件漂移。

### Codex runtime acceptance

- 公开 Codex 文档要求 `name` 与 `description`。固定提交的当前 loader 实现只把
  `name`、`description` 与 `metadata.short-description` 解析为核心 metadata；
  对缺失 `name` 会回退到目录名，并忽略未知 frontmatter 键。这些宽松行为是
  当前实现观察，不是 bridge 可以依赖的公共 authoring contract。
- 显式 skill 注入路径读取 `SKILL.md` 后把 `contents` 原样交给 prompt
  injection；没有与 Claude Code 对应的动态渲染阶段。因而 Claude 的参数 /
  环境变量占位符和 shell injection 语法在 Codex 中保留为原文，除非模型随后
  按普通指令主动解释它们；这与宿主预处理不是同一语义。
- UTF-8 BOM 会使文件不再以可识别的 `---` frontmatter 开始；可移植 skill
  不应带 BOM。

### Codex bundled validator

Codex 当前捆绑的 `skill-creator/scripts/quick_validate.py` 是独立的 authoring
gate，行为与开放规范及 runtime loader 都不完全相同：

- 顶层只允许 `name`、`description`、`license`、`allowed-tools` 与 `metadata`；
  因此会拒绝 Agent Skills 标准合法的 `compatibility`，也会拒绝 Claude-only
  frontmatter。
- 它要求 `name` / `description` 键存在并要求值是字符串；非空时才检查 name
  语法与长度、description 的 1024 字符上限及尖括号。当前脚本对空字符串的放行
  是校验器缺口，不降低开放规范的非空要求。
- 它不检查 `name` 与父目录一致。这个规范要求必须由 bridge 的公共格式校验补齐。
- 它接受 `allowed-tools` 只说明 YAML 键通过此脚本，不证明 Codex runtime 会赋予
  与 Claude 相同的工具权限。

### 行为可移植性

- 整目录逐字节 copy 且两侧原生消费 `SKILL.md`，所以投射机制是 `native`；这不
  自动等于行为原生等价。
- 稳定的共同核心是规范合法的 `name`、`description`、静态 Markdown 指令与按
  普通相对路径引用的资源。`license` / `metadata` 可保持格式，但不提供行为
  等价保证；`compatibility` 当前受 Codex bundled validator 差异阻断。
- `allowed-tools` 不属于行为等价子集：Agent Skills 将其标为 experimental；
  Claude Code 将其实现为 skill 调用当回合的免询问权限授予，并对项目 skill
  受 workspace trust 约束；Codex 没有公开承诺同一权限语义。
- Claude Code 当前会在 skill 内容进入上下文前渲染 `$ARGUMENTS`、
  `$ARGUMENTS[N]` / `$N`、由 `arguments` 声明的 `$name`，以及
  `${CLAUDE_SESSION_ID}`、`${CLAUDE_EFFORT}`、`${CLAUDE_SKILL_DIR}`、
  `${CLAUDE_PROJECT_DIR}`；还会执行行内 `` !`command` `` 与带 `!` 标记的
  fenced shell block，再以输出替换占位。Codex 原文注入不提供这些
  预处理语义。因此任何这些令牌或 Claude-only frontmatter 都必须按行为降级
  报告，而不能因 bytes 相同或 runtime 宽松接收未知键而标为等价。

## AGENTS.md：项目指令加载机制

来源：[guides/agents-md](https://developers.openai.com/codex/guides/agents-md)、
[config-reference](https://developers.openai.com/codex/config-reference)。

- **发现链**：项目根由 `project_root_markers`（默认 `.git`）从 cwd 向上定位，
  随后从项目根到 cwd 逐目录收集指令文件；每目录按 `AGENTS.override.md` →
  `AGENTS.md` → `project_doc_fallback_filenames` 取第一个命中，**每目录至多
  一个文件**。全局层另读 `~/.codex/AGENTS.override.md`（否则 `AGENTS.md`）。
- **`AGENTS.override.md` 是同目录遮蔽**（2026-07-08）：根目录存在 override 时
  它完整取代根 `AGENTS.md` 进链——整个规则投射面静默失效，哨兵将其作为一级
  发现报告。官方文档对该文件是否建议 gitignore 仍无说明。
- **拼接语义**：全部命中文件按根到 cwd 顺序原样拼接（全局指令在前），层级间无
  替换 / 遮蔽；指令链按环境 cwd 构建（2026-07-08 更正，原记"会话启动时构建
  一次"；当前 main 支持多环境，每环境各建一条链），cwd 之下与旁系目录不扫描，
  也不随编辑位置动态加载。
- **预算**（2026-07-08）：`project_doc_max_bytes`（默认 32768 字节，即
  32 KiB）是项目根到 cwd 整条指令链的合并预算，按根在前的顺序消耗；越过剩余
  额度的那个文件被从中间截断，TUI 无任何提示，其后的文件整体跳过。全局层
  `~/.codex/AGENTS(.override).md` 不计入该预算、前置拼接。显式设
  `project_doc_max_bytes = 0` 会关闭整个项目指令面，哨兵对此报观察项。
  config-reference 上按逐文件预算的表述已过时。
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

## 对设计的影响

以下设计结论由 [sync-model](../implementation/sync-model.md) 持有，此处存目：

- 钩子投射目标是项目级 `.codex/hooks.json`，只有超出 Codex 承载能力的意图才
  落回常驻指令（语义降级）：Claude 独有事件、非 command 处理器、`async`
  后台钩子、`permissionDecision: "ask"`、工具输出重写。
- 技能受管副本写入 `.agents/skills/<name>/`。
- 技能的 bytes、host discoverability 与 live activation 分别验证；不为
  `.agents/skills/` 合成未经官方证实的 host-trust 状态。
- `[[skills.config]]` 保持用户本地所有权；M2 不生成或改写 Codex config。
- execpolicy 权限映射在 MVP 维持声明不同步。

## 实现前需要复核

- issue #17532 状态：项目级 `config.toml` 内联 hooks 是否已修复；实测
  `.codex/hooks.json` 在当前 CLI 的触发行为。
- `.agents/skills` 路径是否仍是官方项目级技能目录。
- Codex bundled validator、Agent Skills specification 与 runtime loader
  是否仍有字段差异；runtime 的宽松接受仍不得反向扩张公共格式。
- 分别 smoke test skill list 发现、显式调用与隐式调用；若用户级
  `[[skills.config]]` 覆盖影响结果，只记录环境事实，不改写该配置。
- hooks 的 `prompt` / `agent` 处理器与 `async` 是否已实装（影响可映射的
  意图范围）。
- hooks 信任流程的实际交互成本（首次信任、哈希变更重信任）对快路径体验的
  影响。
- 受管区块与投射内容对 `project_doc_max_bytes` 合并预算的占用；警戒阈值的
  标定留到有真实投射体量后进行。
- `AGENTS.override.md` 的 gitignore 定位（官方仍无说明）。
- 官方 skill 校验器与 Agent Skills 标准对 `compatibility` 键的差异是否消失；
  消失后再收窄对应兼容 lint。
