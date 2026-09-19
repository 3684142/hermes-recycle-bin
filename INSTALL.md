# Install — hermes-recycle-bin

Three steps. No build, no dependencies, no API keys.

## 1. Find your Hermes home

It is `%LOCALAPPDATA%\hermes` by default (PowerShell):

```powershell
echo $env:LOCALAPPDATA\hermes
```

If you set a custom `HERMES_HOME`, use that path instead.

## 2. Copy the plugin folder

Copy the **`recycle-bin`** directory from the release zip into:

```
<HERMES_HOME>\plugins\recycle-bin\
```

The result must look exactly like this (`plugin.yaml` directly inside `recycle-bin`):

```
<HERMES_HOME>\plugins\recycle-bin\plugin.yaml
<HERMES_HOME>\plugins\recycle-bin\__init__.py
<HERMES_HOME>\plugins\recycle-bin\trash.py
<HERMES_HOME>\plugins\recycle-bin\list-bin.ps1
<HERMES_HOME>\plugins\recycle-bin\bin\rm
```

> Do not rename the folder — the plugin registers under the name `recycle-bin`.

## 3. Enable it

```bash
hermes plugins enable recycle-bin
```

Expected output:

```
✓ Plugin recycle-bin enabled. Takes effect on next session.
```

Run the health check to confirm the manifest and hook registered:

```bash
hermes plugins doctor recycle-bin
```

Expected:

```
  manifest: recycle-bin 1.0.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 0 tool(s), 1 hook(s)
```

## Verify it actually works

Start a **new** session (plugins load at session start), then in that session:

```
/recycle-bin verify
```

Expected:

```
[recycle-bin] probe deleted (shim exit=0); Recycle Bin check -> IN-BIN: hermes-recycle-bin-verify.txt
```

If you see `FAILED` instead, run `/recycle-bin status` and check that the shim path it
prints exists on disk.

## Toggling

```bash
hermes plugins enable recycle-bin      # on
hermes plugins disable recycle-bin     # off (back to permanent deletes)
```

Takes effect on the **next session** — a long-running gateway keeps its current
environment until then.

## Uninstall

```bash
hermes plugins disable recycle-bin     # stop using it
hermes plugins remove recycle-bin      # remove the files
```

## Requirements

| Requirement | Notes |
|---|---|
| Windows 10/11 | Recycle Bin API is Windows-only |
| Hermes Agent with `hermes plugins` | Native plugin system |
| Git for Windows (git-bash) | Hermes already uses it as its terminal shell |
| Hermes venv Python | Auto-detected; falls back to any `python` on PATH |

## Troubleshooting

**`hermes plugins doctor` reports the plugin but `enable` says unknown name**
Folder name must be exactly `recycle-bin` and `plugin.yaml` must sit directly inside it.

**`/recycle-bin verify` says "shim missing"**
The `bin/rm` file was not copied (zip extraction sometimes skips extensionless files) or
lost its execute bit. Copy `bin\rm` again; on git-bash run `chmod +x <...>/bin/rm`.

**Deletions still bypass the bin**
Check which rm is being used inside a session: run `which rm` through the agent. It should
print the plugin's `bin/rm` path. If it prints `/usr/bin/rm`, the plugin is not enabled or
the session predates the enable.

**Files land in the bin but I want them gone immediately**
Disable the plugin, or empty the Recycle Bin — this plugin never empties it.

## Notes

- The plugin only changes PATH inside the agent's `terminal` tool calls. Your own shells
  and other programs are unaffected.
- Items stay in the Recycle Bin (using their original drive's space) until you empty it.
