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

## 概览

AIcoding Governance Kit 是一个给 AI 编码项目使用的本地治理工具包。它给 Codex
和 Git 加一点结构，让 agent 可以快速推进，同时仍然留下可信的工作脉络。

它不是 SaaS，不是安全边界，也不是重流程框架。它是一套可以放进仓库、可以审计、
可以按项目调整的 hook + script + skill 工具包。

它的设计刻意走中间路线：

- 不是只写文档。文档如果不和 Git 状态绑定，自己也会漂移。
- 不是默认重管控。每一步都要补流程时，agent 会开始优化治理，而不是优化产品。
- 普通工作 Git-first。源码和文档通常应该由 `git status`、`git diff` 和 commit
  解释。
- 高影响工作要更强证据。运行时变更、数据写入、受保护产物、模型、备份、跨机器
  同步和部署证据，需要 commit 或带 session 标记的 journal/manifest。

## 你会得到什么

- **Codex 生命周期 hooks**：在 session 启动时注入上下文，检查 prompt/tool
  事件，阻断少量破坏性操作，记录 material 工作，并只在高影响工作上强制收口。
- **Git pre-commit 守卫**：阻止受保护产物、大文件、常见秘钥模式，以及项目
  smoke-check 失败的内容进入提交。
- **收口工具**：检查仓库是否可以交接；当 Git 不足以解释工作时，写入带 session
  标记的简短 journal。
- **可复用 agent skill**：告诉 agent 如何使用 `scratch/`、Git 证据、受保护
  产物规则，以及 green/yellow/red 收口模型。

## 现场验证过的行为

AGK 里有几项小功能来自真实的长期 agent 工作区：

- **resume 安全状态**：session 恢复时，hook 会保留之前记录的高影响状态，
  不会因为重开会话就把收口义务清掉。
- **脚本发现提醒**：当 agent 写 `train_*`、`build_*`、`run_*`、`audit_*`
  这类任务型 Python 脚本时，如果附近已经有相似脚本，AGK 会先提醒。
- **脚本 manifest 交接**：如果仓库里有 `scripts/MANIFEST.md`，AGK 会把它复制
  到本次 session 的 scratch 区，让 agent 早点看到脚本归属和不要重复造轮子的
  提示。
- **平衡的 pre-commit 检查**：pre-commit 会阻止受保护产物、疑似秘钥、大型
  运行时文件和 smoke-check 失败。普通实质性编辑默认交给 Git status、diff、
  review 和可选收口策略处理，而不是一律阻断。

## 证据模型

AGK 不把所有操作一刀切，而是按风险分区：

- **Green**：只读工作、`scratch/` 输出、普通源码/文档编辑、本地 Git
  status/diff/add/commit/log。Git 证据足够。
- **Yellow**：`scratch/` 外的新文件、普通文档槽位外的新 Markdown、以及
  `git push` 这类有远端影响但仍由 Git 承载的操作。需要可见，但不阻断普通
  交接。
- **Red**：非 `scratch/` 删除、数据库写入、运行时或生产配置、service/cron/
  systemd/docker 变更、跨机器同步、受保护产物、模型、备份、hook 变更和部署
  证据。必须用 session 后的 commit，或包含 `AGK-Session: <session-id>` 的
  journal/manifest 收口。

Material 但非 red 的工作默认只警告。如果你希望每一次实质性工作都必须收口，
可以设置 `AGK_MATERIAL_CLOSEOUT_MODE=enforce`。

## 安装

安装 Codex hooks：

```bash
./scripts/install_codex_hooks.sh
```

安装器会把 AGK hook 组合并进已有 `hooks.json`，不会替换不相关的 hooks。设置
`CODEX_HOME` 可以选择 Codex 配置目录，设置 `AGK_INSTALL_ROOT` 可以选择本工具包
安装位置。

在仓库中安装 Git pre-commit 守卫：

```bash
./scripts/install_git_hooks.sh /path/to/your/repo
```

如果仓库已经有 `pre-commit` hook，AGK 会把它保留为 `pre-commit.bak-agk`，并在
AGK 检查通过后继续调用它。

## 使用

运行收口检查：

```bash
python3 scripts/agk_closeout_check.py --repo /path/to/your/repo
```

允许普通 dirty 工作存在，但仍然检查受保护产物：

```bash
python3 scripts/agk_closeout_check.py --repo /path/to/your/repo --allow-dirty
```

追加 journal：

```bash
python3 scripts/agk_journal_update.py --domain ops --item "Updated deployment config and verified service health"
```

journal 域包括 `ops`、`infra`、`prod` 和 `research`。helper 会从
`AGK_SESSION_ID` 或最近的 AGK state 文件中写入 `AGK-Session` 标记；也可以用
`--session-id` 手动覆盖。

## 配置

完整环境变量见 `examples/config.example.env`。

| 变量 | 用途 |
| --- | --- |
| `AGK_HOOK_MODE` | Stop hook 的 `enforce` 或 `warn` 模式。 |
| `AGK_MATERIAL_CLOSEOUT_MODE` | material 但非 red 工作的 `off`、`warn` 或 `enforce` 模式，默认 `warn`。 |
| `AGK_PROTECTED_PATHS` | 以冒号分隔的受保护路径标记。 |
| `AGK_JOURNAL_DIRS` | 搜索 journal/manifest 证据的目录。 |
| `AGK_PRE_COMMIT_WARN_ONLY` | 接入 pre-commit 初期可设为 `1`。 |
| `AGK_STATE_DIR` | hook 状态目录。 |
| `AGK_INSTALL_ROOT` | 已安装 hook 实现路径。 |
| `AGK_DEFAULT_JOURNAL` | 可选默认 journal 路径。 |
| `AGK_SESSION_ID` | 可选 journal session 标记覆盖值。 |
| `AGK_JOURNAL_INCLUDE_LOCAL` | 仅在私有 journal 中设为 `1`，用于包含主机名和绝对路径。 |

## 文件

- `agk_common.py`：共用 protected path 匹配逻辑。
- `hooks/hooks.json`：Codex 生命周期 hook 注册。
- `hooks/agent_governance_hook.py`：Codex hook 实现。
- `git-hooks/pre-commit`：可移植 pre-commit wrapper。
- `git-hooks/agk_pre_commit.py`：staged-file 守卫。
- `git-hooks/agk_repo_smoke.py`：可选仓库专属 smoke-check hook。
- `scripts/install_codex_hooks.sh`：安装 Codex hooks。
- `scripts/install_git_hooks.sh`：安装 Git pre-commit 守卫。
- `scripts/agk_closeout_check.py`：交接检查。
- `scripts/agk_journal_update.py`：带 session 标记的 journal helper。
- `skills/agent-operational-governance/SKILL.md`：可复用操作 skill。

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
- 不包含产生这些现场行为的私有工作区主机名、IP 或访问路径

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
