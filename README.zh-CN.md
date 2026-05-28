# AIcoding Governance Kit

[English](README.md)

AIcoding Governance Kit 是一个面向 AI 编码 agent 的轻量级治理层。它把
Codex 生命周期 hooks、Git pre-commit 检查、工作日志和收口检查组合起来，
避免 agent 驱动的项目在增长过程中丢失操作记忆。

## 为什么需要它

我们已经进入 AI 编码时代。很多没有传统软件工程背景的人，正在使用编码
agent 构建真实产品、自动化工作流，并推进过去难以触及的想法。

这很强大，但也带来一种新的失败模式。项目一开始可以进展很快，随后却变得
难以信任：仓库漂移、版本混乱、部署步骤被遗忘、操作变更没有记录，技术债
悄悄累积。对代码不熟悉的构建者很容易陷入可避免的循环，因为 agent 改动的
速度可能快过项目解释自身的速度。

AIcoding Governance Kit 就是为这些构建者准备的。它给 AI 编码工作流加入少量
纪律：

- 检测实质性的代码、配置、服务、数据和 Git 操作
- 在明显危险的命令执行前进行阻断
- 将 agent 活动记录到本地审计日志
- 在实质性会话结束前要求日志、manifest 或 commit 证据
- 阻止大型运行时产物和秘钥进入 Git
- 提供可复用的项目收口脚本

它不能替代工程判断。它为构建者和 agent 提供一种可重复的方式，在有意义的
工作之后留下证据。

## 包含内容

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

## 快速开始

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

运行收口检查：

```bash
python3 scripts/agk_closeout_check.py --repo /path/to/your/repo
```

追加日志记录：

```bash
python3 scripts/agk_journal_update.py --domain ops --item "Updated deployment config and verified service health"
```

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
- `AGK_JOURNAL_INCLUDE_LOCAL`：设为 `1` 时，日志会包含主机名和绝对 CWD。
  默认会脱敏本地机器元数据。

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

## 状态

这是从真实 AI 辅助运维工作流中抽取出来的早期工具包。在重要仓库中启用
`enforce` 模式前，请先审计默认配置。

本项目100％由codex编写。
