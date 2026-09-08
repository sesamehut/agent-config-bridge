# 技术栈与依赖选型

## 设计取向

Bridge 的能力默认通过 skill 调用目标工具和 LLM 的固有能力，只有过了一道窄门才写代码：

- **默认走固有能力**：文件读写交给目标工具自带的 Read / Edit / Write；每条 path
  先经 versioned capability profile。严格 replace/create/delete 只有被证明才用；
  eligible 现有文本替换可走显式非 CAS 的 `guarded-patch/v1` exact-region 流程。
  不能把“先读再普通写”描述成原子操作。语义判断交给 LLM——尚未沉淀的映射、冲突
  仲裁、从自然语言起草意图。
- **窄门才写代码**：一个操作同时满足“交给 LLM 做费 token”和“用代码实现是小轮子（极简、
  稳定、不随工具语义变）”时，才写死成代码——逐字节比对、空 diff 归一化、已确定映射的
  枚举表、批量 frontmatter 解析。
- **确定性底座**：变更判断与仲裁证据交给 Git。事后 rollback 是新的显式计划，只能
  在用户确认后以 current bytes、reachable history 和精确条件写重建；Git 命令本身
  不授予 blanket restore 权限。

判据落在“是否在重复造已有的大轮子”，而不是“代码越少越好”。

## 主要构成

| 层面 | 用途 | 选定 |
| --- | --- | --- |
| skill 内容 | 快路径 / 哨兵 / 仲裁工作流与护栏 | 面向目标工具中智能体的 skill（markdown + frontmatter） |
| 工具映射知识 | Claude / Codex 语义差异与[保真档位](overview.md) | 已确定映射作枚举表，长尾用自然语言知识库，带采集日期 |
| 源树格式 | 源树条目，便于人工审阅和目标工具中的智能体处理 | markdown + 轻量 frontmatter，加目录约定；不先引入完整 schema 校验层 |
| 确定性底座 | 变更检测、仲裁证据、经新计划确认的底层恢复素材 | git（`diff` / reachable 历史；`restore` 仅可作为用户明确选择后的新计划底层能力，禁止 blanket 使用） |
| 文件读写 | 读取现状、执行版本化 path protocol | capability adapter 证明的 strict primitive，或现有文本文件的 `guarded-patch/v1` exact-literal replacement；边界见[写入协议](write-protocol.md) |
| 输出稳定性 | 减少无意义 diff，保护人工内容 | 受管区块标记 + 落盘前逐字节比对 |
| 只读机械辅助 | M1 哨兵的字节比较、规范化、期望报告比较 | Python 3.9+ 标准库脚本 |
| 打包与 doctor | 从允许清单组装并审计 `plugin/` 产物；离线手工排障 | Python 3.9+ 标准库脚本（`scripts/package_plugin.py`、`scripts/bridge_doctor.py`） |
| 运行时 | 机械辅助、打包与 doctor | Python 3.9+；不需要 Node.js |
| frontmatter / YAML | 解析 skill / 规范条目元数据 | 标准库字节级解析；未引入 `yaml` |

## 依赖边界

- **用户机前置**：git 必装；运行哨兵、sync 与 doctor 需要 Python 3.9+；不需要
  Node.js。git 以外的前置须配环境预检：开工前探测并校验版本，
  缺失时给出安装指引并停下，不静默降级。
- **开发期**：文档与 skill 以文本为主；打包脚本是标准库 Python，没有 dev 工具链。
- **运行期依赖**：默认只依赖 git、Python 标准库和目标工具能力。
