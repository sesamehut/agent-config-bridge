# 宿主条件写原语核验

采集日期：2026-07-24。

## 核验问题

Bridge 的写侧需要区分四种不同能力，不能把它们统称为“原子写”：

1. 仅当现有文件仍等于完整 expected bytes 时替换；
2. 仅当最终路径不存在时创建；
3. 仅当现有文件仍等于完整 expected bytes 时删除；
4. 对现有文本中的唯一 exact region 做一次 guarded replacement。

前三项是严格条件原语。第四项只能缩小 stale-write 风险；它不等价于文件级
compare-and-swap，也不证明并发写没有被覆盖。核验对象是宿主公开契约与固定版本
实现，不从工具名称、成功消息或“先读后写”的表象推断更强保证。

## 结论矩阵

| 候选 | 严格替换 | 排他创建 | 严格删除 | exact-region guarded replacement |
|---|---|---|---|---|
| Claude Code `Edit` | 否 | 否 | 否 | 有条件可用 |
| Claude Code `Write` | 否 | 否 | 否 | 否 |
| Codex `apply_patch`（固定实现） | 否 | 否 | 否 | 默认拒绝 |
| Python 标准库通用路径 API | 否 | 最终分量可实现 | 否 | 可实现 check/write，但仍非严格替换 |
| `os.replace` / rename 类 API | 否 | 否 | 否 | 否 |

“否”表示没有找到满足 Bridge 严格定义的公开契约，不表示所有平台上永远无法构造
该能力。后续 host/platform adapter 可以在绑定 tool version、platform、filesystem
与路径安全前提后提供更窄的证明；未证明时必须默认拒绝。

## Claude Code

Claude Code 官方工具文档说明：

- [`Edit`](https://code.claude.com/docs/en/tools-reference#edit-tool-behavior)
  对唯一 `old_string` 做 exact string replacement，不使用 regex 或 fuzzy match；
- 同一文档也明确说明，文件在上次读取后已改变时，只要 `old_string` 在当前内容中
  仍精确且唯一，编辑仍可继续；
- [`Write`](https://code.claude.com/docs/en/tools-reference#write-tool-behavior)
  创建新文件或用完整提供内容覆盖现有文件。

因此 `Edit` 可以作为 `guarded-patch/v1` 的 exact-literal 候选，但不能证明完整文件
仍等于计划 preimage。并发写可能发生在 preflight 与工具内部匹配/写入之间；即使把
完整旧文件作为 `old_string`，它也可能在被添加前缀或后缀后的当前文件中继续唯一
匹配。`Write` 的 read-before-write 要求不是 create-if-absent 或 expected-bytes
条件。

## Codex

核验固定在 OpenAI Codex commit
[`0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1`](https://github.com/openai/codex/tree/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1)。
该版本的
[`apply-patch/src/lib.rs`](https://github.com/openai/codex/blob/0dfa778dae6a94b2ff2c69176cbaf063a3bf18a1/codex-rs/apply-patch/src/lib.rs)
显示：

- add 路径直接调用写文件接口，并会记录可能被覆盖的旧内容；
- update 先读取文本、计算新内容，再调用写文件接口；
- delete 先读内容，再调用 remove；
- patch region 的定位属于 patch matching，不是完整 expected bytes 与 mutation
  绑定的单一条件原语。

这些步骤有助于错误报告与局部变更追踪，但没有关闭读取与写入/删除之间的竞态。
同时 patch matching 不是 Bridge 所需的 exact-literal 唯一替换契约，所以当前
Codex `apply_patch` adapter 对严格原语和 `guarded-patch/v1` 都默认拒绝。

## 标准库与 filesystem 边界

Python
[`open(..., "x")`](https://docs.python.org/3/library/functions.html#open)
能让最终路径分量以 exclusive creation 打开，路径已存在即失败。这可以成为
`strict-create/v1` 的底层原语，但完整能力仍需 adapter 证明父目录链、链接/
reparse-point、路径 containment、写入失败清理与目标 filesystem 前提。

Python
[`os.replace`](https://docs.python.org/3/library/os.html#os.replace)
在满足平台条件时提供 rename 的目录项原子性，但会静默替换已有目标；它不携带
“目标 bytes 必须等于 expected value”的条件。因此临时文件加 `os.replace` 不能
被描述为 byte compare-and-swap。advisory lock 也只能约束合作进程，不能阻止宿主
外部写者。

POSIX 的 descriptor-relative path walk、Linux `openat2`，或 Windows 原生 handle
可以增强路径安全，并可能在特定平台构造更强 adapter；它们不是当前 Python
标准库与两宿主内建文件工具共同提供的可移植严格替换/删除原语。

## 对 Bridge 的约束

- 严格 replace/create/delete 只能来自显式、版本化、环境绑定的 capability
  adapter；默认值全部是 unavailable。
- `guarded-patch/v1` 必须保留独立名称和结果证据，不能被记作 CAS、transaction 或
  atomic replace。
- preflight 只能过滤已发生的 stale plan；postverify 只能证明某个观察时刻的完整
  bytes。两者不能消除工具调用内的 residual race。
- create 只有真实 create-if-absent 才可执行；delete、rename 与自动 compensation
  不得降级到 guarded sequence。
- M3 的协议决策见[写入协议 ADR](../architecture/write-protocol.md)。
