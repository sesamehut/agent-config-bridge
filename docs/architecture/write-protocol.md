# ADR：写入协议

状态：已接受。M3 建立 strict / guarded 双通道；M4 在同一通道下增补 JSON 受管键
的 postimage 求法 `json-owned-span/v1`，协议 token 本身不变。

决策日期：2026-07-24。增补日期：2026-09-07。

## 背景

`reconciliation/v2` 已经把 ownership、Git baseline、closure authorization 与完整
pre/post image 纳入写侧契约，但此前假定宿主能提供三项严格条件原语：

- expected-bytes replace；
- create-if-absent；
- delete-if-exact。

[宿主条件写原语核验](../research/write-primitives.md)表明，当前 Claude Code 与
Codex 内建文件工具不能共同证明这组三原语。继续坚持 strict-only 会让 M3 已有文件
替换路径事实上全部不可执行；把 preflight、普通写入或 atomic rename 改称 CAS，
则会制造错误安全承诺。

本 ADR 的目标是在不虚构 CAS 的前提下开放 M3 的非破坏性核心替换能力，同时让
create、delete、rename、补偿和未来更强 adapter 保持清晰边界。

## 决策

Bridge 采用两个互不冒充的执行通道：

1. **strict 通道**：只有 capability adapter 明确证明原语时才使用
   `strict-replace/v1`、`strict-create/v1` 或 `strict-delete/v1`；
2. **guarded 通道**：对满足资格的现有安全文本文件，允许版本化
   `guarded-patch/v1`，并强制 exact-region、完整 preflight、完整 postverify、
   residual-race warning 与显式确认。

capability adapter 默认拒绝。guarded 通道不是 strict 通道的静默 fallback：
计划必须逐 path 序列化实际协议，用户看到并确认 `guarded-patch-non-cas` 后才可
执行。`applied` 只表示最终验证时观察到完整 planned postimage，不表示调用期间
没有并发写或没有 lost update。

## 协议 token

| Token | 允许的操作 | 承诺 |
|---|---|---|
| `strict-replace/v1` | 替换现有 regular file | mutation 与完整 expected preimage 由同一已证明原语绑定 |
| `strict-create/v1` | 创建缺失路径 | 最终路径已存在时不覆盖，即 create-if-absent |
| `strict-delete/v1` | 删除现有 regular file | mutation 与完整 expected preimage 由同一已证明原语绑定 |
| `guarded-patch/v1` | 替换现有 eligible text file | 完整 preflight、一次唯一 exact-region replacement、完整 postverify；明确保留竞态 |
| `unavailable` | 无 | 当前 binding 没有可用协议，相关 closure 阻断 |

这些 token 正交于 `covenant/v3` 等内容契约版本。协议语义发生不兼容变化时增加新的
protocol version，不把旧 token 的保证悄悄改强或改弱。同理，postimage 怎么求得
不是 capability 声明：`json-owned-span/v1` 是一条具名派生规则，不进入本表。

## capability adapter

逻辑接口是 `capability-profile/v1`。它至少绑定：

```text
host + host version + tool surface + platform + filesystem assumptions
```

输出分别列出 replace、create、delete 支持的 protocol token 与证据来源。任何
binding 分量无法解析、版本不在已核验范围、路径跨越未证明 filesystem，或工具只有
“读取后覆盖”行为时，该项都是 `unavailable`。工具名称、成功消息、用户确认与
advisory lock 都不能自行提升 capability。

适配结果不豁免既有路径门禁。symlink、reparse point、special file、path escape、
case collision、mode 或敏感内容异常仍按原 registry 阻断。

当前基线是：

- Claude Code `Edit` 可作为经版本绑定的 `guarded-patch/v1` 候选；
- Claude Code `Write` 与 Codex `apply_patch` 不证明 strict protocol；
- Codex `apply_patch` 也不满足 exact-literal guarded contract，默认拒绝；
- `strict-create/v1` 只有真实 exclusive create 实现及完整路径安全证明同时存在时
  才可用；
- strict replace/delete 与 strict compensation 默认 unavailable。

fixture-only retained-root-child fault adapter 还有独立的平台边界。POSIX retained
leaf handle 只能证明该 handle 的对象身份；同目录 rename 后再在原名创建新文件时，
它不能仅凭 leaf identity / link count 证明当前 root-child 名称仍指向该 leaf。
因此在缺少独立、同一 mutation 绑定的 current name-to-leaf 证明时，POSIX fault
mutation 只能保留为 declarative-only contract，`apply-fault` 必须在目标 mutation
前 fail closed，不得把“写入 retained handle”表述成 swapped-path 防护。该限制不
外推到 Windows：Windows adapter 继续按自己的 handle、name、reparse 与 filesystem
attestation 独立解析 capability，不能因 POSIX 限制被静默降级或升级。

## `guarded-patch/v1`

### 资格与 exact region

每个 path 必须同时满足：

1. 目标是已存在、路径安全、可完整读取和 byte-round-trip 的 regular UTF-8 text
   file；create、delete、rename、mode-only change 与空 preimage 不合格；
2. 计划已持有完整 `preimage` 与完整 `postimage`，且两者不同；
3. 从首个 changed byte 到最后一个 changed byte 形成一个 contiguous region，并
   向两侧扩展稳定不变的上下文，直到 `old-region` 非空、落在字符边界且在完整
   `preimage` 中恰好出现一次；
4. `postimage` 必须严格等于
   `prefix + new-region + suffix`；region 外 bytes 不变；
5. adapter 能做一次 exact-literal、unique-match、非 regex、非 fuzzy、
   非 `replace_all` 的 replacement。

计划和 operation-local journal 记录 path、完整 pre/post image、region byte
offset、exact old/new region、protocol token 与 adapter binding。若不能形成唯一
region，必须用 `guarded-patch-unavailable` 阻断；不得缩短上下文去“尽量匹配”。

同一文件的多个 selected block change 先合成为完整 postimage，再求一个 contiguous
region。region 可以跨过 manual/unselected span，但这些 bytes 在 old/new region
中必须完全相同。这样一次 path 只发出一个 mutation call，不声称跨 path transaction。

### 执行

每个 guarded path 严格按以下顺序：

1. **final preflight**：在精确计划已确认后、紧邻 host call 前重读完整文件；
   type、mode/representability 或任一 byte 不等于
   planned preimage，立即拒绝该 stale plan；
2. **single patch**：对记录的唯一 `old-region` 发出一次 exact-literal replacement；
3. **postverify**：无论工具返回成功还是错误，都立即重读完整文件；
4. **closure verify**：所有 step 完成后，再验证所有受影响路径的完整 postimage、
   manifest、render relation 与 protected spans。

确定性的 preflight-mismatch 夹具只能把外部变化绑定在“精确计划确认之后、
final preflight 之前”。final preflight 观察到变化后，受影响 closure 精确记为
`failed`，并以完整 pre/post tree 证明 Bridge 零写；不能把同一变化宣称发生在
final preflight 之后。后一个窗口属于另一个 host-call precondition / postverify
场景。

preflight 不是 mutation precondition；postverify 也只是事后观察。并发写可能在
preflight 后、工具匹配前、工具匹配与写入之间或 postverify 后发生。工具可能拒绝
已经改变的 region，也可能覆盖刚进入同一 region 的并发 bytes；region 外变化通常会
在完整 postverify 中暴露，但不能保证防止 lost update。

### 状态机

| 观察 | 无先前本轮 mutation | 已有先前本轮 mutation |
|---|---|---|
| capability/path gate 在 mutation 前失败 | `blocked` | 不适用 |
| preflight 不等于完整 preimage | `failed` | `partial` |
| call 后完整文件等于 planned postimage | step verified，继续 | step verified，继续 |
| call 后完整文件仍等于 planned preimage | `failed` | `partial` |
| call 后为任何第三种值、不可读或类型改变 | `partial` | `partial` |
| 所有 step 与 closure final verify 通过 | `applied` | `applied` |

一旦出现 `partial`，停止该 closure 及后续/dependent closure，并保留当前 bytes 与
journal evidence。不得为了制造整洁结果而覆盖第三种值。

## JSON 受管键写入（json-owned-span/v1）

M4 的两个 hooks carrier（`.claude/settings.json` 与 `.codex/hooks.json`）是 JSON，
但它们对写入协议没有提出新要求：对已存在文件仍是一次 exact-literal、唯一匹配、
非 regex 的替换，正好是 `guarded-patch/v1` 的承诺；缺失文件仍只接受
`strict-create/v1`。因此不新增 protocol token，只给 postimage 的求法一个名字
`json-owned-span/v1`。它是派生规则，不是能力声明，也不进 Write capabilities 表。

### 资格

carrier 必须是已存在、路径安全、可完整读取并 byte-round-trip 的 regular UTF-8
text file，能被严格解析器解析成 JSON 对象，且**任何层级都没有重复对象键**，
所有节点都落在封闭的 hooks 形状内。重复键或形状之外的节点用
`hooks-carrier-unusable` 阻断对应 closure。这里必须 fail closed：重复键让 span
与取值的对应不唯一，猜错一个就会静默丢掉用户的 hook。

### owned span 派生

ownership 只来自意图文档：对 host `h`，owned 组恰好是 `targets.<h>.surface` 为该
host JSON carrier 的合法条目的 `(event, effective-matcher(h))` 对。机械层在精确
preimage 上做 span-preserving 扫描，给出 `hooks`、每个 `hooks.<Event>` 数组、每个
组元素、每个 handler 对象与每个 key/value 成员的 byte range，以及元素之间的精确
分隔符字节；它从不重新序列化，也不判断归属。不存在的组是一个零宽插入点，带自己
的精确前后缀字节，插入层级只有 group、event、hooks 三种。

postimage 就是 preimage 加上「只编辑 owned span、只填插入点」：

- **已存在的成员**做最小成员 span 编辑。改标量只替换该值的 token span；加键插在
  该对象最后一个成员之后，沿用该对象自己的分隔符与缩进；删键删掉该成员 span 加
  恰好一个分隔符。组内键顺序与未变化的 `matcher` 成员绝不重写。
- **新建的组或 handler**才用规范化 render，缩进与 handler 单行/多行形态从所在
  文件推断，键顺序固定。
- 其余每个字节逐字节复制：兄弟 event、同 event 的其他组、无关顶层键、Codex 顶层
  `description`、键顺序、缩进与文件末尾换行都不动。

得到 `(preimage, postimage)` 之后，交给上面**未修改**的 guarded region 规则求唯一
contiguous region。hooks JSON 高度重复，region 可能合法地吞入相邻的未受管字节
（允许，因为它们新旧值相同），也可能始终无法唯一；后者用
`guarded-patch-unavailable` 阻断，上下文一律不得为了凑匹配而缩短。

### 幂等律

**当每个 owned 组解析后都已等于其期望模型时，`compose(preimage, desired)` 必须
恒等于 `preimage`，与格式无关。** 状态由语义 handler 相等决定，字节相等只决定
是否存在一行 Write capabilities：语义相等且没有额外键的组序列化成
`unchanged` / `unchanged`、不产生写入行，字节不同时只发信息性
`hook-format-preserved`。这条律不是风格偏好，而是可比性的前提：夹具按原始字节
比较整棵树，非幂等的 renderer 会让每次运行都在未受管字节上报出假漂移。

合成器自检前后缀相等，拒绝任何在已定位 span 之外发生差异的 postimage；计划验证
器另有封闭失败 id `hooks-carrier-composition`，它重算「preimage 只改 owned span」
的结果并要求与 render 操作的 post 值逐字节相等。整文件反序列化再序列化因此被显式
禁止。

### 数组只追加

新组追加在 `hooks.<Event>` 数组的收尾括号处，回退过尾部空白后写「`,` + 换行 +
缩进 + 渲染结果」。Bridge 永不移动、排序或重排既有元素，无论受管与否。删除移除
元素 span 加恰好一个相邻分隔符（非首元素取前一个，否则取后一个）连同该侧空白；
被清空的 event 成员整体删除，被清空的 `hooks` 对象保留为 `"hooks": {}`。

这是安全决定而不是风格决定：Codex 的逐 hook 信任与用户在 `/hooks` 里的禁用选择
都存在按 `group_index`、`handler_index` 编址的 key 之下，按 id 排序会把无关 hook
的信任指到别处，甚至静默重新启用用户刻意禁用的 hook。任何使后续下标位移的删除
都必须发需确认的 `codex-trust-reindex`。

### 为什么不整文件重写

整文件重新序列化会重排未受管组、抹掉用户的手工格式，并因此触发上一条的信任位移；
它还会改写 Codex 顶层 `description` 这个用户唯一的元数据槽（Bridge 从不写它、
从不创建它、也从不修复它的缺失）。本仓库自己那份手写 `.claude/settings.json`
就是反例：混合的行内与多行数组、成规模的 map，一次重排就是一次不可评审的 diff。

### 与其他 token 的关系与后果

- `json-owned-span/v1` 只描述怎样得到 postimage；实际 mutation 仍由
  `guarded-patch/v1` 执行，并照常发出 `guarded-patch-non-cas`。
- carrier 缺失时动作仍是 `create`，协议解析为 `unavailable` 并阻断，计划在
  Evidence 里给出需要用户自己创建的精确 bytes；Bridge 不用无条件写入伪造
  create-if-absent。
- 逆操作与补偿的规则不变：没有 strict inverse 就不做乐观回退，按观察结果报
  `partial`。
- 向 Claude carrier 写 hook 还要求一条需确认的 `claude-hooks-shared-execution`：
  提交进仓库的 hook 会在每个 clone 上运行，Bridge 的分类是评审元数据而不是沙箱。
  写入协议本身不提供任何执行边界。

## create、delete、rename 与 compensation

- **create**：只接受 `strict-create/v1`。普通 `Write`、patch add 或
  “检查不存在后创建”不合格。
- **delete**：只接受 `strict-delete/v1`。先读后 remove 不合格。
- **rename**：拆成计划内的 destination/source path operations；每一步都必须有
  strict protocol，缺一项就整体阻断。guarded patch 不参与 rename。
- **same-operation compensation**：只有每个逆操作在首写前都已解析为相应 strict
  protocol 时才能进入 `compensating`。guarded patch 永不用于补偿。

strict compensation 默认 unavailable，因此 Bridge 默认阻断补偿尝试，而不是用
第二次 optimistic patch 冒充恢复。forward guarded plan 可以在用户确认
`strict-compensation-unavailable` 后执行；发生不能直接证明为完整 preimage 或
postimage 的失败时报告 `partial`。这是一条显式损失边界，不是 rollback 保证。

`applied` 后 journal 关闭。之后的 rollback 仍需用 current bytes 与 reachable Git
形成新计划；它不能复用旧 journal，也不能绕过当时可用的 protocol gate。

## manual zone

`AGENTS.md` 的所有 manual、unselected 与 conflict spans 继续进入完整 planned
pre/post image：

- 使用 `strict-replace/v1` 时可发出 `manual-zone-preserved`；
- 使用 `guarded-patch/v1` 时只能发出 `manual-zone-guarded`，并同时发出
  `guarded-patch-non-cas`；
- 两种 token 都不授予 block ownership，marker map 异常仍阻断。

guarded 模式证明 planned postimage 在验证时保留了这些 spans，但不证明调用窗口中
某个并发 manual-zone edit 没有被覆盖。M3 成功标准据此改为“精确保留计划内
manual bytes，并明确披露 residual race”，不再声称所有计划外并发变化必然令
full-file precondition 拒绝。

## 计划接口与确认

`sync-plan/v3` 使用 closed `Capability profiles` binding 表：

```markdown
| binding | profile | host | host version | tool surface | platform | filesystem assumptions |
|---|---|---|---|---|---|---|
```

每行 `profile` 固定为 `capability-profile/v1`；binding 由 path operation 引用。host
与 platform 使用 closed token，version/tool 是 exact observed ASCII identifier，
filesystem assumptions 是排序后的 versioned token 集。未引用 profile row 不合法。

随后按实际执行顺序排列 `Write capabilities`：

```markdown
| step | closure | path | operation | protocol | binding | inverse protocol | inverse binding |
|---|---|---|---|---|---|---|---|
```

`operation` 是 `replace`、`create` 或 `delete`。`protocol` 使用本 ADR 的 token；
strict/guarded protocol 必须引用 profile binding，`unavailable` 的 binding 为 `-`；
`inverse protocol` 使用对应 strict token 或 `unavailable`。Evidence and notes 必须
记录 guarded region offset 与 exact-value 摘要；exact bytes 留在 live journal，
不泄漏 ignored/sensitive/out-of-scope 内容。

以下 warning 需要显式 acknowledgement：

- `guarded-patch-non-cas`；
- `manual-zone-guarded`；
- `strict-compensation-unavailable`；
- 既有 `agents-md-near-budget` 与 strict 路径的 `manual-zone-preserved`。

缺少 strict-required protocol 用 `conditional-write-unavailable` 阻断；本可做
existing-file replacement、但没有合格 guarded adapter/region 时用
`guarded-patch-unavailable` 阻断。确认不能把任一 `unavailable` 改写成 available。

## 被否决的方案

### strict-only 立即作为 M3 完成条件

安全语义清楚，但当前宿主能力矩阵会让已有文件替换全面阻断，把 entry/rule 核心
能力实质推迟到后续包装/helper。保留 strict 通道，不把它作为唯一通道。

### 把 preflight + 普通写称为 CAS

读取与 mutation 之间存在竞态，名称会误导用户和后续实现。否决。

### 临时文件 + atomic replace 或 advisory lock

atomic rename 不带 expected destination bytes；advisory lock 不约束非合作写者。
它们可作为未来 adapter 的内部步骤，但不能单独证明 strict protocol。

### guarded 失败后再做 guarded compensation

第二次乐观替换可能覆盖失败后产生的新用户 bytes，扩大损失。否决；没有 strict
inverse protocol 就停止为 `partial`。

## 后果

- M3 可在能力已绑定的宿主上执行现有文本文件的非破坏性替换，不必等待 M5
  packaging；
- bootstrap/create、delete、rename、binary/mode change 与 strict compensation
  仍可能阻断，这是有意的 capability boundary；
- `applied` 的含义保持为“验证通过”，但必须结合 path protocol 与 warning 解读；
- fixture/replay 需要分别覆盖 preflight rejection、unique-region rejection、
  exact postverify、第三值 `partial`、无 strict inverse、以及 strict-only 操作阻断；
- hooks carrier 另需覆盖幂等重跑（重规划后整棵树逐字节不变）、手工格式 carrier 的
  未受管字节保全、无法唯一化的 region、重复键 carrier 与缺失 carrier 的阻断；这些
  是 `json-owned-span/v1` 的回归面，不能靠 `guarded-patch/v1` 既有夹具代证；
- 可执行的 preflight rejection 夹具还必须把精确 confirmed plan、bundle、
  root/leaf identity、preimage/mode 与一次性 `armed -> claim -> injected` evidence
  绑定起来；plan 的 hash、parse 与正式验证必须来自同一次 retained-handle bytes
  捕获。phase receipt 的 probe/read/exclusive create 必须相对同一个 retained
  `.git` parent，receipt 自绑定创建时 file/parent identity、mode、nlink 与
  reparse 状态，后继状态再绑定前序 raw digest 与完整 identity evidence；
  合法 claim 中断只可从精确 preimage 继续注入，或从精确 postimage 补齐
  injected evidence，其余组合 fail closed。`apply-fault` 不接受调用方自报
  phase/target，且需由独立 CLI 进程证明注入持久化与完整树只有声明目标改变；
  POSIX 若不能把当前 root-child 名称与 retained leaf 绑定到同一 mutation，则该
  平台只验证 declarative contract，并在目标 mutation 前 fail closed；Windows
  capability 仍按其独立 attestation 解析；
- 未来 helper 若能证明更强原语，只需新增 adapter evidence 并选择已有 strict
  token，不需要把 `guarded-patch/v1` 偷换成 CAS。
