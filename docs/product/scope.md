# 产品范围

## 要解决的问题

同一项目交替使用 Claude Code 与 Codex 时，project-level skills、rules 与 hooks
容易分裂为两套长期维护树。简单复制可以应急，却无法回答：

- 哪一份是共享意图的 source；
- projection-side 手改应采纳、重投射还是判为 conflict；
- 既有同名内容是否真的归 Bridge 所有；
- 两侧 bytes 相同是否也代表 runtime / behavior 相同。

Agent Config Bridge 的承诺是共享配置只维护一份，同时保留两个工具对称的变更入口。
完整机制见[架构概览](../architecture/overview.md)。

## 立场：工具等权重

source 使用 Claude 形态是 container schema 的工程选择，不代表工具优先级：

- Claude / Codex 会话都可发起配置意图；
- projection-side 的 proven managed change 可经 adoption 回到 source；
- Claude 起点、Codex 起点与空项目都有显式 onboarding 路径；
- host 差异按 compatibility / fidelity 如实报告，不靠静默丢弃营造“一致”。

## 面向用户

- 在一个 Git 仓库中交替使用 Claude Code 与 Codex 的开发者；
- 希望把项目智能体配置当作可审阅、可追溯工程资产的维护者；
- 已有 Claude skills 或 Codex project skills、需要安全收编而非直接覆盖的项目。

## MVP 范围与 milestone

MVP 最终覆盖三类 project-level 配置：

- **skills**：complete skill Git tree；
- **entry / rules**：source shards 到 `AGENTS.md` managed blocks；
- **hooks**：intent document 到双侧 native hooks carrier。

写能力按阶段开放：

- M2：skills projection / adoption / reconciliation，以及 versioned covenant
  bootstrap；
- M3：一般 entry / rules projection 与 managed-block reverse adoption；
- M4：hook intents 与双侧 projection。

M2 covenant 的 source + `AGENTS.md` block 只是 onboarding / ownership
基础设施，不表示 rules surface 已提前开放；M2 不安装 hooks。

## M2 用户契约

M2 的 canonical unit 是 immediate `.claude/skills/<name>/` 完整 regular-file Git
tree，projection 是 `.agents/skills/<name>/` 同名完整 tree。source 明确携带的
`agents/openai.yaml` 原样复制；Bridge 不派生 sidecar、不写 `skills.config`。

用户得到两项分离能力：

- read-only Sentinel 只报告 current carrier；
- write-side Sync 从 Git 可达历史重建 per-unit provable baseline，给完整计划、取得
  确认后执行。

current two-tree diff 不直接决定 `adopt` / `conflict`。无 baseline 不猜方向；未知
occupancy 必须 annex-or-keep。`keep` 仅本轮零写、仍未解决，不创建 ignore manifest。
delete / rename 只有 Git 证明目标曾受管才进入自动计划；rename old/new 原子。
尤其 copy-only S4 无论 project covenant 是否有效，都先保持
`adoption-candidate` / `annex-or-keep`；只有写侧历史仲裁能把它认定为受管删除。

每个 managed skill 有 `bridge-intent.yaml`：initial onboarding / annex / adopt /
semantic change / rename 追加日期与动机，pure mechanical reproject 不追加。intent
是 evidence，不授予 ownership。

## 产品约束

1. **单一 source、对称入口**：projection 不反向拥有 shared truth，但 proven
   projection intent 可以 adopt 回 source。
2. **观察与写入隔离**：Sentinel 严格只读；只有 Sync 可在 confirmed plan 下写。
3. **ownership 需证明**：project covenant 不自动收编同名文件；unit 需要 Git
   transition evidence 或明确 annex。
4. **冲突不自动 merge**：只有同一 baseline 两侧不同新意图才 conflict；用户选择
   source、projection 或 resolved result。
5. **零静默覆盖**：hand-written duplicate、non-empty no-SKILL target、path safety
   异常与未知 occupancy 全部停问。
6. **完整写前计划**：tracked / relevant untracked / ignored / dirty scope、baseline、
   action、warning 与 physical dependency closure 全部可见，每次写都确认。
7. **Git 可追溯但不代替授权**：Bridge 不 stage / commit；确认计划授权同一
   closure 的 journaled CAS 失败补偿，无法安全补偿时报告 `partial`；成功写入后的
   rollback 只限本轮 recorded preconditions，需新计划与再次确认。
8. **版本显式**：covenant / source-tree / report / reconciliation / plan 绑定版本；
   版本变化走 migration，不保留隐式兼容模式。

## compatibility 承诺

“已投射”至少拆为四个正交判断：Agent Skills format、host runtime loadable、release
validator profile、behavior portability。byte-identical skill 的 projection tier 可以
是 `native`，同时因 Claude-only frontmatter、dynamic content 或 `allowed-tools` 标
`behavior-degraded`。

只有 identity、YAML、确定加载失败与 path safety 是 blocker。Codex project skill
carrier 不合成 `awaiting-host-trust`；live activation 无法从 repo bytes 得知，写后
以 fresh session / restart hedge 说明。

## MVP 之外

MCP servers、subagents、global user config、model selection、第三方 IDE rules，
以及 Claude permission rules / Codex approval-sandbox rules 的互投射不在 MVP。
这些 runtime policy 不能用散文伪装成等价安全边界。

## 成功标准

M2 完成时：

- source-only change 在确认后投射为 identical complete Git tree；
- proven projection-only change 可安全 adopt 并补 intent；
- two-sided different intent 报 conflict 且该 unit 零写；
- no-baseline duplicate 不被覆盖，必须 annex / keep；
- delete / rename、untracked / ignored、mode / path safety 与 unrelated dirty
  changes 都有可执行的保守边界；
- 写后 manifest compare 与 scoped Git checks 可证明 path / type / bytes / mode；
  mode-only 差异不会伪装成相等；
- 失败补偿只覆盖本轮精确写入值；成功恢复报 `compensated`，无法证明完整 closure
  报 `partial`，未执行依赖项报 `not-attempted`。

完整 MVP 完成时，entry / rules / hooks 也满足相同的 ownership、plan、confirmation
与 verification 原则；不同 host 的降级档位逐 unit 可解释。
