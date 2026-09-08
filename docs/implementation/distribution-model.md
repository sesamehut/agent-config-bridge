# 分发模型

## 仓库角色

本仓库采用单仓库模式：上游开发态内容（skill 源、工具映射知识、打包与 doctor 脚本、
文档、测试）和可安装插件产物位于同一个仓库。分发形态由仓库内的 `plugin/` 子目录
承载，仓库根目录同时作为只含这一个插件的自托管市场。

Bridge 的主要产物是 skill 和知识库，代码只承担入口和辅助检查职责。仓库内部按角色分层：

- `skills/`：skill 源，面向目标工具中智能体的 skill 内容，markdown 为主；可含
  必要的 host metadata、reference specs 和过窄门的机械辅助脚本，入库。严格只读的
  `bridge-sentinel` 与独立写侧 `bridge-sync` 两种权限不能重新合并。
- `templates/`：面向目标项目安装的约定模板等写入素材，与只读 skill 指令分离，
  入库；只有路线图开放相应写路径后才会安装。
- `knowledge/`：工具映射知识，自然语言知识库，带采集日期，入库。
- `fixtures/`：验证用夹具项目，携带已知状态与期望报告，供哨兵等 skill 对照
  校验，入库；不进入插件产物。
- `scripts/`：打包脚本 `package_plugin.py` 与 doctor 脚本 `bridge_doctor.py`
  的源，Python 3.9+ 标准库，入库。没有 `src/`、`dist/`、`package.json` 或任何
  Node 工具链；原先"若包装脚本使用 TypeScript"的 `src/` / `dist/` 分层不再需要。
- `VERSION`：唯一的版本来源，一行严格 semver，入库。
- `.claude-plugin/marketplace.json`：仓库根的市场清单，**生成物**，把
  `./plugin` 登记为唯一条目；Claude Code 与 Codex 都从这个文件解析市场。
- `plugin/`：可安装插件产物，作为**入库的边界产物**提交；skill、templates 与
  knowledge 从上游拷入，doctor 脚本从 `scripts/` 拷入，两份 host manifest、
  产物 README 与 `.gitattributes` 由打包脚本渲染。

`plugin/` 与根市场清单虽然入库，但仍按生成物管理：`python -B
scripts/package_plugin.py build` 从允许清单重新组装，`verify` 在字节层面比对
入库产物与重新组装结果并做产物审计，任何漂移都失败。要改变行为，应修改上游
skill、知识或脚本后重新 `build`，不直接手工编辑产物目录。产物 README 顶部带
GENERATED 标记说明这一属性。

## 形态：skill 为主，包装为辅

分发主体是 skill 和工具映射知识。它们本身是文本，不需要编译成可执行文件。
用户机前置依赖与环境预检规则见
[tech-stack.md 依赖边界](../architecture/tech-stack.md)；两个 skill 各自在
Procedure 第一步探测 Git 与 Python 并在缺失时停下，这是真正的开工前预检。
`plugin/scripts/bridge_doctor.py` 是同一组检查的手工排障版本：离线、只读、
不在插件树内写任何字节，供用户在安装后自行核对解释器、Git、产物布局、两份
manifest 的一致性与哨兵机械自测。

发布产物不携带上游开发记录：`bridge-intent.yaml` 是用户项目为自己的受管技能维护的
机制，本仓库的技能源在开发期不维护这份文件，发布产物中也不出现；技能出处由发布
版本号加本仓库的 git 历史承担，用户收编技能后从自己的第一条意图记录开始。

用户安装插件后将获得 read-only Sentinel 与 plan-confirm-write Sync；具体流程由
目标工具中的智能体执行，Git 提供 per-unit baseline 与 ownership evidence。Sync
把全部选中的 root `AGENTS.md` block 变化合成为一个完整 desired image；替换现有
文件时按 capability profile 选择已证明的 strict replace，或明确非 CAS 的
`guarded-patch/v1` 单次 exact-region replacement；新建、删除、rename 与
compensation 仍要求对应 strict primitive。缺少合格协议就阻断，不用无标识的
"先检查、再普通写入"替代，也不扩张为跨文件事务保证。

## 单一产物目录服务两个 host

`plugin/` 同时是 Claude Code 插件根与 Codex 插件根：`.claude-plugin/plugin.json`
与 `.codex-plugin/plugin.json` 并列，`skills/`、`templates/`、`knowledge/`
保持与上游相同的兄弟布局。两个 host 都会静默接受对方的 manifest 目录并把整个
目录复制进各自的缓存；两个 skill 正文的全部相对引用（`<skill-dir>/scripts/`、
`../bridge-sentinel/`、`../../templates/covenant/`、`../../knowledge/`）在仓库与
产物里按同一相对路径解析，因此 skill 正文逐字节拷贝，不按 host 分别渲染。
机制依据见[插件分发面](../research/plugin-distribution-surface.md)（核对日期
2026-09-08）。

产物根目录**不**放 `CLAUDE.md`、`AGENTS.md`、裸 `plugin.json`、`bin/` 或任何
hook：前两者会触发 Claude 严格校验失败与本仓库的 twin 规则，裸 `plugin.json`
会让 Codex 切换到另一套更受限的清单格式，hook 一律不随插件分发。

## Claude Code 入口

核对日期 2026-09-08（Claude Code 2.1.263）：

- 插件 skill 的正文进入会话时，host 会告知该 skill 的绝对基目录，并就地替换
  正文与 `allowed-tools` 中的 `${CLAUDE_SKILL_DIR}`、`${CLAUDE_PLUGIN_ROOT}`、
  `${CLAUDE_PLUGIN_DATA}`。Bridge 的正文不依赖任何占位符，只写"相对本
  `SKILL.md` 解析"，因为同一份正文也交给不做任何替换的 Codex。
- 安装后的产物位于会话 cwd 之外，Read 工具默认不能读取；两个 skill 的
  frontmatter 因此声明 `allowed-tools: Read`，让 skill 能读到自带的 references、
  templates 与 knowledge。它只放开只读工具，用户的 deny 规则仍然生效；带路径的
  `Read(<path>)` 形式因单斜杠、双斜杠与 Windows 盘符的锚定规则跨平台不一致，
  M5 不采用。运行自带 Python 脚本走正常的 Bash 权限确认，不预授权。
- 持久状态使用 `${CLAUDE_PLUGIN_DATA}`；插件树本身每次更新都会换目录，任何流程
  都不得向插件树内写入。
- skill 名带插件前缀：`/agent-config-bridge:bridge-sentinel`、
  `/agent-config-bridge:bridge-sync`，与开发态源树不冲突。

## Codex 入口

核对日期 2026-09-08（codex-cli 0.153.4）：

- Codex 把 `SKILL.md` 正文逐字注入，不替换任何 `${...}` 占位符；它通过注入片段
  中的 `<path>` 与技能目录中的文件定位告诉模型 `SKILL.md` 的绝对路径，并要求模型
  相对该目录解析正文中的相对路径。因此技能本地的 `scripts/sentinel_mechanics.py`
  就是 Codex 侧的入口，`bridge-sync` 经 `../bridge-sentinel/` 复用它；分发模型
  早先设想的"技能本地包装脚本"由这个已存在的机械脚本承担，不再另加一层。
- 插件 skill 名同样带前缀：`$agent-config-bridge:bridge-sentinel`、
  `$agent-config-bridge:bridge-sync`。打包时把 `agents/openai.yaml` 中
  `default_prompt` 的 `$bridge-*` 提法改写成带前缀形式，这是产物相对上游的两处
  确定性改写之一。
- Codex 只为插件 hook 进程注入 `PLUGIN_ROOT` / `PLUGIN_DATA`（并提供
  `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA` 别名）；skill 正文没有这类机制。
  本插件不分发 hook，所以只记录这一事实。
- Codex 默认沙箱对项目内 `.git`、`.agents`、`.codex` 只读，`bridge-sync` 向
  `.codex/hooks.json` 的写入会触发审批。

## 插件产物

产物由允许清单生成，清单是 `git ls-files` 下 `skills/`、`templates/`、
`knowledge/` 的全部 tracked 文件（symlink、submodule、untracked、ignored 一律
不入）加固定的生成集合：

- 目标工具清单：`.claude-plugin/plugin.json` 只含 Claude 识别的字段；
  `.codex-plugin/plugin.json` 满足 Codex 官方 `validate_plugin.py` 的必填集
  （含 `interface` 与 `"skills": "./skills/"`）。两份 `name` 与 `version` 相同，
  也与市场条目名、目录名一致。
- 技能：权限分离的 `bridge-sentinel` 与 `bridge-sync`，正文逐字节拷贝。
- covenant templates：当前 tuple（`covenant/v3`）的 exact source / managed
  block，以及只作显式 migration evidence 的归档 v1 / v2 exact bytes；
  `templates/hook-intents.example.md` 只是示例文档，任何流程都不安装它。
- 工具映射知识：`knowledge/` 全部文件；指向 `../docs/` 的链接改写为本仓库
  GitHub `blob/main` 地址（显示文本同步去掉 `../`），这是第二处确定性改写，
  `verify` 断言改写目标在上游存在、产物内不残留 `../docs/`。
- doctor：`scripts/bridge_doctor.py`，离线可运行。
- README 与 `.gitattributes`：README 说明前置要求（git、Python 3.9+，无需
  Node）、两侧安装 / 更新 / 卸载命令与它们写入的用户配置、doctor、安全边界与
  生成物属性；`.gitattributes` 让子目录或 sparse 检出仍按 LF 落盘。

`verify` 的产物审计同时是密钥扫描：禁止 `.pem` / `.key` / `.p8` / `.env*` /
`id_*` 等文件名，禁止 PEM 私钥块、AWS / GitHub / OpenAI 风格 / Slack token
形态；`--dangerously-bypass-hook-trust` 只允许出现在 `knowledge/hooks.md` 的
两处文档化说明里，其余任何文件（含 markdown）出现即失败。审计不通过时 `build`
不落盘。打包 allowlist 与 `bridge-sync` 的项目 write-side scope 是两道独立边界。

## 版本策略

`VERSION` 是唯一版本来源，`build` 把它渲染进两份 manifest 与产物 README，
`verify` 断言三者相等且为严格 semver。市场条目不写 `version`：Claude 会在条目
版本与 manifest 版本不一致时让 `plugin tag` 与严格校验失败，Codex 的市场条目
没有版本字段。发布 tag（`claude plugin tag` 生成 `agent-config-bridge--v<版本>`）
属于 M6 的发布流程，M5 不打 tag。

两个 host 都以声明的版本作为更新信号：版本不变则用户停留在缓存副本；第三方与
本地市场默认不自动更新，README 因此给出显式的更新命令。

## 市场发布

仓库根的 `.claude-plugin/marketplace.json` 让用户直接从仓库安装：Claude Code
可用 `--plugin-dir ./plugin` 免安装试用，或先 `marketplace add` 再 `install`；
Codex 没有 `--plugin-dir` 等价物，必须先 `codex plugin marketplace add`，再
`codex plugin add agent-config-bridge@agent-config-bridge`。两侧的 git 形式都会
克隆整个上游仓库（含 `docs/` 与惰性的 `fixtures/`），只把 `plugin/` 复制进插件
缓存；README 提醒用户不要在市场克隆目录里启动会话。

登记到类似 `sesamehut/plugins-marketplace` 的外部市场仍放在插件产物可安装、
doctor 可用、版本策略稳定之后，届时再决定。
