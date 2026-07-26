# Host 上下文加载行为核验

采集日期：2026-07-24。Claude Code 的公开契约以
[How Claude remembers your project](https://code.claude.com/docs/en/memory)
与 [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands)
为准；Codex 对照以官方文档和 openai/codex 固定提交的实现为准。本文区分三种
证据等级：官方文档是 host contract；固定提交源码只是带日期的 implementation
observation；本仓库的 live smoke test 是 empirical observation。后两者都不能
反向扩张公开契约。官方仓库 issue 只用于记录尚未承诺的请求状态。

这份核验用于支撑两个设计决策：入口文件方向（`CLAUDE.md` 为源、`AGENTS.md` 为
投射面）与受管区块标记的成本判断。

## Claude Code 端结论

- **Claude Code 只读 `CLAUDE.md`，不读 `AGENTS.md`**。官方文档明确表述
  "Claude Code reads `CLAUDE.md`, not `AGENTS.md`"；请求原生支持 `AGENTS.md` 的
  issue（[anthropics/claude-code#34235](https://github.com/anthropics/claude-code/issues/34235)）
  截至采集日仍处 open、无路线图承诺。官方给出的桥接方式是在 `CLAUDE.md` 中写
  `@AGENTS.md` import。
- **项目入口有两个官方位置**（2026-07-24 复核）：官方写法是项目入口可位于
  `CLAUDE.md` **或** `.claude/CLAUDE.md`，但没有规定二者同时存在时的加载顺序
  或 precedence。Bridge 对双入口采用 fail-closed policy：二者都不胜出，必须报告
  需要用户决策的分叉风险。
- **import 机制**：启动时解析；路径相对包含文件解析；最大递归 4 跳；Markdown
  code span 与 fenced code block 内不解析 import；项目外路径首次使用需要用户
  确认。
- **块级 HTML 注释剥离的证据边界**：官方明确承诺 `CLAUDE.md` 文件中的块级
  `<!-- ... -->` 在注入前剥离，代码块内注释保留，用 Read 工具直接读取时仍可见。
  官方文字没有把这项承诺明确扩展到 `.claude/rules/*.md`；规则分片中的注释剥离
  只由 2026-07-21 的本仓库 live observation 支撑。因此入口文件标记可按官方
  契约视为零上下文成本，规则分片标记的零成本只能标 empirical、随 host 版本复核。
- **`.claude/rules/*.md`**：递归发现，支持 `paths` frontmatter 做路径作用域，
  支持 symlink 共享。`paths` 是唯一文档化的 rules frontmatter 键，未知键容忍度
  官方未说明（2026-07-08）；额外 `bridge` 键的容忍度已实测（M1 实现波次内、
  先于 `bridge` 键在本仓库 `.claude/rules/fixtures.md` 上线），带日期的结果与
  当前生效的意图记录形态记录在
  [knowledge/entry-and-rules.md](../../knowledge/entry-and-rules.md)。无 `paths`
  的规则在启动时常驻；带 `paths` 的规则只在 Claude 读取匹配文件时触发，不随每次
  tool use 触发。当前官方还规定：同一规则的整个 `paths` 列表共享 1000 个展开
  pattern / 4 MiB brace-expansion 预算；超限 pattern 保持未展开，字面花括号
  匹配不到文件；无法解析的 `[` bracket pattern 匹配不到文件，但不阻断同规则
  其余 pattern。Bridge 不能把这类 host no-op pattern 静默投射成 Codex 常驻规则。
- **`claudeMdExcludes` 语义**（2026-07-08）：可写在任意 settings 层；glob 按
  绝对路径匹配，相对形态的模式需加 `**/` 前缀；多层的数组合并生效。它只覆盖
  memory 系文件：被排除 glob 之下的 CLAUDE.md 与 rules 分片都被排除，但不覆盖
  嵌套 `.claude/skills/`。
- **夹具泄漏相关事实**：嵌套 CLAUDE.md 与嵌套 `.claude/skills/` 会被根目录会话
  惰性发现并加载；settings 没有向下或向上发现，项目 settings 只从会话起始目录
  加载（2026-07-08）。`skillOverrides` 可按技能名设为 `"off"`（2026-07-23）；
  同日在本仓库实测：仅有夹具本地 settings 时，根会话仍会发现并注册嵌套夹具
  技能（唯一未被发现的是仍带 `disable-model-invocation` 的那个），因此夹具
  项目和仓库根的 settings 必须各自携带同一份 override 清单。`skillOverrides`
  能否压制惰性发现的嵌套技能官方未记载，无害正文是最后兜底（比在被测
  `SKILL.md` 中塞入 Claude 专属 frontmatter 更适合测试真正的可移植子集）。这组事实支撑根
  `.claude/settings.json` 的 `claudeMdExcludes` 围栏与"不在 `fixtures/` 内启动
  工作会话"的约定。
- **skill 内容先渲染再进入上下文**：Claude Code 调用 skill 时会替换
  `$ARGUMENTS`、`$ARGUMENTS[N]` / `$N`、由 `arguments` 声明的 `$name`，以及
  `${CLAUDE_SESSION_ID}`、`${CLAUDE_EFFORT}`、`${CLAUDE_SKILL_DIR}`、
  `${CLAUDE_PROJECT_DIR}`。它还会在注入前执行行内 `` !`command` `` 与
  以 `!` 标记的 fenced shell block，用输出替换原占位；随后将渲染
  结果作为一条消息加入会话。`allowed-tools` 另行只授予调用当回合的免询问权限，
  并非正文转换，也不限制其他工具；项目 skill 的该权限效果受 workspace trust
  约束。
- **Windows 上 symlink 需要管理员权限或开发者模式**：跨工具共享文件不宜依赖
  symlink；投射选择 copy 与受管区块。
- **`/init` 读取 `AGENTS.md` 有条件**：默认 `/init` 读取 Cursor rules 与
  Copilot instructions；只有设置 `CLAUDE_CODE_NEW_INIT=1` 的新流程才额外读取
  `AGENTS.md`、Devin、Windsurf 与 Cline 规则。Bridge 的 Codex 起点收编不能依赖
  默认 `/init`。
- **`CLAUDE.md` 是上下文不是强制**：官方将其定位为 context；硬约束需走 hooks。
  这与"hook 与常驻指令同为提示词注入、差别在投递确定性与事件邻近性"的分层判断
  一致。
- **Claude hooks 面**（2026-07-08）：文档化事件 29 个，处理器类型 5 种
  （`command`、`http`、`mcp_tool`、`prompt`、`agent`）；`timeout` 单位为秒；
  settings 中的 hooks 配置改动由文件监视器捕获，无需重启会话。未知事件名应按
  "晚于采集日期的新增"处理，不视为非法。

## Codex 端对照（与标记成本直接相关）

Codex 侧机制细节见 [codex-capability-surface.md](codex-capability-surface.md)
（2026-07-24），此处只记影响本文档结论的差异：

- **Codex 不做内嵌语义预处理**：固定提交
  [`0dfa778` 的 `agents_md.rs`](https://github.com/openai/codex/blob/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1/codex-rs/core/src/agents_md.rs)
  先按字节读取和截断，再用 `String::from_utf8_lossy` 解码；合法 UTF-8 的
  frontmatter、HTML 注释与 `@path` 都原样成为文本，不被解释或剥离。截断若切开
  多字节字符会产生替换字符，因此不能再表述为任意 raw bytes 原封不动进入
  prompt。受管标记会进入上下文并占用项目指令预算。
- **`AGENTS.md` 不解析 frontmatter / `paths` 作用域**：path-scoped 分片仍以
  显式适用性前言投射。
- **发现链受运行环境影响**：[官方 AGENTS.md 指南](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
  按 `AGENTS.override.md` → `AGENTS.md` → fallback 每目录取一个文件；
  `project_root_markers` 默认 `.git`，设为空数组会把当前 cwd 当根。创建 root
  `AGENTS.md` 会遮蔽同目录原本生效的 fallback；root override 则会遮蔽 Bridge
  target。这些都是写前需观察的 host state，Bridge policy 是报告并要求收编 /
  决策，而不是改写用户配置。
- **生命周期**：公开契约是每个 run（TUI 通常每个启动 session）构建一次指令链。
  固定提交的
  [`AgentsMdManager`](https://github.com/openai/codex/blob/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1/codex-rs/core/src/agents_md_manager.rs)
  在 session 初始化加载；每回合虽调用 refresh，但 environment selection 列表
  未变化时直接复用 cache，只有 selection 变化才重建。后者是 implementation
  observation，不是可依赖的 host contract；投射后仍应要求新 run / session。
- **managed-worktree 特例**：[官方 worktree 文档](https://learn.chatgpt.com/docs/environments/git-worktrees#copy-ignored-local-files-into-managed-worktrees)
  说明被 ignore 的 `AGENTS.override.md` 会自动复制进本地 ChatGPT desktop 管理的
  worktree，无需 `.worktreeinclude`；该保证不适用于 remote worktree 或用户从
  CLI 自建的 worktree。
- **Codex skill 没有对应的动态渲染阶段**：openai/codex 固定提交 `44d76c6`
  的
  [显式注入路径](https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/core-skills/src/injection.rs)
  读取 `SKILL.md` 后把 `contents` 原样交给 prompt injection。因此上述 Claude
  占位符和 shell injection 语法在 Codex 中保留为原文；模型随后可能把它们当
  普通指令解释，但这不等同于宿主预处理，也不能标为行为等价。

## 对设计的影响

- `AGENTS.md` 不被 Claude 读取，因此可以安全地作为面向 Codex 的投射面，承载规则
  分片的结构降级注入，不会造成 Claude 侧内容重复。
- 替代方案"`AGENTS.md` 作共享入口、`CLAUDE.md` 写 `@AGENTS.md` 垫片"不采用：
  在"规则分片必须注入 `AGENTS.md`"的前提下，它会让 Claude 经 import 与
  `.claude/rules/` 原生发现重复读取分片内容。
- 双入口时 `neither wins` 的 fail-closed 仲裁、root managed-block carrier 与
  适用性前言都是 Bridge policy；host 事实只说明可用入口和加载机制。实现与报告
  不得把这些策略写成官方 precedence、机械路径约束或 enforcement。
- 任意有效 `@path` import 都会在 Claude 侧展开、在 Codex 侧保持普通文本；不仅
  `@AGENTS.md` 有 fidelity gap。Bridge 必须把内部 tracked import closure、
  外部 / 未跟踪 import 与自引用 import 分开仲裁，不能仅凭投射 bytes 一致声称
  行为一致。
- Codex 的适用性前言只是 attention scoping。schema-invalid、全部 no-op 或超过
  Claude glob expansion 预算的 `paths` 不能静默扩大成 Codex unconditional
  guidance；具体阻断 / 降级策略由 contract owner 定义。

## 实现前需要复核

- Claude Code 是否新增了 `AGENTS.md` 原生支持（issue #34235 状态）。
- `.claude/rules/*.md` 的块级 HTML 注释剥离 observation 是否仍然成立；官方
  `CLAUDE.md` 保证本身已于 2026-07-24 复核。
- rules frontmatter `bridge` 键的实测结论是否已按
  [knowledge/entry-and-rules.md](../../knowledge/entry-and-rules.md) 记录、
  当前生效的意图记录形态（frontmatter 还是注释回退）是否与仓库实际一致。
- Claude `paths` glob 语法、brace-expansion 预算与 no-op pattern 是否仍与
  2026-07-24 官方说明一致。
- Claude hooks 事件清单是否继续增长（29 个为 2026-07-08 快照）。
- `claudeMdExcludes` 的覆盖范围是否变化——本仓库的夹具围栏依赖它。
- Codex 侧机制按 [codex-capability-surface.md](codex-capability-surface.md) 的
  复核清单跟进，特别是公开文档与固定提交源码的 budget 措辞、environment
  selection cache、root markers、fallback 与 managed-worktree 特例。
