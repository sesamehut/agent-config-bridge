# Host 上下文加载行为核验

采集日期：2026-07-07；2026-07-08 与 2026-07-23 的复核增补已并入正文，逐条标注
日期。主要来源为 Claude Code 官方文档
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
- **项目入口有两个官方位置**（2026-07-08）：`CLAUDE.md` 与 `.claude/CLAUDE.md`
  可共存，共存是内容分叉隐患；哨兵把共存作为观察项报告。
- **import 机制**：启动时解析；路径相对包含文件解析；最大递归 4 跳；项目外路径
  首次使用需要用户确认。
- **块级 HTML 注释在注入上下文前被剥离**：`CLAUDE.md` 系文件（含
  `.claude/rules/*.md`）中的块级 `<!-- ... -->` 不进运行时上下文，代码块内的
  注释原样保留（2026-07-07 采集，2026-07-08 复核收窄为块级）；用 Read 工具读
  文件时仍可见。受管 / 排除标记按块级注释书写，零运行时成本、编辑时完整可见。
- **`.claude/rules/*.md`**：递归发现，支持 `paths` frontmatter 做路径作用域，
  支持 symlink 共享。`paths` 是唯一文档化的 rules frontmatter 键，未知键容忍度
  官方未说明（2026-07-08）；额外 `bridge` 键的容忍度已实测（M1 实现波次内、
  先于 `bridge` 键在本仓库 `.claude/rules/fixtures.md` 上线），带日期的结果与
  当前生效的意图记录形态记录在
  [knowledge/entry-and-rules.md](../../knowledge/entry-and-rules.md)。
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
- **Windows 上 symlink 需要管理员权限或开发者模式**：跨工具共享文件不宜依赖
  symlink；投射选择 copy 与受管区块。
- **`/init` 会读取既有 `AGENTS.md` 并整合**：Codex 起点项目的收编方向与官方行为
  一致。
- **`CLAUDE.md` 是上下文不是强制**：官方将其定位为 context；硬约束需走 hooks。
  这与"hook 与常驻指令同为提示词注入、差别在投递确定性与事件邻近性"的分层判断
  一致。
- **Claude hooks 面**（2026-07-08）：文档化事件 29 个，处理器类型 5 种
  （`command`、`http`、`mcp_tool`、`prompt`、`agent`）；`timeout` 单位为秒；
  settings 中的 hooks 配置改动由文件监视器捕获，无需重启会话。未知事件名应按
  "晚于采集日期的新增"处理，不视为非法。

## Codex 端对照（与标记成本直接相关）

Codex 侧机制细节见 [codex-capability-surface.md](codex-capability-surface.md)
（2026-07-07），此处只记影响本文档结论的差异：

- **Codex 不剥离 HTML 注释**：`AGENTS.md` 按原始字节拼进 prompt，受管标记进入
  模型上下文并占用项目指令预算——Claude 侧标记零运行时成本，Codex 侧标记应
  保持精简。
- **`AGENTS.md` 不解析 frontmatter / `paths` 作用域**：path-scoped 分片仍以
  显式适用性前言投射。

## 对设计的影响

- `AGENTS.md` 不被 Claude 读取，因此可以安全地作为面向 Codex 的投射面，承载规则
  分片的结构降级注入，不会造成 Claude 侧内容重复。
- 替代方案"`AGENTS.md` 作共享入口、`CLAUDE.md` 写 `@AGENTS.md` 垫片"不采用：
  在"规则分片必须注入 `AGENTS.md`"的前提下，它会让 Claude 经 import 与
  `.claude/rules/` 原生发现重复读取分片内容。

## 实现前需要复核

- Claude Code 是否新增了 `AGENTS.md` 原生支持（issue #34235 状态）。
- 块级 HTML 注释剥离行为是否仍然成立（标记成本判断依赖它）。
- rules frontmatter `bridge` 键的实测结论是否已按
  [knowledge/entry-and-rules.md](../../knowledge/entry-and-rules.md) 记录、
  当前生效的意图记录形态（frontmatter 还是注释回退）是否与仓库实际一致。
- Claude hooks 事件清单是否继续增长（29 个为 2026-07-08 快照）。
- `claudeMdExcludes` 的覆盖范围是否变化——本仓库的夹具围栏依赖它。
- Codex 侧机制按 [codex-capability-surface.md](codex-capability-surface.md) 的
  复核清单跟进；此外指令链的重建时机仍待观察（该文档只记链按环境 cwd 构建，
  未覆盖重建时机）。
