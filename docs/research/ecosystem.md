# 现有工具调研

采集日期：2026-06-15。

这份调研用于判断：现有项目是否已经覆盖 Agent Config Bridge 需要的产品组合。

## 评估维度

本项目需要同时满足几个条件：

- 项目内技能、钩子、规则主要维护一份规范源。
- Claude Code 与 Codex 都能使用各自的投射结果。
- 用户在目标工具配置文件里的有效修改，可以通过明确采纳流程回到规范源。
- 初始范围覆盖技能、钩子和规则。
- 分发上可以做成插件，必要的包装脚本随插件打包。

只解决技能，或者只做工具配置目录树连续同步的工具，仍然有参考价值，但只能覆盖本项目的一
部分。

## 工具观察

| 工具 | 观察 | 与本项目的距离 |
| --- | --- | --- |
| [ai-config-sync-manager](https://github.com/slash9494/ai-config-sync-manager) | README 定位为 Claude Code 与 Codex 的连续双向同步，覆盖技能、智能体、MCP、钩子、权限，并强调工具语义映射。 | 更接近两个工具配置目录树之间的持续同步。本项目选择规范源 + 投射，以减少双源漂移。 |
| [skillshare](https://github.com/runkids/skillshare) | 面向多种 AI CLI 的技能同步和团队分享，范围主要集中在技能。 | 技能管理思路可参考。本项目还需要覆盖钩子 / 规则语义，以及 Claude / Codex 项目级规则的 Bridge。 |
| [sync-skills](https://github.com/viteinfinite/sync-skills) | 使用 `.sync-skills` 作为规范源，把 `.claude/skills` 和 `.codex/skills` 指向共同技能。 | 很接近技能单项需求。本项目还需要处理规则 / 钩子和工具特化映射。 |
| [ai-rules-sync](https://github.com/lbb00/ai-rules-sync) | 覆盖规则、技能、命令、子智能体和多种智能体工具，强调管理与分享。 | 通用面更广。本项目需要更严格地区分 Claude / Codex 的规则与钩子语义，并围绕插件 + 内置包装脚本分发。 |
| [rulesync](https://github.com/dyoshikawa/rulesync) | 从统一规则生成多种 AI 工具配置，支持规则、命令、MCP、ignore、子智能体、技能等。 | 规则生成方向值得参考，但目标范围更广；没有专门围绕 Claude / Codex 的技能 / 钩子 / 规则单源采纳模型展开。 |

## 结论

目前没有看到一个工具完整覆盖本项目的组合要求。

最接近的方向有两个。`ai-config-sync-manager` 在 Claude / Codex 映射上更接近，但模型
更偏工具配置目录树同步。`sync-skills` 和 `skillshare` 在技能管理上很接近；本项目把规则 /
钩子、采纳和插件分发放在同一个模型里。

因此 Agent Config Bridge 可以吸收这些项目的经验，同时保持自己的产品边界：规范源是
长期维护对象；投射负责生成目标工具配置文件；采纳只处理来自某个工具的人工修改。

## 实现前需要复核

下面这些信息变化较快，进入实现前要重新看官方文档：

- Claude Code 插件、技能、钩子与 `CLAUDE_PLUGIN_ROOT` 的最新行为。
- Codex 插件清单、`skills` 目录、技能本地 `scripts` / `resources` 的最新行为。
- Codex 对规则、项目指令、命令审批或类钩子自动化的当前支持边界。

这份调研的采集日期说明当时的判断依据；实现前仍以官方文档复核为准。
