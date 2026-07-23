# 路线图

## 当前状态

实现阶段已经完成 M1（源树声明与只读哨兵）和 M2（技能投射与采纳）。下一里程碑
是 M3（入口与规则投射），尚未实施。当前交付的是开发态 skill、versioned specs、
covenant templates 与隔离夹具；产品产物继续按
[分发模型](../implementation/distribution-model.md)声明的目录落地。CLI、npm
package、插件清单、插件制品和 CI 门禁仍按里程碑门控，当前均未引入。

M2 在本工作单元落地了四组边界明确的交付物：

- [`bridge-sentinel`](../../skills/bridge-sentinel/SKILL.md) 保持严格只读，并把
  carrier contract 升级为
  [`source-tree/v3`](../../skills/bridge-sentinel/references/source-tree-spec.md)
  与 [`report/v3`](../../skills/bridge-sentinel/references/report-spec.md)；
- [`bridge-sync`](../../skills/bridge-sync/SKILL.md) 作为独立写侧入口，实现
  [`reconciliation/v1`](../../skills/bridge-sync/references/reconciliation-spec.md)
  的 Git baseline 仲裁，以及
  [`sync-plan/v1`](../../skills/bridge-sync/references/sync-plan-spec.md) 的完整计划、
  确认、落盘与写后验证；
- [`covenant/v1`](../../templates/covenant/README.md) 用 tracked、immutable 的
  source half 与 `AGENTS.md` managed block 建立 versioned onboarding anchor；
- [`fixtures/m2-sync/`](../../fixtures/m2-sync/README.md) 提供 13 个隔离场景与
  22 项轻量 safeguards，覆盖正常投射、反向采纳、冲突、未知占用、路径与 mode
  护栏、DAG 歧义、失败边界和 covenant 生命周期。

13 个场景是 `baseline-dag-ambiguous`、`behavior-degraded`、
`conflict-zero-write`、`covenant-bootstrap`、`covenant-partial-blocked`、
`create-rerun`、`manual-copy-decision`、`multi-unit-batch`、
`occupied-and-links`、`projection-adopt`、`source-reproject`、
`untracked-ignore` 与 `write-verify-failure`。

### M2 检查命令与证据边界

仓库内稳定、可复现的机械检查不依赖构建或打包工具：

```text
python -B skills/bridge-sentinel/scripts/sentinel_mechanics.py self-test
python -B fixtures/m2-sync/fixture_harness.py self-test
git diff --check
```

第一条验证 Sentinel 的 normalization、diff shape、tree / mode inspection 与
expectation comparison。第二条验证全部 13 个 `bridge-sync-scenario/v1` 定义、
expected plans、post-state trees 和 22 项 safeguards；它是 fixture contract
self-test，不冒充 Bridge workflow 的执行结果。

本工作单元还对其中 12 个 agent-replayable 场景执行了真实 `bridge-sync` workflow
回放：transition 组 6/6 场景通过，7/7 次 plan + post-tree comparison 通过；
guard 组 7/7 branches 通过；`baseline-dag-ambiguous` 另行回放通过。
`write-verify-failure` 是唯一 declarative-only 场景，因为它要求在写入与验证之间
注入故障；其 plan、失败 post-state、fault checkpoint 和 fail-reviewably 约束由
fixture self-test 与 safeguards 验证，不能表述成已执行的 fault-injection smoke。

完整检查清单还包括：

- 两个 formal skill 均通过当前 Codex bundled validator，且
  `agents/openai.yaml` 满足界面字段约束；
- 仓库 JSON 可解析、markdown 相对链接可达、docs inventory 与目录一致；
- `CLAUDE.md` / `AGENTS.md` 保持镜像，covenant source / render bytes 与版本 tuple
  一致；
- 没有残留临时 `bridge-sync-*` worktree、nested `.git`、`__pycache__` 或越过
  milestone 的生成物。

这些证据验证的是仓库载体和 agent workflow。尚未执行 Claude Code / Codex live
host discovery 或 activation smoke；repo bytes 不能证明当前 host session 已加载
技能。

进入 M5 / M6 后，这份清单固化为发布前验证命令与 CI 门禁。

路线图按风险递增推进：先定稿源树声明、行为约定和保真度分类，做只读的哨兵与同步
计划；再从技能这种原生等价配置面开始落盘；随后处理规则与钩子投射，最后打包
分发。

## M1：源树声明与只读哨兵（已完成）

M1 是只读阶段。目标是确定源树形状、行为约定文本和报告口径，让后续落盘建立在
清楚的输入和分类规则上。

已交付：

- 定稿源树布局与条目约定（markdown + frontmatter 加目录约定，含意图记录）。
- 起草注入两个 host 的行为约定文本：两侧同构，常驻指令加 hook 提醒。
- 起草哨兵检查流程与同步计划报告格式（含保真档位）。
- 起草工具映射知识的初始结构（带采集日期）。

完成标准（已满足）：

- 能扫描一个示例项目，报告源树与各投射面的一致性状态。
- 报告状态集封闭，与 [report-spec](../../skills/bridge-sentinel/references/report-spec.md)
  的口径一一对应，夹具比对按该口径逐一验收。
- 没有落盘能力；所有结果只停留在报告与同步计划。

## M2：技能投射与采纳（原生等价档，已完成）

技能是第一块落盘配置面。目录结构清楚，Claude Code 和 Codex 都消费 `SKILL.md`，
适合验证快路径、文件集所有权和哨兵比对。

已交付：

- 技能母本到 Codex 项目级技能目录（`.agents/skills/`）的 complete-tree 投射。
- 快路径在技能面落地：编辑母本后，同一 confirmed work unit 内更新副本并做
  mechanical compare 与 scoped Git checks。
- 写侧仲裁从 `HEAD` 可达 Git DAG 逐 unit 重建 provable baseline；无歧义时采纳或
  重投射，两侧自同一 baseline 携带不同新意图时报告 conflict 并保持该 closure
  零写。
- 未知占用、无 baseline 副本、delete / rename、untracked / ignored、mode 与 path
  safety、部分批次、写后失败和 rollback 边界均进入完整计划与显式确认。

完成标准（已满足）：

- 用户只维护 `.claude/skills/` canonical tree；Bridge 生成 byte / mode
  可保真的 `.agents/skills/` carrier。是否已被 live host 发现仍需 fresh session
  或 restart 后另行验证。
- 看似人工维护的既有副本不被覆盖，Sync 停下来问 `annex` 还是 `keep`；`keep`
  不伪装成同步成功。
- 副本与母本自同一 proven baseline 同时携带不同新意图时报告 `conflict`，该 unit
  与依赖 closure 零写。
- source-only projection、proven projection-only adoption、no-baseline duplicate、
  delete / rename、untracked / ignored、path / mode safety、unrelated dirty
  preservation 与 failure reviewability 都有代表性 fixture contract；除明确标注的
  fault-injection 场景外，均有 agent replay 证据。

## M3：入口与规则投射（结构 / 语义降级档，尚未实施）

规则在技能之后处理，因为它开始涉及降级投射与 LLM 语义映射。

要完成：

- `CLAUDE.md` 共享内容与 `.claude/rules/` 分片投射进 `AGENTS.md` 受管区块。
- 受管区块直接改动的反向采纳。
- path-scoped 分片的适用性前言渲染。
- host 自指内容的投射改写约定；Claude-only 段落的注释标记。
- 三种起点的引导流程，重点是 Codex 起点：既有 `AGENTS.md` 收编为源树。

投射与反向采纳的机制细节见[同步模型](../implementation/sync-model.md)。

完成标准：

- 共享规则只维护一份，两个工具都生效；作用域语义在 Codex 以适用性前言保留。
- 手改 `AGENTS.md` 受管区块的内容能正确回到对应源分片，两侧重新一致。
- `AGENTS.md` 受管区块外的人工区逐字节保留。
- Codex 起点项目可经逐段确认完成收编，无静默覆盖。

## M4：钩子意图与双侧投射

钩子放在更后面，因为风险主要来自执行语义：触发时机、环境变量、权限和失败处理
在两个工具中都可能不同。

要完成：

- 定稿钩子意图文档模型，见[同步模型](../implementation/sync-model.md)钩子一节。
- Claude 侧投射到 `settings.json` 声明键；Codex 侧投射到 `.codex/hooks.json`
  声明键，超出目标侧 hooks 能力面的意图降级为 `AGENTS.md` 常驻指令。
- 实测项目级 `.codex/hooks.json` 的信任加载与逐 hook 重新信任流程，把实测
  确认的执行约束写入映射知识（逐项复核清单见
  [Codex 能力面核验](../research/codex-capability-surface.md)）。
- 在映射知识里写清每类钩子意图在两侧的保真档位。

完成标准：

- 高副作用钩子默认要求显式启用。
- 声明不同步以独立状态呈现。
- 同步计划能解释每个钩子在两个工具上的档位与理由。

## M5：插件打包（skill 加薄包装）

等同步模型稳定后，再做插件产物。这样可以先验证入口、目录和写入策略，再固定发布
形态。

要完成：

- 把 skill、工具映射知识和薄包装脚本组装成 Claude / Codex 插件。
- 两侧技能入口与入库的 `plugin/` 边界目录产物，机制按
  [分发模型](../implementation/distribution-model.md)落地。

完成标准：

- 用户安装插件后获得配套 skill 与工具映射知识。
- 产物由允许清单生成，并经过密钥扫描。
- `plugin/` 入库但明确声明生成物属性：由上游组装，不手工编辑。

## M6：稳定化

最后阶段处理跨平台、可靠性和发布。这里维持既定范围，重点是把已经支持的配置面
做稳。

要完成：

- 补齐跨平台路径、换行；确保 git 操作在不同环境下行为稳定。
- 强化 `conflict` / 仲裁的 skill 行为与示例。
- 建立发布前验证命令和 CI 门禁（以文本 / 链接校验和版本一致性为主）。

完成标准：

- 示例项目覆盖技能 / 规则 / 钩子三类 MVP 配置面。
- 快路径、哨兵与仲裁的 skill 行为稳定，落盘前确认与收尾自检可靠。
- 发布流程能复现生成产物。
