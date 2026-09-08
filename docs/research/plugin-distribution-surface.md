# 插件分发面

采集日期 2026-09-08。对象：Claude Code 2.1.263、codex-cli 0.153.4（openai/codex
tag `rust-v0.153.4`），Windows 11 本机；Codex 侧结论以官方文档与该 tag 源码为准，
Claude 侧以官方文档与本机探测为准。本文只记录 host 机制，设计结论见
[分发模型](../implementation/distribution-model.md)。

## Claude Code 插件清单

- `.claude-plugin/plugin.json` 可选；存在时只有 `name` 是加载期必填。但
  `claude plugin validate --strict` 会把缺少 `version`、`description`、`author`
  的警告升级为失败，所以产物四者齐备。
- 识别字段：`name`、`$schema`、`displayName`、`version`、`description`、
  `author`（对象）、`homepage`、`repository`、`license`、`keywords`、`metadata`、
  `defaultEnabled`，加 13 个组件路径字段（`skills`、`commands`、`agents`、
  `workflows`、`hooks`、`mcpServers`、`outputStyles`、`lspServers`、
  `experimental`、`userConfig`、`channels`、`dependencies` 等）。未知顶层字段
  加载期忽略、校验期警告、`--strict` 下失败；识别字段类型错误则加载失败。
- `skills/<name>/SKILL.md` 无需 `skills` 字段即被发现；`skills` 是唯一"追加
  而非替换"默认扫描目录的路径字段。`package.json` 加 lockfile 会触发 Node 依赖
  自动安装，产物不带 `package.json`。
- 插件根目录的 `CLAUDE.md` 触发警告（`--strict` 失败），且不作为项目上下文
  加载；`README.md`、`LICENSE`、`CHANGELOG.md` 无警告；顶层 `bin/` 被 claude.ai
  组织分发拒绝。
- `plugin details <name>` 会列出组件清单与常驻 token 估算，但对不存在的插件也
  以退出码 0 返回；`validate --strict --json` 对健康插件返回空 `contents`，
  不能证明 skill 数量。自动化检查应把退出码非 0 视为失败，并用
  `Skills (2)  bridge-sentinel, bridge-sync` 一行做字面断言。

## Claude Code 插件 skill 运行期

- skill 正文渲染后作为一条消息进入会话，后续轮次不再重读。渲染时替换正文与
  `allowed-tools` Bash 规则中的 `${CLAUDE_SKILL_DIR}`、`${CLAUDE_PLUGIN_ROOT}`、
  `${CLAUDE_PLUGIN_DATA}`、`${CLAUDE_PROJECT_DIR}`；Windows 上展开为带盘符的
  正斜杠绝对路径。本机探测：不含任何占位符的正文同样收到 host 告知的技能
  基目录（反斜杠形式）。
- `${CLAUDE_PLUGIN_ROOT}` 只作为环境变量导出给 hook、MCP、LSP 进程，普通 Bash
  子进程读不到；被调用脚本的 cwd 是会话目录而非技能目录。
- 未声明 `allowed-tools` 时，从不含插件的 cwd 读取插件缓存内文件会被拒绝
  （`-p` 非交互运行中观察为 DENIED）；声明 `allowed-tools: Read` 后同一读取
  成功，兄弟目录 `../<skill>/` 与 `../../templates/` 同样可读，Bash 仍可用且
  照常提示。工作区信任从不影响 `allowed-tools`。
- Read / Edit 路径规则用 gitignore 语法：`//path` 是文件系统绝对路径，单斜杠
  锚定在设置来源，`~/` 锚定家目录；Windows 路径先归一化成 `/c/Users/...`，
  绝对匹配要写 `//c/**`。带路径的允许规则因此跨平台不稳定。
- 插件 skill 名为 `<plugin>:<skill>`，与项目级同名 skill 并存而不遮蔽，裸名
  `/bridge-sentinel` 解析到项目级 skill。`skillOverrides` 不能关掉单个插件
  skill，只能禁用或卸载整个插件。
- 插件树每次更新换目录，旧目录约两周后清理；持久状态放
  `${CLAUDE_PLUGIN_DATA}`（`~/.claude/plugins/data/<id>/`）。市场安装是复制，
  插件根之外的内容与指向外部的 symlink 不进入缓存，`../` 组件路径被拒绝。

## Codex 插件清单

- 清单查找顺序固定：根 `plugin.json`（agent-plugins.org 格式）→
  `.codex-plugin/plugin.json` → `.claude-plugin/plugin.json` →
  `.cursor-plugin/plugin.json`，取第一个常规非 symlink 命中。`.codex-plugin/`
  存在时静默遮蔽 Claude 清单；只有 `.claude-plugin/` 的目录也能装进 Codex。
- 根 `plugin.json` 是陷阱：它把清单降为 10 键白名单、强制 `skills` 为
  `./skills`、只发现直接子目录、跳过 hook 加载并把 skill 正文截断到 8000 字节。
- 运行期只要求文件可解析：`name` 为空回退到目录名，`version` 缺失时缓存目录
  名为字面 `local` 并永久优先于任何 semver 目录。实践上 `name` 必须与市场条目
  名一致（否则安装硬失败），`version` 必须是严格 semver。
- 官方脚手架的 `validate_plugin.py`（codex-cli 安装或加载时并不运行它）要求：
  `name` 匹配 `[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*`、`version` 严格 semver、非空
  `description`、`author` 对象含非空 `name`、`interface` 含非空 `displayName`
  / `shortDescription` / `longDescription` / `developerName` / `category`、
  `defaultPrompt` 存在、`capabilities` 为字符串数组；顶层 13 键白名单（`id`、
  `name`、`version`、`description`、`skills`、`apps`、`mcpServers`、
  `interface`、`author`、`homepage`、`repository`、`license`、`keywords`），
  `hooks` 键不在其中，hook 应放 `hooks/hooks.json` 而不声明键。
  `interface.category` 与 `capabilities` 没有枚举，自由字符串；`brandColor`
  匹配 `^#[0-9A-F]{6}$`。
- `"skills": "./skills/"` 是同时满足校验器（归一化为 `skills`）与运行期
  （必须 `./` 开头）的唯一写法；声明值替换默认值而不是追加。
- `<skill>/agents/openai.yaml` 逐技能生效且 fail open：未知键忽略，损坏文件
  整体忽略；`policy.allow_implicit_invocation: false` 是 Codex 侧关闭隐式调用
  的机制，`disable-model-invocation` 会被 `validate_plugin.py` 拒绝。

## Codex 插件 skill 运行期

- 正文逐字注入，`ext/skills/src/render.rs` 没有任何 `${...}` 替换；含
  `${CLAUDE_PLUGIN_ROOT}` 的 Claude 风格正文会原样到达模型。唯一的 `${KEY}`
  展开在插件 hook 的 `command` / `commandWindows`（`PLUGIN_ROOT`、
  `PLUGIN_DATA`、`CLAUDE_PLUGIN_ROOT`、`CLAUDE_PLUGIN_DATA`）与 AgentPlugin
  格式的 MCP stdio 参数中；Windows 上先选 `commandWindows` 再展开。
- 模型两次得知路径：注入片段中的 `<path>` 与目录行 `- {name}: {desc} (file:
  {locator})`；系统提示要求"相对包含该 `SKILL.md` 的目录解析相对路径"并优先
  运行自带 `scripts/`。官方 `latex` 插件同样以 `python3 scripts/...` 方式
  调用自带脚本。
- 插件 skill 的模型可见名为 `<manifest name>:<skill>`（源码
  `ResolvedSkillNamespace::qualify`），`$plugin:skill` 是单个提及 token；
  frontmatter `name` ≤ 64 字符，限定名 ≤ 129 字符。插件 skill 根是
  `SkillScope::User`，目录预算下最先被截断；`description` 全文进入目录，
  `short_description` 不减少开销。项目级 skill 根只有 `.agents/skills` 与
  `.codex/skills`，顶层 `skills/` 与 `plugin/skills/` 都不会被发现。
- frontmatter 解析只读 `name`、`description`、`metadata.short-description`，
  未知键忽略；官方 `quick_validate.py` 只允许 `name`、`description`、
  `license`、`allowed-tools`、`metadata`，并在 Windows 默认 GBK 代码页下需要
  `PYTHONUTF8=1` 才能读取 UTF-8 文件。
- 默认沙箱：全盘可读、网络关闭，项目内 `.git`、`.agents`、`.codex` 只读；
  Windows 命令经 `pwsh -NoProfile -Command` 执行。本机 `python3`（pyenv
  3.12.9）与 `python`（3.14.5）是不同解释器，文档不能硬编码任一名字。
- 插件自带 hook 属非托管，需用户在 `/hooks` 逐条信任，编辑后重新信任；插件
  skill 不经信任审查，也不受项目信任门控。

## 市场

- Codex 市场清单查找顺序：`.agents/plugins/marketplace.json`、
  `.agents/plugins/api_marketplace.json`、`.claude-plugin/marketplace.json`、
  `.cursor-plugin/marketplace.json`，取第一个命中；没有
  `.codex-plugin/marketplace.json`。顶层必填 `name` 与 `plugins`，条目必填
  `name` 与 `source`，`policy` 缺省为 `AVAILABLE` / `ON_INSTALL`，未知键静默
  接受。因此仓库根一份 `.claude-plugin/marketplace.json` 同时服务两侧，但必须
  停留在两侧 schema 的交集：`name`、`owner`、顶层 `description`、
  `plugins[{name, description, source}]`；加入 Codex 的 `policy` / `interface`
  会让 Claude `--strict` 失败，Claude 侧缺少顶层 `description` 也会失败。
- 条目 `source` 相对**市场根**（去掉清单相对路径后的目录）解析，必须以 `./`
  开头且不得 `..`；`"."` 在 Codex 合法、在 Claude 报不支持，`"./plugin"` 两侧
  都合法。`local` 源不能离开市场根；`url` / `git-subdir` / `npm` 可以。
- Claude 市场条目声明 `version` 且与 manifest 不一致时，`plugin tag` 与对本地
  路径条目的 `validate --strict` 都失败；条目省略 `version` 时相对路径插件按
  commit SHA 解析。Codex 条目没有 `version` 字段。
- 两侧的 git 市场都克隆整个仓库（Claude 到 `~/.claude/plugins/marketplaces/
  <name>`，Codex 到 `~/.codex/.tmp/marketplaces/<name>`），再只复制插件目录进
  缓存；`--sparse`（Codex）只对 git 源生效，需要同时包含清单目录与插件目录，
  未实测。`owner/repo` 简写解析到默认分支；Claude 简写走 SSH，除非设置
  `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`。
- 目录级校验不打开插件内的 skill / agent / hook 文件，所以市场根与 `./plugin`
  要分别 `validate --strict`，再对 `./plugin/skills` 校验 frontmatter。
- Codex 没有 `--plugin-dir`；`codex plugin add` 只接受 `PLUGIN@MARKETPLACE`，
  CLI 子命令不自动发现仓库根市场，必须先 `codex plugin marketplace add`。
  格式错误的 Codex 条目被警告后跳过而不报错，验证要断言条目出现在
  `codex plugin list --available --json` 里；`-c marketplaces.<key>.*` 覆盖
  只对该次调用生效，每条命令都要重复。同名市场不能改指向不同来源，需先
  `marketplace remove`。
- 写入位置：Claude `marketplace add` 写用户级 `known_marketplaces.json`，
  `install` 写 `enabledPlugins`（默认用户设置，`--scope project` 写仓库内
  `.claude/settings.json`）、`installed_plugins.json` 与
  `~/.claude/plugins/cache/<market>/<plugin>/<version>/`；Codex
  `marketplace add` 写 `~/.codex/config.toml` 的 `[marketplaces.<name>]`
  （Windows 本地路径存为 `\\?\C:\...`），`plugin add` 写
  `[plugins."<plugin>@<market>"] enabled = true` 与
  `~/.codex/plugins/cache/...`，两者都不确认。第三方与本地市场在 Claude 默认
  不自动更新；`extraKnownMarketplaces` 项目设置不会自动安装外部来源插件。
