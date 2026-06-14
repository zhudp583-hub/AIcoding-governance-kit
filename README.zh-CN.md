# AIcoding Governance Kit

[English](README.md)

这是给没有代码背景的 AI coder 用的。一个简单的测试方法：如果你知道什么是
“代码git化”，那么你并不需要它；如果你不知道，我就是这样的人。

项目进行到一定的复杂度的时候，agent 会突然抓起一个 20 个版本前的代码就用，
然后发现不符合预期，于是我连着迭代了一周，最后发现只是原地打转。原来那些
bug 我三个月前就修完了，并且已经有一个很完美的方案。

我靠着这个工具解决了这些问题。它能帮你在每次重要修改前后留下日记，帮你
理清楚代码主干和旁支，防止你跑错版本、提交错文件、忘记自己推进到一半的
思路。

所以我把这个工具分享出来，希望能帮到你，祝你一切顺利。

*以上是本项目中唯一由人类书写的部分。*

##

AIcoding Governance Kit 是一个给 AI 编码项目使用的轻量级治理工具包。它把
Codex 生命周期 hooks、Git pre-commit 检查、项目日志和收口脚本组合起来，让
agent 可以快速推进，同时不至于悄悄丢失项目脉络。

它故意保持本地化和文件化：不需要服务器，不需要 SaaS 账号，不需要数据库，也
不绑定任何私有基础设施。安装 hooks，把脚本放进项目，然后按你的仓库规则调整
配置即可。

## 它解决什么问题

AIcoding Governance Kit 关注的是一个很实际的问题：agent 驱动的项目需要记忆、
边界和证据。

它可以帮你：

- 在 Codex session 启动时加载治理上下文
- 识别实质性工具调用，例如编辑、提交、服务命令、数据命令和跨机器同步
- 阻断少量最容易破坏用户工作的危险命令
- 防止秘钥、模型、数据库、日志、导出文件等受保护产物进入 Git
- 把 hook 事件记录到本地，方便审计和排查
- 普通代码工作默认使用 Git status、diff 和 commit 作为证据
- 对高影响操作要求更强的收口证据
- 提供一份可复用的 Codex skill，告诉 agent 如何干净交接工作

它不能替代工程判断、CI、备份、分支保护或人工 review。它的作用是处理 AI 编码
中最常见的日常失控：agent 改得很快，但项目解释不清自己到底发生了什么。

## 工作方式

这个工具包有四层：

1. **Codex 生命周期 hooks**

   hook 会在 `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`
   和 `Stop` 阶段运行。它会注入操作上下文，记录实质性工作，阻断部分破坏性
   命令，识别受保护产物路径，并且只在工作进入高影响范围时要求收口证据。

2. **Git pre-commit 守卫**

   pre-commit hook 会在提交前检查 staged 文件。它会阻断受保护产物路径、大
   文件、常见秘钥模式，以及没有日志、报告或 manifest 的实质性源码、配置、
   hook 变更。刚接入项目时也可以切到 warn-only 模式。

3. **收口脚本**

   `agk_closeout_check.py` 用于检查仓库是否可以交接，以及是否还有受保护产物
   处于 dirty 或 staged 状态。`agk_journal_update.py` 用于在确实需要日志或
   manifest 时追加简短、带时间戳的工作记录。

4. **Agent 操作 skill**

   `skills/agent-operational-governance/SKILL.md` 给 agent 一套紧凑的工作模型：
   临时输出放进 `scratch/`，普通工作优先使用 Git 证据，不把运行时产物提交进
   仓库，高影响操作必须用 commit 或 manifest 收口。

## 仓库内容

- `hooks/hooks.json`：Codex session、prompt、tool 和 stop 事件的 hook 注册。
- `hooks/agent_governance_hook.py`：生命周期 hook 实现。
- `git-hooks/pre-commit`：可移植的 pre-commit wrapper。
- `git-hooks/agk_pre_commit.py`：针对已暂存文件的日志、秘钥和受保护产物守卫。
- `git-hooks/agk_repo_smoke.py`：可选的仓库专属 smoke check 扩展点。
- `scripts/install_codex_hooks.sh`：将 Codex hook 文件安装到
  `~/.codex/agent-governance-kit`。
- `scripts/install_git_hooks.sh`：将 Git pre-commit 守卫安装到指定仓库。
- `scripts/agk_journal_update.py`：向日志追加收口记录。
- `scripts/agk_closeout_check.py`：在交接前检查仓库状态。
- `skills/agent-operational-governance/SKILL.md`：描述操作纪律的 Codex skill。

## 安装

克隆仓库后，在仓库根目录运行安装脚本。

安装 Codex hooks：

```bash
./scripts/install_codex_hooks.sh
```

安装器会把 AIcoding Governance Kit 的 hook 组合并进已有 `hooks.json`，而不是
替换不相关的 hooks。设置 `CODEX_HOME` 可以选择 Codex 配置目录，设置
`AGK_INSTALL_ROOT` 可以选择本工具包的安装位置。

在仓库中安装 Git pre-commit 守卫：

```bash
./scripts/install_git_hooks.sh /path/to/your/repo
```

如果仓库已经有 `pre-commit` hook，安装器会把它保留为
`pre-commit.bak-agk`，并在 AGK 检查通过后由 AGK wrapper 继续调用它。

## 使用

运行收口检查：

```bash
python3 scripts/agk_closeout_check.py --repo /path/to/your/repo
```

允许普通 dirty 工作存在，但仍然检查受保护产物：

```bash
python3 scripts/agk_closeout_check.py --repo /path/to/your/repo --allow-dirty
```

追加日志记录：

```bash
python3 scripts/agk_journal_update.py --domain ops --item "Updated deployment config and verified service health"
```

可用日志域包括 `ops`、`infra`、`prod` 和 `research`。

## 配置

默认配置有意保持通用。请通过环境变量自定义配置，而不是直接编辑 hook 代码。

完整变量列表见 `examples/config.example.env`。

常用变量：

- `AGK_STATE_DIR`：hook 状态的存储位置。
- `AGK_INSTALL_ROOT`：已安装 hook 实现的位置。
- `AGK_HOOK_MODE`：`enforce` 或 `warn`。
- `AGK_JOURNAL_DIRS`：以冒号分隔的日志或 manifest 目录。
- `AGK_PROTECTED_PATHS`：以冒号分隔的路径标记，这些路径不应被提交。
- `AGK_RESEARCH_GRACE_ROOTS`：可选的冒号分隔根目录，允许临时研究文件在一段
  时间内保持 dirty。
- `AGK_RESEARCH_GRACE_PREFIXES`：上述根目录下允许 dirty 的路径前缀。
- `AGK_RESEARCH_DIRTY_GRACE_HOURS`：这些研究路径的宽限小时数。
- `AGK_PRE_COMMIT_WARN_ONLY`：设为 `1` 时，pre-commit 只警告不阻断。
- `AGK_DEFAULT_JOURNAL`：日志 helper 使用的可选默认日志路径。
- `AGK_JOURNAL_INCLUDE_LOCAL`：设为 `1` 时，日志会包含主机名和绝对 CWD。
  默认会脱敏本地机器元数据。

## 收口模型

当前默认是 Git-first。普通源码和文档编辑如果已经能通过 `git status` 和
`git diff` 解释清楚，不需要额外写日志。manifest 用于高影响操作：非
`scratch/` 删除、服务或 cron 变更、数据库写入、跨机器同步、受保护产物、
模型、备份、部署证据，以及其他 Git 无法完整描述的运行时变更。

skill 使用的分区模型是：

- **Green**：只读查询、`scratch/` 下的工作、普通源码和文档编辑、本地 Git
  status/diff/add/commit/log 操作。
- **Yellow**：`scratch/` 外的新文件、普通文档槽位外的新 Markdown、以及
  `git push` 这类有远端影响但仍然由 Git 承载的操作。
- **Red**：非 `scratch/` 删除、数据库写入、运行时或生产配置、service/cron/
  systemd/docker 变更、跨机器同步、受保护产物、模型、备份、hook 变更和部署
  证据。

Red 工作应该用 Git commit 或 manifest 结束。Green 工作如果 diff 已经能解释
清楚，就不应该被额外文书拖住。

## 安全模型

AIcoding Governance Kit 是一个本地防护栏。它用于减少可避免的错误，不是安全
边界。

请配合以下措施使用：

- GitHub branch protection
- CI 检查
- 秘钥扫描
- 备份
- 生产操作的人类审查
- 清晰的回滚流程

## 公开安全默认值

本仓库已经过有意清理，适合公开：

- 不包含私有主机名
- 不包含 IP 地址
- 不包含内部仓库名称
- 不包含个人机器路径
- 不包含秘钥
- 不包含业务专属部署逻辑

项目专属策略应放在本地配置、私有 fork 或私有部署脚本中。

## 项目状态

这是从真实 AI 辅助运维工作流中抽取出来的早期社区工具包。默认规则偏保守，
但任何团队在重要仓库中启用 `enforce` 模式前，都应该先审计这些规则。

适合优先贡献的内容是具体的小改进：

- 不同 Codex 安装方式的更清晰文档
- hook 边界情况的更多测试
- 安全项目配置示例
- 常见接入路径说明

## 状态

本项目100％由codex编写。
