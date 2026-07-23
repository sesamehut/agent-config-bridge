# Host 上下文加载行为核验

采集日期：2026-07-07；2026-07-08 与 2026-07-23 复核增补（见同名小节）。主要来源为 Claude
Code 官方文档
（[How Claude remembers your project](https://code.claude.com/docs/en/memory)）与
GitHub issue 追踪。进入实现前需按本文档日期重新核验。

这份核验用于支撑两个设计决策：入口文件方向（`CLAUDE.md` 为源、`AGENTS.md` 为
投射面）与受管区块标记的成本判断。

## Claude Code 端结论

- **Claude Code 只读 `CLAUDE.md`，不读 `AGENTS.md`**。官方文档明确表述
  "Claude Code reads `CLAUDE.md`, not `AGENTS.md`"；请求原生支持 `AGENTS.md` 的
  issue（[anthropics/claude-code#34235](https://github.com/anthropics/claude-code/issues/34235)）
  截至采集日仍处 open、无路线图承诺。官方给出的桥接方式是在 `CLAUDE.md` 中写
  `@AGENTS.md` import。
- **import 机制**：启动时解析；路径相对包含文件解析；最大递归 4 跳；项目外路径
  首次使用需要用户确认。
- **HTML 注释在注入上下文前被剥离**：`CLAUDE.md` 系文件中的 `<!-- ... -->` 不进
  运行时上下文，但用 Read 工具读文件时仍可见。受管 / 排除标记语法因此零运行时
  成本、编辑时完整可见。
- **`.claude/rules/*.md`**：递归发现，支持 `paths` frontmatter 做路径作用域，
  支持 symlink 共享。
- **Windows 上 symlink 需要管理员权限或开发者模式**：跨工具共享文件不宜依赖
  symlink；投射选择 copy 与受管区块。
- **`/init` 会读取既有 `AGENTS.md` 并整合**：Codex 起点项目的收编方向与官方行为
  一致。
- **`CLAUDE.md` 是上下文不是强制**：官方将其定位为 context；硬约束需走 hooks。
  这与"hook 与常驻指令同为提示词注入、差别在投递确定性与事件邻近性"的分层判断
  一致。

## Codex 端对照（与标记成本直接相关）

Codex 侧机制细节见 [codex-capability-surface.md](codex-capability-surface.md)
（2026-07-07），此处只记影响本文档结论的差异：

- **Codex 不剥离 HTML 注释**：`AGENTS.md` 按原始字节拼进 prompt，
  `<!-- bridge:managed:* -->` 受管标记在 Codex 侧进入模型上下文，并与投射内容
  一同占用 `project_doc_max_bytes` 总预算（默认 32 KiB，超出截断）。标记成本
  按 host 分列：Claude 侧零运行时成本，Codex 侧标记应保持精简。
- **`AGENTS.md` 不解析 frontmatter / `paths` 作用域**：作用域只能靠目录放置，
  嵌套文件仅在 cwd 位于对应目录之下时加载、不随编辑位置动态选取——
  path-scoped 分片仍以显式适用性前言投射。

## 2026-07-08 复核增补

采集日期：2026-07-08。来源同上（官方文档与 issue 追踪复查）。

- **注释剥离收窄为块级**：Claude 剥离的是 `CLAUDE.md` 系文件（含
  `.claude/rules/*.md`）中的块级 HTML 注释；代码块内的注释原样保留。此前
  "HTML 注释在注入上下文前被剥离"的表述据此收窄——受管 / 排除标记按块级注释
  书写即可维持零运行时成本的结论不变。
- **项目入口有两个官方位置**：`CLAUDE.md` 与 `.claude/CLAUDE.md` 都是官方项目
  入口位置，二者可共存，共存是内容分叉隐患；哨兵把共存作为观察项报告。
- **Claude hooks 面已扩大**：文档化事件 29 个，处理器类型 5 种（`command`、
  `http`、`mcp_tool`、`prompt`、`agent`）；`timeout` 单位为秒；settings 中的
  hooks 配置改动由文件监视器捕获，无需重启会话。未知事件名应按"晚于采集日期的
  新增"处理，不视为非法。
- **`claudeMdExcludes` 语义**：可写在任意 settings 层；glob 按绝对路径匹配，
  相对形态的模式需加 `**/` 前缀；多层的数组合并生效。它只覆盖 memory 系文件：
  被排除 glob 之下的 CLAUDE.md 与 rules 分片都被排除，但不覆盖嵌套
  `.claude/skills/`。
- **夹具泄漏相关事实**：嵌套 CLAUDE.md 与嵌套 `.claude/skills/` 会被根目录
  会话惰性发现并加载；settings 文件没有向下或向上发现——项目 settings 只从
  会话起始目录加载。这组事实支撑本仓库的夹具围栏：根 `.claude/settings.json`
  的 `claudeMdExcludes` 围栏，加上"不在 `fixtures/` 内启动工作会话"的约定。
  2026-07-23 复核确认 `skillOverrides` 可按技能名设为 `"off"`；但项目
  settings 只从会话起始目录加载，而嵌套 `.claude/skills/` 会被根会话惰性
  发现（同日在本仓库实测复现：仅有夹具本地 settings 时，根会话仍会发现并
  注册嵌套夹具技能，唯一未被发现的是仍带 `disable-model-invocation` 的那
  个），因此夹具项目和仓库根的 settings 必须各自携带同一份 override 清单。
  `skillOverrides` 能否压制惰性发现的嵌套技能官方未记载，无害正文是最后
  兜底；即便如此，这仍比在每个被测 `SKILL.md` 中塞入 Claude 专属
  frontmatter 更适合测试真正的可移植子集。
- **rules frontmatter 的未知键容忍度官方未说明**：`paths` 是唯一文档化的
  rules frontmatter 键，对额外 `bridge` 键的容忍度需要实测。实测在 M1 实现
  波次内、`bridge` 键在本仓库 `.claude/rules/fixtures.md` 上线之前完成；带
  日期的结果与当前生效的意图记录形态记录在
  [knowledge/entry-and-rules.md](../../knowledge/entry-and-rules.md)。
- **更正 Codex 指令链构建时机的表述**：指令链按环境 cwd 构建（当前 main 支持
  多环境，每个环境各建一条链），从不跟随被编辑文件，也从不向 cwd 之下扫描。
  此前"指令链在会话启动时构建一次"的表述据此更正；链的重建时机仍待观察。

## 对设计的影响

- `AGENTS.md` 不被 Claude 读取，因此可以安全地作为面向 Codex 的投射面，承载规则
  分片的结构降级注入，不会造成 Claude 侧内容重复。
- 替代方案"`AGENTS.md` 作共享入口、`CLAUDE.md` 写 `@AGENTS.md` 垫片"不采用：
  在"规则分片必须注入 `AGENTS.md`"的前提下，它会让 Claude 经 import 与
  `.claude/rules/` 原生发现重复读取分片内容。

## 实现前需要复核

- Claude Code 是否新增了 `AGENTS.md` 原生支持（issue #34235 状态）。
- HTML 注释剥离行为是否仍然成立（2026-07-08 已复核并收窄为块级；标记成本判断
  依赖它，写侧实现前再核验一次）。
- rules frontmatter `bridge` 键的实测结论是否已按
  [knowledge/entry-and-rules.md](../../knowledge/entry-and-rules.md) 记录、
  当前生效的意图记录形态（frontmatter 还是注释回退）是否与仓库实际一致。
- Claude hooks 事件清单是否继续增长（29 个为 2026-07-08 快照；未知事件名按
  新增处理）。
- `claudeMdExcludes` 的覆盖范围（memory 系文件，不含技能）是否变化——本仓库
  的夹具围栏依赖它。
- Codex 侧机制（hooks、技能目录、rules、项目级配置面）已由
  [codex-capability-surface.md](codex-capability-surface.md) 单独核验
  （2026-07-07，2026-07-08 增补），按该文档的复核清单跟进。
