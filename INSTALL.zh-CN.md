# 安装 — hermes-recycle-bin

三步搞定，无需编译、无第三方依赖、不需要 API Key。

## 1. 找到你的 Hermes 主目录

默认是 `%LOCALAPPDATA%\hermes`（PowerShell）：

```powershell
echo $env:LOCALAPPDATA\hermes
```

如果你设置过自定义 `HERMES_HOME`，用那个路径。

## 2. 复制插件目录

把下载的 zip 里的 **`recycle-bin`** 整个目录复制到：

```
<HERMES_HOME>\plugins\recycle-bin\
```

最终结构必须完全是这样（`plugin.yaml` 直接在 `recycle-bin` 里面）：

```
<HERMES_HOME>\plugins\recycle-bin\plugin.yaml
<HERMES_HOME>\plugins\recycle-bin\__init__.py
<HERMES_HOME>\plugins\recycle-bin\trash.py
<HERMES_HOME>\plugins\recycle-bin\list-bin.ps1
<HERMES_HOME>\plugins\recycle-bin\bin\rm
```

> 不要改目录名 —— 插件以 `recycle-bin` 这个名字注册。

## 3. 启用

```bash
hermes plugins enable recycle-bin
```

预期输出：

```
✓ Plugin recycle-bin enabled. Takes effect on next session.
```

再跑一次健康检查，确认 manifest 与钩子注册成功：

```bash
hermes plugins doctor recycle-bin
```

预期：

```
  manifest: recycle-bin 1.0.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 0 tool(s), 1 hook(s)
```

## 验证是否真的生效

**新开一个会话**（插件在会话启动时加载），然后在会话里执行：

```
/recycle-bin verify
```

预期：

```
[recycle-bin] probe deleted (shim exit=0); Recycle Bin check -> IN-BIN: hermes-recycle-bin-verify.txt
```

如果显示 `FAILED`，执行 `/recycle-bin status`，检查它打印的 shim 路径在磁盘上是否存在。

## 开关

```bash
hermes plugins enable recycle-bin      # 开启
hermes plugins disable recycle-bin     # 关闭（恢复永久删除）
```

**下一会话生效** —— 长命网关会沿用当前环境直到那时。

## 卸载

```bash
hermes plugins disable recycle-bin     # 停用
hermes plugins remove recycle-bin      # 删除文件
```

## 环境要求

| 要求 | 说明 |
|---|---|
| Windows 10/11 | 回收站 API 仅 Windows 提供 |
| 支持 `hermes plugins` 的 Hermes Agent | 需要原生插件系统 |
| Git for Windows（git-bash） | Hermes 本就以它作为终端 shell |
| Hermes venv 的 Python | 自动探测；找不到时回退到 PATH 里的 python |

## 排错

**`hermes plugins doctor` 能看到插件，但 `enable` 说名字未知**
目录名必须是 `recycle-bin`，且 `plugin.yaml` 直接位于其中。

**`/recycle-bin verify` 提示 "shim missing"**
`bin/rm` 没被复制过去（有些解压工具会跳过无扩展名文件），或丢了可执行位。
重新复制 `bin\rm`；在 git-bash 里执行 `chmod +x <...>/bin/rm`。

**删除仍然绕过回收站**
在会话里用 agent 执行 `which rm` 看解析到哪个。应当打印插件的 `bin/rm` 路径；
若打印 `/usr/bin/rm`，说明插件未启用，或该会话早于启用时刻。

**文件确实进了回收站，但我想立刻彻底删除**
停用插件，或直接清空回收站 —— 本插件从不主动清空回收站。

## 说明

- 插件只改动 Agent `terminal` 工具调用内部的 PATH，你自己的 shell 和其它程序不受影响。
- 删除物保留在回收站中（占用原盘空间），直到你清空回收站。
