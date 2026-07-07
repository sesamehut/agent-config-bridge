# Host 上下文加载行为核验

采集日期：2026-07-07。主要来源为 Claude Code 官方文档
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

## 对设计的影响

- `AGENTS.md` 不被 Claude 读取，因此可以安全地作为面向 Codex 的投射面，承载规则
  分片的结构降级注入，不会造成 Claude 侧内容重复。
- 曾评估过的替代方案——`AGENTS.md` 作共享入口、`CLAUDE.md` 写 `@AGENTS.md`
  垫片——在"规则分片必须注入 `AGENTS.md`"的前提下，会让 Claude 经 import 与
  `.claude/rules/` 原生发现重复读取分片内容，被否决。

## 实现前需要复核

- Claude Code 是否新增了 `AGENTS.md` 原生支持（issue #34235 状态）。
- HTML 注释剥离行为是否仍然成立（标记成本判断依赖它）。
- Codex 侧机制（hooks、技能目录、rules、项目级配置面）已由
  [codex-capability-surface.md](codex-capability-surface.md) 单独核验
  （2026-07-07），按该文档的复核清单跟进。
