# 分发模型

## 仓库角色

本仓库采用单仓库模式：上游开发态内容（skill 源、工具映射知识、薄包装脚本源、文档、
测试）和可安装插件产物位于同一个仓库。分发形态由未来的内部 `plugin/` 子目录承载。

Bridge 的主要产物是 skill 和知识库，代码只承担入口和辅助检查职责。仓库内部按角色分层：

- `skills/`：skill 源，面向目标工具中智能体的 skill 内容，markdown 为主；可含
  必要的 host metadata、reference specs 和过窄门的机械辅助脚本，入库。M3 继续
  保持严格只读的 `bridge-sentinel` 与独立写侧 `bridge-sync`；后者在技能树之外
  承担 entry / rule managed-block reconciliation，两种权限不能重新合并。
- `templates/`：面向目标项目安装的约定模板等写入素材，与只读 skill 指令分离，
  入库；只有路线图开放相应写路径后才会安装。
- `knowledge/`：工具映射知识，自然语言知识库，带采集日期，入库。
- `fixtures/`：验证用夹具项目，携带已知状态与期望报告，供哨兵等 skill 对照
  校验，入库。
- `src/`：薄包装脚本源（若包装脚本使用 TypeScript），入库。
- `dist/`：包装脚本的构建中间产物，不入库（写进 `.gitignore`）。
- `plugin/`：可安装插件产物，作为**入库的边界产物**提交，供市场按“仓库 + 子目录路径”
  安装；skill 与知识从上游拷入，薄包装脚本从 `dist/` 拷入。

`plugin/` 虽然入库，但仍按生成物管理。要改变行为，应修改上游 skill、知识或包装脚本后
重新组装，不直接手工编辑产物目录。

## 形态：skill 为主，包装为辅

分发主体是 skill 和工具映射知识。它们本身是文本，不需要编译成可执行文件。只有当目标工具
入口需要稳定调用点时，才提供薄包装脚本。用户机前置依赖与环境预检规则见
[tech-stack.md 依赖边界](../architecture/tech-stack.md)。

发布产物不携带上游开发记录：`bridge-intent.yaml` 是用户项目为自己的受管技能维护的
机制，本仓库的技能源在开发期不维护这份文件，发布产物中也不出现；技能出处由发布
版本号加本仓库的 git 历史承担，用户收编技能后从自己的第一条意图记录开始。

用户安装插件后将获得 read-only Sentinel 与 plan-confirm-write Sync；具体流程由
目标工具中的智能体执行，Git 提供 per-unit baseline 与 ownership evidence。Sync
把全部选中的 root `AGENTS.md` block 变化合成为一个完整 desired image；替换现有
文件时按 capability profile 选择已证明的 strict replace，或明确非 CAS 的
`guarded-patch/v1` 单次 exact-region replacement；新建、删除、rename 与
compensation 仍要求对应 strict primitive。缺少合格协议就阻断，不用无标识的
“先检查、再普通写入”替代，也不扩张为跨文件事务保证。Claude Code 插件与 Codex
插件分别适配各自入口。

截至 M3 的开发态仍不引入 plugin manifest、package files、CLI、bundled
JavaScript 或 distribution payload。仓库根 `CLAUDE.md` / `AGENTS.md` 只提供
checked-in skill development entrypoint；到 M5 才生成 host-native plugin
entrypoint。

## Claude Code 入口

官方插件参考确认（核对日期 2026-06-17）：`${CLAUDE_PLUGIN_ROOT}` 在**加载技能内容时
就地替换**为插件安装目录的绝对路径，Bash 子进程中没有同名环境变量，技能正文因此可以
直接写依赖它的命令或文件引用：

```text
node "${CLAUDE_PLUGIN_ROOT}/scripts/bridge.mjs" status
```

这里的 `bridge.mjs` 是未来薄包装脚本，投射 / 仲裁判断仍由 skill 正文、versioned
spec 与工具映射知识完成。
另一锚点 `${CLAUDE_SKILL_DIR}` 指技能自身子目录（官方推荐用于“随技能打包”的文件，
例如工具映射知识片段）。

持久状态使用 `${CLAUDE_PLUGIN_DATA}`（`~/.claude/plugins/data/{id}/`，跨更新保留）。
实现时应避免依赖某次安装的绝对路径；插件更新后路径会变，旧路径会沿用到
`/reload-plugins`。

## Codex 入口

Codex 已为插件 hook 进程注入插件根目录环境变量，hook 命令可直接依赖（见
[codex-capability-surface.md](../research/codex-capability-surface.md)）；但技能正文
没有文档化的插件根目录就地替换机制，Codex 技能入口因此以技能本地包装脚本为默认
设计。包装脚本放在技能自己的 `scripts/` 目录里：

- 插件清单指向 `skills` 目录。
- Codex 技能自带轻量包装脚本。
- 包装脚本从自身位置回溯到插件产物里的薄包装脚本与工具映射知识。
- 技能文档只要求目标工具中的智能体调用这个技能本地包装脚本。

这个设计只依赖稳定文件布局。若 Codex 未来为技能正文提供等价机制，可以把包装脚本
继续收薄，同时保持面向目标工具中智能体的工作流不变。

## 插件产物

未来产物至少需要包含：

- 目标工具清单：Claude Code 与 Codex 各自需要的插件元数据。
- 技能：权限分离的 `bridge-sentinel` 与 `bridge-sync`。
- covenant templates：M3 当前 tuple 的 exact source / managed block，以及只作
  显式 migration evidence 的旧版 exact bytes；M4 hook-intent asset 保持不可由
  M3 安装。
- 工具映射知识：Claude Code / Codex 语义差异的自然语言知识，带采集日期。
- 薄包装脚本：交付 skill、定位自带文件、执行 doctor 的可选 `bridge.mjs`；doctor
  应可离线运行。
- README / 智能体指引：说明前置要求（git，必要时 Node）、安装方式、doctor、安全边界，
  以及 `plugin/` 产物目录的生成物属性。

产物生成应该使用允许清单。发布物只包含经过审计的文件，避免把本地环境变量、密钥、调试
输出和其他开发期内容带入插件。`bridge-sync` 默认排除 ignored files，并阻断疑似
secret / generated payload；打包 allowlist 与项目 write-side scope 是两道独立边界。

## 版本策略

发布时需要让这些版本一致：

- 包版本 / 源码版本。
- 薄包装脚本 `--version`（若提供）。
- 插件清单版本。
- 市场条目版本。
- 生成产物 README 中展示的版本。

版本一致性应该成为发布前门禁。早期机制可以由发布脚本完成：版本不一致时直接失败，避免
发布后再人工排查。

## 市场发布

市场集成放在插件产物可安装、doctor 可用、版本策略稳定之后，届时再决定是否更新类似
`sesamehut/plugins-marketplace` 的市场条目；在此之前仓库保持开发状态。
