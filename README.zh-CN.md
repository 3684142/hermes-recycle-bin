# hermes-recycle-bin

[English](README.md) | [简体中文](README.zh-CN.md)

一个 Hermes Agent 插件：让 Agent 执行的 `rm` 删除**移入 Windows 回收站**，而不是永久删除。
用官方插件命令即可开关，不用改配置文件。

```bash
hermes plugins enable recycle-bin      # 删除改为移入回收站（下一会话生效）
hermes plugins disable recycle-bin     # 恢复永久删除（下一会话生效）
```

给"让 AI 在自己电脑上跑命令"的人用 —— 需要一层能在 Agent 判断失误时兜底的安全网。

> **适用范围：仅 Windows。** 插件在 macOS/Linux 上会拒绝注册（未接入对应平台的回收站机制）。
> 依赖它之前请先读[边界](#边界)。

## 为什么做这个

Hermes 的 `terminal` 工具通过 git-bash 执行命令，其中的 `rm` 会直接 unlink 文件 —— 一删就没了。
Agent 认错目录来一次 `rm -rf`，文件无法找回。Hermes 官方没有回收站开关（官方的恢复手段是
`checkpoints`/`/rollback`，默认关闭，以及桌面端文件浏览器的删除按钮）。本插件补上这个缺口：
把一个 `rm` shim 插到 `/usr/bin` **之前**，且**只影响 Agent 自己的 shell 命令**。

## 工作原理

```
terminal 工具调用
      │
      ▼
pre_tool_call 钩子  ──►  前置一行: export PATH="<插件目录>/bin:$PATH"
      │
      ▼
bash 执行命令
      │  `rm foo.txt` 解析到 <插件目录>/bin/rm（而不是 /usr/bin/rm）
      ▼
bin/rm（shim）  ──►  cygpath -w  ──►  trash.py
                                        │
                                        ▼
                         shell32 SHFileOperationW（FOF_ALLOWUNDO）
                                        │
                                        ▼
                                  Windows 回收站  ♻
```

| 文件 | 作用 |
|---|---|
| `__init__.py` | `pre_tool_call` 钩子 + `/recycle-bin` 斜杠命令 |
| `bin/rm` | 兼容 GNU 的 `rm` shim（支持 `-f`、`-r`、`-rf`、`--`、多路径、`--version`） |
| `trash.py` | 回收站后端：`SHFileOperationW` + `FOF_ALLOWUNDO │ FOF_NOCONFIRMATION │ FOF_SILENT │ FOF_NOERRORUI` |
| `list-bin.ps1` | 辅助工具：列出回收站中匹配的条目及原目录 |

你自己的 PowerShell、Git Bash、资源管理器以及机器上其它程序**完全不受影响** ——
PATH 改动只作用于 Agent 的 `terminal` 调用。

## 安装

见 [INSTALL.zh-CN.md](INSTALL.zh-CN.md) —— 三步，无需编译。
English: [INSTALL.md](INSTALL.md)

## 使用

```
/recycle-bin status    # 查看 shim 路径、注入行、绕过边界
/recycle-bin verify    # 实测删一个临时文件并确认进了回收站
/recycle-bin open      # 打开 Windows 回收站
```

`verify` 输出示例：

```
[recycle-bin] probe deleted (shim exit=0); Recycle Bin check -> IN-BIN: hermes-recycle-bin-verify.txt
```

## 边界

以下路径**不会**经过 shim（设计如此），仍是永久删除：

| 绕过场景 | 原因 |
|---|---|
| `/usr/bin/rm`、`command rm` | 绝对路径不经过 PATH 查找 |
| Python `os.remove` / `shutil.rmtree`、`find -delete` | 不是 shell 的 `rm` 调用 |
| `mv`、覆盖写 | 从不经过 `rm` |
| cron 脚本任务（`hermes cron script=...`） | 走 `subprocess` + 净化环境，不经过终端 PATH |
| 机器上其它程序 | PATH 改动仅限 Agent 的终端工具 |

与 GNU `rm` 的行为差异：

- `rm -i` 不会弹确认（网关会话没有 TTY，文件会被删除）。
- `rm -v` 不打印 `removed '…'`。

两者对 Agent 场景都是无关紧要的差异。其余行为（`-f`、`-r`、`-rf`、`--`、多路径、
文件不存在时的处理、`--version`）均与 GNU 一致。

## 安全说明

- 删除物占用其原盘空间，直到清空回收站。各卷配额见
  `HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\BitBucket\Volume`
  （`MaxCapacity`，单位 MB）；超配额时 Windows 会清理最旧的条目。
- `FOF_NOERRORUI` 是保证无头网关不会卡在弹窗上的关键标志，请勿移除。
- 钩子只对 `tool_name == "terminal"` 生效，且幂等 —— 路径已存在时不会重复注入。
- 已实测不干扰 Hermes 的危险命令审批：前置 `export PATH=…` 行后，
  `rm -rf /`、`sudo rm -rf /etc`、`dd if=/dev/zero of=/dev/sda`、fork bomb 等的
  `detect_dangerous_command()` 结果保持不变。

## 兼容性

- Windows 10/11；Hermes Agent 需支持原生插件系统（`hermes plugins`）。
- 依赖 git-bash（随 Git for Windows 安装，Hermes 本就以它作为 shell）与 Hermes venv 的
  Python —— 两者自动探测，无硬编码路径。
- 插件 manifest v1（`kind: standalone`）、一个 `pre_tool_call` 钩子、一个斜杠命令。
  不含工具、无第三方依赖、无网络访问。

## 常见问题

**会影响我自己的终端吗？**
不会。PATH 前置只发生在 Agent 的 `terminal` 工具调用内部。

**删大文件怎么办？**
一样进回收站；Windows 按卷配额处理，满了会清理最旧条目。

**怎么找回文件？**
用 `/recycle-bin open` 打开回收站，或用 `list-bin.ps1` 定位后在资源管理器里还原。

**多 Hermes profile 能用吗？**
能 —— shim 从自身所在位置推导路径，放在任意 `HERMES_HOME/plugins/recycle-bin/` 下都可用。

## 卸载

```bash
hermes plugins disable recycle-bin     # 停用（保留文件）
# 或彻底移除：
hermes plugins remove recycle-bin
```

## 许可

MIT —— 见 [LICENSE](LICENSE)。
