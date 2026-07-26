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

M3 把 M2 covenant 升级为当前 `covenant/v2`，正式开放 entry / rules 写面；hooks
仍未安装。

## M2–M3 用户契约

技能 canonical unit 仍是 immediate `.claude/skills/<name>/` 完整 regular-file
Git tree，projection 是 `.agents/skills/<name>/` 同名完整 tree。M3 新增两类
canonical unit：

- `entry`：`CLAUDE.md` 或 `.claude/CLAUDE.md` 恰好一个；二者并存直接阻断；
- `rules/<id>`：`.claude/rules/**/*.md` 中除 covenant 与 `hooks.md` 之外的分片。

entry / rules 通过固定 `source-tree/v4` render 投入 root `AGENTS.md` 独立 managed
block。受管区块外与未被本轮选中的所有 bytes 都是 manual zone，进入完整 planned
pre/post image。已有文件优先使用已证明的 strict replace；否则 eligible 文本文件
可用显式非 CAS 的 `guarded-patch/v1` exact-region 流程。新建只接受
`strict-create/v1`。Bridge 不支持自由 semantic managed mode；shared
内容先改成 host-neutral 表述，Claude-only 内容用受控注释减除，Codex-only 内容留在
manual zone。

用户继续得到两项分离能力：

- read-only Sentinel 只报告 current carrier；
- write-side Sync 从 Git 可达历史重建 per-unit provable baseline，给完整计划、取得
  确认后执行。

current carrier diff 不直接决定 `adopt` / `conflict`。无 baseline 不猜方向；未知
occupancy 必须 annex-or-keep。`keep` 仅本轮零写、仍未解决，不创建 ignore manifest。
delete / rename 只有 Git 证明目标曾受管才进入自动计划；rename old/new 是不可拆
closure，但不虚构跨文件原子性。
尤其 copy-only S4 无论 project covenant 是否有效，都先保持
`adoption-candidate` / `annex-or-keep`；只有写侧历史仲裁能把它认定为受管删除。

每个 managed skill 有 `bridge-intent.yaml`：initial onboarding / annex / adopt /
semantic change / rename 追加日期与动机，pure mechanical reproject 不追加。intent
是 evidence，不授予 ownership。entry / rule intent 使用受控
`bridge:intent` HTML comments，禁止依赖宿主未承诺的 unknown YAML key。

Codex 起点不会整文件自动收编：计划把既有 `AGENTS.md` 精确分段，逐段确认进入
`entry`、某个 rule shard、保留为 manual，或显式丢弃。source 写入与同一段替换为
确定性 managed block 属于同一 closure。

## 产品约束

1. **单一 source、对称入口**：projection 不反向拥有 shared truth，但 proven
   projection intent 可以 adopt 回 source。
2. **观察与写入隔离**：Sentinel 严格只读；只有 Sync 可在 confirmed plan 下写。
3. **ownership 需证明**：project covenant 不自动收编同名文件；unit 需要 Git
   transition evidence 或明确 annex。
4. **冲突不自动 merge**：只有同一 baseline 两侧不同新意图才 conflict；用户选择
   source、projection 或 resolved result。
5. **零静默覆盖 / 零静默扩域**：hand-written duplicate、non-empty no-SKILL
   target、path safety 异常与未知 occupancy 全部停问；invalid、no-op、duplicate
   或 brace-expansion 超预算的 `paths` 直接阻断，绝不当作 unscoped rule。
6. **完整写前计划**：tracked / relevant untracked / ignored / dirty scope、baseline、
   action、warning 与 physical dependency closure 全部可见；每个 closure 的稳定 id、
   members、dependency、selected / not-selected 和 authorization 都可序列化并确认。
7. **Git 可追溯但不代替授权**：Bridge 不 stage / commit；same-operation
   compensation 只有全部 inverse protocol 预先证明为 strict 才执行，否则明确
   warning 并在失败时报告 `partial`；`applied` 后 journal 关闭，rollback 必须以
   current bytes + reachable Git 重建新计划并再次确认，无法从 Git 重建旧值就不可
   回滚；用户确认不能替代 ownership、baseline 或 prior bytes。
8. **版本显式**：covenant / source-tree / report / reconciliation / plan 绑定版本；
   当前 tuple 是 `covenant/v2`、`source-tree/v4`、`report/v4`、
   `reconciliation/v2`、`sync-plan/v2`。v1/v3 只作一次性显式 migration evidence，
   不保留双读兼容模式；迁移必须把 reachable-v1 proven units 作为闭集由一个
   reachable transition commit carry / repair / explicit release，不能只换 covenant；
   每个 unit 的全部 ancestry-maximal legacy OID 必须独立列出，ambiguity 不得折叠成
   任意单个 baseline。
9. **可达性先于落盘**：root override、无法证明的 root-marker、会被新建
   `AGENTS.md` 遮蔽的 fallback、budget=0 或 planned bytes 超预算，默认阻断 apply；
   live activation 会检查 exact safe override / fallback（即使 untracked / ignored）
   与 resolved config，unknown 同样阻断；这些 bytes 不授予 ownership。Bridge 不改
   用户 Codex config 来制造“已生效”。
10. **版本化写协议而非伪 CAS**：strict replace/create/delete 只在
    `capability-profile/v1` 证明后使用；现有 eligible 文本文件可用
    `guarded-patch/v1`，但计划必须显示 exact region、完整 preflight/postverify、
    residual race 与缺失 strict compensation。create、delete、rename 和 inverse
    operation 不得 guarded 降级。Bridge 不承诺 lock、跨文件 transaction 或 crash
    durability。

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

M3 完成时：

- shared entry 与 rules 每个只维护一份，Codex managed block 可由固定 render
  重建，path scope 以 versioned preamble 明确标为 semantic tier；
- proven managed block 的直接修改可反向映射到对应 source；受保护 span 或 host
  自指产生歧义时必须展示 source candidate 与 rerender，再显式确认；
- `AGENTS.md` manual zone 在任何 create / update / adopt / delete / migration 中
  都按 planned image 逐字节保留；strict path 拒绝不匹配 precondition，guarded path
  明确披露工具调用内并发修改可能被拒绝、检测或覆盖，不虚报 CAS；
- 空项目、Claude 起点与 Codex 起点都能通过完整计划接入，无整文件隐式 annex；
- Git reachable DAG、失败补偿、rollback 与 M2 使用同一安全底座。

完整 MVP 完成时，hooks 也满足相同的 ownership、plan、confirmation 与 verification
原则；不同 host 的降级档位逐 unit 可解释。
