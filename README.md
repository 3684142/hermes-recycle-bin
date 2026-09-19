# hermes-recycle-bin

[English](README.md) | [简体中文](README.zh-CN.md)

A Hermes Agent plugin that sends the agent's `rm` deletions to the **Windows Recycle
Bin** instead of deleting them permanently. Toggle it with the standard plugin commands —
no config editing.

```bash
hermes plugins enable recycle-bin      # deletions become recycle-bin moves (next session)
hermes plugins disable recycle-bin     # back to permanent deletes (next session)
```

Built for people who let an autonomous agent run shell commands on their own machine and
want a safety net that survives the agent's mistakes.

> **Scope:** Windows only. The plugin refuses to register on macOS/Linux (no Recycle Bin
> equivalent is wired up). See [Boundaries](#boundaries) before relying on it.

## Why

Hermes' `terminal` tool runs the agent's commands through git-bash, where `rm` unlinks
files permanently. `rm -rf` on a directory the agent misidentified is unrecoverable.
Hermes has no built-in recycle-bin setting (its official recovery features are
`checkpoints`/`/rollback`, off by default, and the desktop file browser's trash button).
This plugin fills that gap by putting an `rm` shim ahead of `/usr/bin` *only for the
agent's own shell commands*.

## How it works

```
terminal tool call
      │
      ▼
pre_tool_call hook  ──►  prepends: export PATH="<plugin>/bin:$PATH"
      │
      ▼
bash runs the command
      │  `rm foo.txt` resolves to <plugin>/bin/rm  (not /usr/bin/rm)
      ▼
bin/rm (shim)  ──►  cygpath -w  ──►  trash.py
                                        │
                                        ▼
                        shell32 SHFileOperationW (FOF_ALLOWUNDO)
                                        │
                                        ▼
                                Windows Recycle Bin  ♻
```

| File | Role |
|---|---|
| `__init__.py` | `pre_tool_call` hook + `/recycle-bin` slash command |
| `bin/rm` | GNU-compatible `rm` shim (`-f`, `-r`, `-rf`, `--`, multi-path, `--version`) |
| `trash.py` | Recycle-Bin backend: `SHFileOperationW` with `FOF_ALLOWUNDO │ FOF_NOCONFIRMATION │ FOF_SILENT │ FOF_NOERRORUI` |
| `list-bin.ps1` | Helper: lists matching items in the Recycle Bin with their original folder |

Your own PowerShell, Git Bash, Explorer, and every other program on the machine are
untouched — the PATH change applies only to the agent's `terminal` calls.

## Install

See [INSTALL.md](INSTALL.md) — three steps, no build required.
中文安装说明：[INSTALL.zh-CN.md](INSTALL.zh-CN.md)

## Usage

```
/recycle-bin status    # shim path, injection line, bypass boundaries
/recycle-bin verify    # delete a throwaway file through the shim, confirm it is in the bin
/recycle-bin open      # open the Windows Recycle Bin
```

Sample `verify` output:

```
[recycle-bin] probe deleted (shim exit=0); Recycle Bin check -> IN-BIN: hermes-recycle-bin-verify.txt
```

## Boundaries

These paths do **not** go through the shim, by design — they still delete permanently:

| Bypass | Why |
|---|---|
| `/usr/bin/rm`, `command rm` | Absolute paths skip PATH lookup entirely |
| Python `os.remove` / `shutil.rmtree`, `find -delete` | Not shell `rm` calls |
| `mv`, file overwrites | Never went through `rm` |
| Cron job scripts (`hermes cron script=...`) | They run via `subprocess` with a sanitized env, not the terminal PATH |
| Other programs on the machine | The PATH change is scoped to the agent's terminal tool |

Behavioural differences from GNU `rm`:

- `rm -i` does not prompt (there is no TTY in a gateway session; the file is deleted).
- `rm -v` does not print `removed '…'`.

Both are cosmetic for agent use. Everything else (`-f`, `-r`, `-rf`, `--`, multiple
paths, missing-file handling, `--version`) matches GNU behaviour.

## Safety notes

- Items sit in the Recycle Bin occupying their original drive until emptied. Per-volume
  quota: `HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\BitBucket\Volume`
  (`MaxCapacity`, MB). Windows purges oldest items past the quota.
- `FOF_NOERRORUI` is what keeps a headless gateway from ever blocking on a dialog.
  Do not remove that flag.
- The hook only fires for `tool_name == "terminal"` and is idempotent — it will not
  double-inject if the path is already in the command.
- Verified not to interfere with Hermes' dangerous-command approval: prepending the
  `export PATH=…` line leaves `detect_dangerous_command()` results unchanged for
  `rm -rf /`, `sudo rm -rf /etc`, `dd if=/dev/zero of=/dev/sda`, fork bombs, etc.

## Compatibility

- Windows 10/11, Hermes Agent with the native plugin system (`hermes plugins`).
- Requires git-bash (ships with Git for Windows; Hermes already uses it as its shell) and
  the Hermes venv Python — both auto-detected, no hardcoded paths.
- Hermes plugin manifest v1 (`kind: standalone`), one `pre_tool_call` hook, one slash
  command. No tools, no dependencies, no network access.

## FAQ

**Does this affect my own terminal?**
No. The PATH prepend happens inside the agent's `terminal` tool calls only.

**What if I delete something huge?**
It goes to the Recycle Bin like anything else; Windows applies the per-volume quota and
purges the oldest entries when full.

**How do I get a file back?**
Open the Recycle Bin (`/recycle-bin open`), or use `list-bin.ps1` to find it and restore
from Explorer.

**Does it work with multiple Hermes profiles?**
Yes — the shim resolves its own location from the file it runs from, so a copy under any
`HERMES_HOME/plugins/recycle-bin/` works.

## Uninstall

```bash
hermes plugins disable recycle-bin     # stop using it (keeps files)
# or fully remove:
hermes plugins remove recycle-bin
```

## License

MIT — see [LICENSE](LICENSE).
