# Codex 能力面核验

采集日期：2026-07-24；Hooks 一节已于 2026-09-07 整体复核并重写，其余章节仍沿用
2026-07-24 的采集边界。主要来源为 Codex 官方文档
（learn.chatgpt.com/docs）、Agent Skills 官方规范与 openai/codex 官方仓库。
`developers.openai.com/codex/*` 已被上游重定向到 `learn.chatgpt.com/docs/*`：
hooks 一节的引用已改指新地址，其余章节保留旧链接，需在各自复核时逐条改指。
本文把官方文档记为 host contract，把固定提交源码记为带日期的 implementation
observation；源码观察不能反向扩张公开契约。issue / discussion 只保留为待复核
线索，不承担公共契约。哨兵观察项与注记的口径见
[report-spec](../../skills/bridge-sentinel/references/report-spec.md)。

这份核验梳理 Codex 的项目级配置能力面。结论：hooks、项目级技能、命令规则与
项目指令（`AGENTS.md`）都是原生机制，投射就是把内容写进各 host 的原生位置。

## Hooks：原生支持，已 GA

本节于 2026-09-07 全面复核，取代 2026-07-24 / 2026-07-25 的旧结论。公开契约来源
是 [Codex Hooks](https://learn.chatgpt.com/docs/hooks)（raw 版本为同址加 `.md`
后缀）：`developers.openai.com/codex/hooks` 已重定向到该地址，
`learn.chatgpt.com/docs/codex/hooks` 不是有效路径。实现观察取自 openai/codex
main 分支的
[`hook_config.rs`](https://github.com/openai/codex/blob/main/codex-rs/config/src/hook_config.rs)、
[`engine/discovery.rs`](https://github.com/openai/codex/blob/main/codex-rs/hooks/src/engine/discovery.rs)、
[`engine/command_runner.rs`](https://github.com/openai/codex/blob/main/codex-rs/hooks/src/engine/command_runner.rs)
与
[`tools/hook_names.rs`](https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/hook_names.rs)，
按带日期的 implementation observation 处理，不反向扩张公开契约。

- **状态**：实验版随 CLI v0.114 引入（约 2026-03），GA 约 2026-05-14；
  CLI 0.153.4 的 `codex features list` 报告 `hooks stable true`。
- **事件模型（复核：12 个，且存在 Codex 独有事件）**：`SessionStart`、
  `SessionEnd`、`SubagentStart`、`PreToolUse`、`PermissionRequest`、
  `PostToolUse`、`PreCompact`、`PostCompact`、`UserPromptSubmit`、
  `SubagentStop`、`Stop`、`Interrupt`。前 11 个在 Claude Code 同名存在；
  `Interrupt` 是第一个 Codex 独有事件，Claude 侧没有原生承载面。旧结论
  「11 个事件、无 Codex 独有事件」作废。12 个事件中只有 9 个处理 matcher，
  `UserPromptSubmit`、`Stop` 与 `Interrupt` 忽略 matcher。
- **timeout（复核）**：一般事件默认 600 秒、下限钳到 1 秒；只有 `SessionEnd` 与
  `Interrupt` 默认 1 秒、上限钳到 3 秒，越界静默钳制并给 warning。旧结论
  「command 默认 timeout 1 秒、最大 3 秒」只对这两个事件成立。
- **handler 类型（复核）**：`command`、`mcp_tool`、`prompt`、`agent` 四种可解析；
  `prompt` 与 `agent` 在 discovery 阶段被拒（"not supported yet"），`mcp_tool`
  已可执行。`async: true` 的 command handler 现在后台执行（最多 8 个并发，
  `SessionEnd` 始终同步），不再整体跳过。旧结论「只有 command 会执行、`async`
  被跳过」作废。
- **配置形式**：`hooks.json` 顶层是带 `hooks` 键的包装对象（可选顶层
  `description` 字符串），`hooks` 内为事件名键，值是「matcher 分组 → handler
  列表」。command handler 字段为 `command`、`commandWindows`、`timeout`、
  `async`、`statusMessage`、`additionalContextLimit`；分组字段为 `matcher`、
  `hooks`。也可在 `config.toml` 内联 `[[hooks.<Event>]]` 表。
- **未知键的严格程度（复核）**：`#[serde(deny_unknown_fields)]` 只加在
  `HooksFile` 顶层，`MatcherGroup` 与 `HookHandlerConfig` 都不拒绝未知键。因此
  顶层多一个键会让整份文件加载失败，而分组或 handler 内的未知键被静默忽略；
  不能把严格性描述到 handler 层。
- **配置层级**：用户级 `~/.codex/hooks.json`；**项目级
  `<repo>/.codex/hooks.json`**（也可写在项目 `.codex/config.toml`）；插件自带
  `hooks/hooks.json`；企业 `requirements.toml`。多层命中的 hook 全部执行，高层
  不覆盖低层，因此用户级与项目级各有一份等价 hook 时会执行两遍。
- **信任机制（复核细节）**：项目级 `.codex/` 层只在项目被信任后加载；逐 hook
  信任绑定一个 normalized identity 哈希，且该哈希在 timeout 取默认值与钳制
  **之后**计算。进入 identity 的是 event 名、`matcher`、`command`、归一化
  `timeout`、`statusMessage`、`async` 与归一化 `additionalContextLimit`；
  `commandWindows` **不在** identity 内，所以只改 Windows 分支不会使既有信任失效。
  持久状态是 `[hooks.state."<key>"] {enabled, trusted_hash}`，由 `/hooks` 经
  `ConfigBatchWrite`（`file_path: None`）写入**用户的 `config.toml`**；key 形如
  `<source>:<Event>:<groupIndex>:<handlerIndex>`，按位置编址，重排分组或 handler
  会静默孤立既有信任记录。`hook_trust_status()` 给出
  `Trusted | Modified | Untrusted | Managed`，未信任或已修改的 hook 在分发时被
  静默跳过，既不阻断也不在会话中提示。
- **协议与交付语义（复核）**：command hook 从 stdin 读 JSON（session_id、cwd、
  事件名、model、permission_mode 等），可返回 JSON 控制续行 / 提示
  （`continue`、`stopReason`、`systemMessage`、`suppressOutput`，其中
  `suppressOutput` 目前只解析未实装）；exit code 2 加 stderr 是统一的阻断语义。
  `SessionStart` 接受纯文本 stdout（作为 developer context 注入）与 JSON
  `hookSpecificOutput.additionalContext`；`Stop` 只接受 JSON 或 exit 2，纯文本
  对该事件无效。`SessionEnd` 有输入 schema 却没有输出 schema，属于
  fire-and-forget。模型可见的 hook 输出上限约 2500 tokens，超出部分写入临时文件。
- **PreToolUse 拦截范围与 tool_name 词汇（复核）**：`tool_name` 是开放集合。
  shell / unified exec 报 `Bash`（`tool_input.command`），文件编辑报
  `apply_patch`（matcher 别名 `Write` / `Edit`，别名只用于匹配、不进 stdin），
  子智能体报 `spawn_agent`（别名 `Agent`），其余本地函数工具报各自的扁平函数名
  （如 `update_plan`、`write_stdin`、`request_permissions`），MCP 工具报
  `mcp__<server>__<tool>`。`WebSearch` 等 hosted tool 不走本地函数工具的 hook
  路径，因此不会触发 hook；官方仍把 hooks 定位为 guardrail 而非完整
  enforcement boundary。matcher 是无锚定的 Rust 正则（不支持 lookahead 与反向
  引用），与 Claude「命中字符类就按精确列表、否则按 JS 正则」的双模语法不同形。
- **PermissionRequest 决策形状（复核）**：Codex 返回对象
  `decision: {behavior, ...}`，Claude 返回字符串 `allow | deny | ask`，两者
  **不同形**；Codex 的 `permissionDecision: "ask"` 仍未实装。旧结论「与 Claude
  同形，Claude 式 deny hook 原生可表达」作废。
- **Windows 执行与环境（复核）**：`commandWindows` 由会话检测到的 shell 执行，
  Windows 上检测无条件为 PowerShell：先 `pwsh`，回退 `powershell.exe`，只有在
  没有会话 shell 时才落到 `COMSPEC` / `cmd.exe /C`；argv 为
  `<shell> -NoProfile -Command <command>`。hook 进程先 `env_clear()` 再回放会话
  启动时捕获的环境快照，**项目级 hook 不获得任何 Codex 注入的环境变量**；
  `PLUGIN_ROOT` 等只注入插件来源的 hook。
- **对 Claude 的刻意兼容**：插件 hook 除 `PLUGIN_ROOT` / `PLUGIN_DATA` 外还注入
  `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA`（官方文档明言 "for
  compatibility"）。Codex 自带的 Claude 迁移器只搬运键集恰为 `{matcher, hooks}`
  的分组，以及键集属于
  `{type, command, timeout|timeoutSec, statusMessage, async}` 的 command
  handler，并丢弃 `async: true`、`asyncRewake`、`shell` 与 `once`；宿主自己也
  收敛到同一个跨 host 安全核心。
- **已知 bug（复核）**：
  [openai/codex#17532](https://github.com/openai/codex/issues/17532) 于
  2026-09-07 仍 open，最后活动 2026-05-21；其复现用的是 legacy
  `hooks = "<path>"` 指针键加已废弃的 `features.codex_hooks` 别名。投射目标因此
  固定为 `.codex/hooks.json`，并在同层检测到内联 `[hooks]` 表或该指针键时阻断：
  两种形态在同一层合并成两个位置 key 却共享同一个 normalized 哈希，hook 会执行
  两遍。

### 2026-09-07 的证据分层

本机实测（Windows 11 Pro 10.0.26200，Codex CLI 0.153.4；一次性临时项目或用后即删
的临时 carrier，未修改用户配置）：

- 未受信任的项目不加载 `.codex/` 层；`-c projects.<path>.trust_level` 的命令行
  覆盖也不能让它加载，项目信任只从用户配置文件的 `projects` 表读取。
- 未受信任的 hook 在 `codex exec` 中被静默跳过，`--json` 流里没有任何提示；只有
  加上 `--dangerously-bypass-hook-trust` 才运行。该标志仅用于这次人工取证，绝不
  进入夹具或 CI 路径。
- `SessionStart`、`UserPromptSubmit`、`Stop`、`SessionEnd`、`PreToolUse` 与
  `PostToolUse` 都在 `codex exec` 中触发，并带上文所述的 stdin 信封；shell 工具
  向 hook 报 `tool_name: "Bash"`。
- Windows 上只有 `commandWindows` 分支运行，四个被测事件全部如此；实测 shell 为
  pwsh 7.6.5，`echo %COMSPEC%` 原样写出字面量。
- `SessionStart` 的纯文本 stdout 与脚本文件输出的 `additionalContext` 都被注入
  模型；单独的 `systemMessage` 不可见；经内联 `cmd /c echo` 输出的 JSON 信封被
  引号处理破坏、未送达。输出 JSON 信封的 hook 必须是提交进仓库的脚本文件。
- 当天 7 次 `codex exec` 中有 1 次完全没有触发任何 hook，原因不明。hook 执行必须
  按「观察到的行为」处理，绝不作为边界或保证。

源码复核（openai/codex main 分支，未在本机运行）：`deny_unknown_fields` 的作用
范围、trust identity 的字段构成与计算时机、`[hooks.state."<key>"]` 的写入文件与
位置化 key、Windows shell 的选择顺序与环境快照、`tool_name` 词汇表，以及 12 个
事件的 serde 重命名与 `SessionStart` / `Stop` 的输出语义。

尚未验证、不得作为实现依据：交互式 `/hooks` 的完整信任流程（首次信任后不加 bypass
也能运行、改动 identity 字段后变为 Modified），以及状态记录落盘位置的现场确认。
装机的用户 `config.toml` 当前没有任何 `hooks` 行，`~/.codex` 下也没有 hook 命名的
文件，因此这一项必须由一次人工 TUI 会话补齐。

## notify：被 hooks 取代的窄机制

来源：[config-advanced](https://developers.openai.com/codex/config-advanced)
（链接为 2026-07-24 采集，已重定向到 learn.chatgpt.com/docs/*，待本节复核时改指）。

`notify` 在事件发生时调外部程序，但只有一个事件（`agent-turn-complete`），且
**仅用户级生效**——官方明确项目级配置不能覆盖 notify 键。生命周期自动化应走
hooks，notify 不作为投射目标。

## Rules（execpolicy）：命令审批的项目级规则

来源：[developers.openai.com/codex/rules](https://developers.openai.com/codex/rules)
（链接为 2026-07-24 采集，已重定向到 learn.chatgpt.com/docs/*，待本节复核时改指）。

- `.rules` 文件用 Starlark 编写 `prefix_rule(pattern, decision, ...)`，decision
  为 `allow | prompt | forbidden`；多规则命中时最严者胜；shell 链
  （`&&`、`;`、`|`）逐段评估。
- 位置：用户级 `~/.codex/rules/`，**项目级 `<repo>/.codex/rules/`**（同样受
  信任门槛）。`codex execpolicy check` 可离线测试。
- 与 `approval_policy`（`untrusted | on-request | never`）同属执行语义。这与
  Claude 的 permissions 规则在语义上是对应物，且两侧都是文件化配置面——
  维持"声明不同步"；两侧映射面都已存在，可作未来映射立项候选。

## 技能：格式、运行时、校验器与行为可移植性分层

来源：[Codex skills 文档](https://developers.openai.com/codex/skills)
（链接为 2026-07-24 采集，已重定向到 learn.chatgpt.com/docs/*，待本节复核时改指）、
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

公开契约来源：
[AGENTS.md 指南](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、
[Advanced Configuration](https://learn.chatgpt.com/docs/config-file/config-advanced#project-root-detection)
与
[Worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees#copy-ignored-local-files-into-managed-worktrees)。
实现观察固定在 openai/codex 提交
[`0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1`](https://github.com/openai/codex/commit/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1)，
主要证据为
[`agents_md.rs`](https://github.com/openai/codex/blob/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1/codex-rs/core/src/agents_md.rs)、
[`agents_md_manager.rs`](https://github.com/openai/codex/blob/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1/codex-rs/core/src/agents_md_manager.rs)
与
[`codex-home/src/instructions/mod.rs`](https://github.com/openai/codex/blob/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1/codex-rs/codex-home/src/instructions/mod.rs)。

- **发现链（host contract）**：项目根由 `project_root_markers`（默认 `.git`）
  从 cwd 向上定位；空 marker 列表不搜索父目录，并把当前 cwd 当项目根。随后从
  项目根到 cwd 逐目录收集指令文件；每目录按 `AGENTS.override.md` →
  `AGENTS.md` → `project_doc_fallback_filenames` 取第一个命中，**每目录至多
  一个文件**。全局层另读 `$CODEX_HOME/AGENTS.override.md`（否则
  `AGENTS.md`）。
- **override 与 fallback（host contract）**：`AGENTS.override.md` 完整遮蔽
  同目录的 `AGENTS.md`；`AGENTS.md` 又遮蔽同目录 fallback。因此 root override
  会使 Bridge 的 root target 不进入链，而新建 root `AGENTS.md` 可能使原先通过
  fallback 生效的指导退出链。Bridge policy 是写前观察有效 root markers、
  override 与 fallback，并在会丢失既有上下文时要求收编 / 用户决策；不是改写
  用户级 config。
- **ignored override 的 managed-worktree 特例（host contract）**：本地
  ChatGPT desktop 管理的 worktree 会自动复制被 ignore 的
  `AGENTS.override.md`，无需把它列入 `.worktreeinclude`。官方明确把该行为限定在
  local managed worktree；remote worktree 与用户通过 CLI 自建的 worktree
  不在保证范围内。官方没有给普通仓库一个普遍的 “override 应当 gitignore”
  规范。
- **拼接与生命周期（host contract）**：项目文件按 root→cwd 进入组合上下文，
  deeper 文件因位置靠后获得软 precedence；cwd 以下和旁系目录不扫描，也不随
  正在编辑的文件动态加载。官方文档明确指令链在每个 run 启动时构建，TUI 通常是
  每个已启动 session 一次；配置变化需要新 command / restart。
- **cache 细节（implementation observation，2026-07-24）**：固定提交在 session
  初始化加载指令；每回合虽然调用 refresh，但 cache key 只包含 environment
  selection 列表。列表不变时不会重读文件，selection 变化时才按每个 environment
  cwd 重建一条链。该行为解释当前 main 的多环境实现，但不是 Bridge 可依赖的
  host contract；写入后仍应提示新 run / session 才能验证 activation。同一固定
  提交还在计算 root markers 时排除 project config layers；这是实现观察，公开
  文档没有承诺项目 `.codex/config.toml` 能改变对其自身的根发现。
- **预算（host contract + implementation observation）**：
  `project_doc_max_bytes` 默认 32768 字节（32 KiB），是项目 root→cwd **组合**
  guidance 的预算，而非每文件各一份。固定提交进一步证实预算按每个 selected
  environment 的链独立计算、root-first 消耗；跨越剩余额度的文件按字节中途截断，
  后续文件跳过；`0` 关闭整个项目指令面。全局
  `$CODEX_HOME/AGENTS(.override).md` 独立读取、trim 后前置，不计 project
  budget。当前源码写 tracing warning，但公开 UI 没有承诺可见的截断提示。
  Advanced Configuration 同页仍写 “from each AGENTS.md file”，与更专门的
  AGENTS.md 指南及固定提交实现冲突；本文采用后两者，并保留该文档漂移观察。
- **字节与解码（implementation observation，2026-07-24）**：固定提交先按字节
  读取 / 截断，再以 `String::from_utf8_lossy` 解码；合法 UTF-8 内容不解析
  frontmatter，不展开 `@path`，不支持 glob / 条件作用域，也不剥离 HTML 注释。
  截断若切开多字节字符会产生 U+FFFD，所以准确表述是“字节预算、无内嵌语义
  预处理”，不是任意 raw bytes 原封不动进入 prompt。受管区块标记会进入模型
  上下文并占用预算，应保持精简。
- **没有分片机制**：Codex 没有 `.claude/rules/*.md` 的等价物（官方
  [customization](https://developers.openai.com/codex/concepts/customization)
  页枚举的模型面只有 AGENTS.md / Memories / Skills / MCP / Subagents；链接为
  2026-07-24 采集，已重定向到 learn.chatgpt.com/docs/*，待本节复核时改指）；嵌套
  AGENTS.md 是唯一原生多文件指令形态。规则分片注入 `AGENTS.md` 受管区块就是
  投射到原生指令面，path-scoped 语义走适用性前言。适用性前言是 Bridge 的
  attention-scoping policy，不是 Codex 的机械 path enforcement。

## 其余机制速记

- **Automations**（[app/automations](https://developers.openai.com/codex/app/automations)，
  链接为 2026-07-24 采集，已重定向到 learn.chatgpt.com/docs/*，待本节复核时改指）：
  Codex app 专属的定时任务（支持 cron 表达式），在本机后台 worktree 运行；
  CLI / IDE 无此机制。属调度自动化，与 hooks 的事件自动化互补，MVP 不涉及。
- **Custom prompts 已废弃**（[custom-prompts](https://developers.openai.com/codex/custom-prompts)，
  链接为 2026-07-24 采集，已重定向到 learn.chatgpt.com/docs/*，待本节复核时改指）：
  官方建议改用技能。
- **Local Environments**（app）：worktree 创建时执行 setup 脚本，配置存于项目
  `.codex/` 并可入库。
- Codex app 设置面板的「编码」区（钩子 / 连接 / Git / 环境 / 工作树）与上述
  文件机制一一对应；hooks 定义本身是文件，**可随仓库共享**。可共享也意味着它会
  被每个 clone 拿到：Codex 侧还有项目信任与逐 hook 信任两道门，Claude 侧没有，
  所以提交进仓库的 hook 是评审问题而不是配置问题。

## 项目级配置面汇总

Codex 读取的项目级配置：`AGENTS.md`（含根到 cwd 链上的嵌套文件与
`AGENTS.override.md`）与 `.agents/skills/`（注意根目录是 `.agents` 不是
`.codex`）；受信任门槛的 `.codex/` 层——`config.toml`（不可覆盖 provider /
auth / notify 等机器本地键）、`hooks.json`、`rules/*.rules`、`agents/*.toml`
（项目级 subagent 定义，仅作用于该 subagent 会话）。

## 对设计的影响

以下设计结论由 [sync-model](../implementation/sync-model.md) 持有，此处存目：

- 钩子投射目标是项目级 `.codex/hooks.json`，且是 Codex 唯一写目标；同层内联
  `[hooks]` 或 legacy 指针键会造成双重注册，检测到就阻断该 closure。
- 语义降级只对 `reminder` / `observation` 意图开放，且只在该 event 在目标侧
  没有原生承载面时成立：Claude 独有事件在 Codex 侧落到 root `AGENTS.md` 常驻
  指令，Codex 独有的 `Interrupt` 在 Claude 侧由意图文档自身承载（零写入）。
  非 command 处理器、`async` 后台钩子、`permissionDecision: "ask"` 与
  `PermissionRequest` 的决策形状差异都不降级，而是以 `declared-unsynced` 如实
  声明：它们的效果是运行期否决，散文不能替代。
- Codex 逐 hook 信任按位置编址且哈希覆盖 `statusMessage`，所以受管组只追加、
  不重排，Codex 侧的 `[bridge:<id>]` 标记只在创建时写。
- 技能受管副本写入 `.agents/skills/<name>/`。
- 技能的 bytes、host discoverability 与 live activation 分别验证；不为
  `.agents/skills/` 合成未经官方证实的 host-trust 状态。
- `[[skills.config]]` 保持用户本地所有权；M2 不生成或改写 Codex config。
- execpolicy 权限映射在 MVP 维持声明不同步。
- entry / rules 的 Bridge policy 同样把 repo bytes、host discoverability 与
  live activation 分开：root `AGENTS.md` 中存在完整 managed block 只证明投射
  bytes；有效 root markers、无同目录 override、非零且足够的组合预算才支撑
  discoverability；新 run / session 的加载证据才支撑 activation。
- 新建 `AGENTS.md` 会按 host priority 遮蔽同目录 fallback。Bridge 不改用户
  `$CODEX_HOME/config.toml`；写前应把有效 fallback 和其内容丢失风险纳入同一
  aggregate plan，必要时要求收编或用户决策。
- 同一物理 `AGENTS.md` 的受管分片必须聚合计划并保护 manual zone；只有在按实际
  文件顺序、marker bytes 与有效 `project_doc_max_bytes` 计算后，完整受管区块
  仍位于可加载前缀内，才能声称该 target 可发现。该规则是由 host 预算推导出的
  Bridge policy，不是 Codex 自带的事务保证。

## 实现前需要复核

- issue #17532 是否修复（2026-09-07 复核仍 open）。项目级 `.codex/hooks.json` 在
  当前 CLI 的触发行为已于同日实测，见上文证据分层。
- 交互式 `/hooks` 的完整信任流程与 `[hooks.state."<key>"]` 的实际落盘位置：源码
  层已定位到用户 `config.toml`，但装机上尚未观察到真实写入，需要一次人工 TUI
  会话确认。这是 hooks 知识条目上唯一未闭合的阻塞项。
- `.agents/skills` 路径是否仍是官方项目级技能目录。
- Codex bundled validator、Agent Skills specification 与 runtime loader
  是否仍有字段差异；runtime 的宽松接受仍不得反向扩张公共格式。
- 分别 smoke test skill list 发现、显式调用与隐式调用；若用户级
  `[[skills.config]]` 覆盖影响结果，只记录环境事实，不改写该配置。
- hooks 的 `prompt` / `agent` 处理器是否已实装（2026-09-07 仍在 discovery 阶段
  被拒；`mcp_tool` 与 `async` 已实装，见上文）。
- hooks 信任流程的实际交互成本（首次信任、identity 变更重信任）对快路径体验的
  影响；`commandWindows` 不进 identity 这一盲区是否在后续版本收敛。
- Codex 事件清单是否继续增长（12 个为 2026-09-07 快照），以及 9 / 12 的 matcher
  适用面是否变化。
- 受管区块与投射内容对 `project_doc_max_bytes` 合并预算的占用；警戒阈值的
  标定与“区块不完整即阻断”的 contract-owner 决策。
- 有效 `project_root_markers`、fallback names、root override 与 budget=0 对
  当前 repo discoverability 的影响；只记录环境事实，不修改用户配置。
- openai/codex 后续版本是否改变 session-init /
  environment-selection cache 语义；公开契约仍以每 run / TUI session 为准。
- ignored `AGENTS.override.md` 自动复制是否仍只限本地 ChatGPT desktop managed
  worktree，不把该特例推广为普通 CLI / remote worktree 契约。
- Advanced Configuration 的 per-file budget 措辞是否与 AGENTS.md 指南和实现
  重新对齐。
- 官方 skill 校验器与 Agent Skills 标准对 `compatibility` 键的差异是否消失；
  消失后再收窄对应兼容 lint。
