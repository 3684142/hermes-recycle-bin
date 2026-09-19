"""recycle-bin plugin — Hermes `rm` deletions become Windows Recycle Bin moves.

How it works: a `pre_tool_call` hook prepends a PATH export to every `terminal`
command, putting this plugin's ``bin/`` dir ahead of ``/usr/bin``. The ``rm``
shim found there hands the paths to ``trash.py`` (shell32 ``SHFileOperationW``
with ``FOF_ALLOWUNDO``), which moves them to the Recycle Bin instead of
unlinking them.

Toggle: ``hermes plugins enable recycle-bin`` / ``disable`` (next session).
Slash:  ``/recycle-bin status|open|verify``.

Boundaries (by design, not bugs): ``/usr/bin/rm``, ``command rm``, python
``os.remove``, ``find -delete``, and cron job scripts never resolve through
PATH here, so they still delete permanently. Non-Windows hosts are refused at
register() time.
"""

from __future__ import annotations

import logging
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).resolve().parent
_BIN_DIR = _PLUGIN_DIR / "bin"
_SHIM = _BIN_DIR / "rm"


def _to_posix(p: Path) -> str:
    """``C:\\x`` -> ``/c/x`` (git-bash spelling); other shapes pass through."""
    s = p.as_posix()
    if len(s) > 1 and s[1] == ":":
        return "/" + s[0].lower() + s[2:]
    return s


def _find_bash() -> Optional[str]:
    """A bash that can run the shim, or None."""
    candidates = [
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files (x86)/Git/bin/bash.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    import shutil as _shutil
    return _shutil.which("bash")


def _shim_posix() -> Optional[str]:
    """The `rm` shim as a git-bash POSIX path, or None when missing."""
    if not _SHIM.is_file():
        return None
    return _to_posix(_SHIM)


def _bin_posix() -> Optional[str]:
    """``bin/`` as a git-bash POSIX path (``C:\\x`` -> ``/c/x``), or None when unusable."""
    if not _SHIM.is_file():
        return None
    return _to_posix(_BIN_DIR)


def _pre_tool_call(tool_name: str = "", args: Optional[Dict[str, Any]] = None, **_: Any) -> Optional[Dict[str, Any]]:
    """Prepend the shim to PATH for `terminal` commands. Returns None to leave the call untouched."""
    if tool_name != "terminal" or not isinstance(args, dict):
        return None
    cmd = args.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return None
    bin_posix = _bin_posix()
    if bin_posix is None:
        logger.warning("recycle-bin: shim missing at %s; leaving command untouched", _SHIM)
        return None
    if bin_posix in cmd:  # already injected (or the model wrote it) — never double up
        return None
    escaped = bin_posix.replace("\\", "\\\\").replace('"', '\\"')
    return {"action": "modify", "args": {"command": f'export PATH="{escaped}:$PATH"\n{cmd}'}}


def _run_ps(script_lines: str) -> str:
    """Run a PowerShell snippet; return stdout (+stderr tail) as text."""
    pwsh = "powershell"
    try:
        proc = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", script_lines],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return out if out else (err[-400:] or "(no output)")
    except Exception as exc:  # never raise into the slash command
        return f"recycle-bin: PowerShell failed: {exc}"


def _cmd_status() -> str:
    bin_posix = _bin_posix()
    lines = [
        "[recycle-bin] Hermes deletions go to the Windows Recycle Bin.",
        f"  shim      : {_SHIM}  ({'present' if _SHIM.is_file() else 'MISSING'})",
        f"  backend   : {_PLUGIN_DIR / 'trash.py'}",
        f"  injected  : export PATH=\"{bin_posix}:$PATH\"",
        f"  scope     : terminal commands in CLI + gateway sessions",
        "",
        "  Bypassed (still permanent): /usr/bin/rm · command rm · os.remove · find -delete · cron scripts",
        "  Toggle: hermes plugins disable recycle-bin   (takes effect next session)",
    ]
    return "\n".join(lines)


def _cmd_open() -> str:
    try:
        subprocess.Popen(["explorer.exe", "shell:RecycleBinFolder"])
        return "[recycle-bin] Opened the Windows Recycle Bin."
    except Exception as exc:
        return f"[recycle-bin] Could not open the Recycle Bin: {exc}"


def _cmd_verify(argv) -> str:
    """Delete a throwaway file through the shim and confirm it landed in the Recycle Bin."""
    import tempfile

    name = "hermes-recycle-bin-verify.txt"
    target = Path(tempfile.gettempdir()) / name
    try:
        target.write_text("recycle-bin verification probe\n", encoding="utf-8")
    except OSError as exc:
        return f"[recycle-bin] Cannot create probe: {exc}"
    # git-bash script + native-file argument: use POSIX spellings for BOTH, so bash can
    # open the script and the shim can resolve the target without path-conversion surprises.
    shim_posix = _shim_posix()
    if shim_posix is None:
        return f"[recycle-bin] FAILED — shim missing at {_SHIM}"
    probe_posix = _to_posix(target)
    bash = _find_bash()
    if bash is None:
        return "[recycle-bin] FAILED — bash not found (needed to run the shim)."
    try:
        proc = subprocess.run([bash, shim_posix, probe_posix],
                              capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[recycle-bin] Shim run failed: {exc}"
    if target.exists():
        return (f"[recycle-bin] FAILED — probe still on disk.\n"
                f"  shim exit={proc.returncode} err={(proc.stderr or '').strip()[:300]}")
    stem = name.replace(".txt", "")
    found = _run_ps(
        "$sh=New-Object -ComObject Shell.Application; $b=$sh.Namespace(10); "
        f"$m=@(); foreach($i in $b.Items()){{ if($i.Name -like '*{stem}*'){{ $m+= $i.Name }} }}; "
        "if($m.Count -eq 0){'NOT-IN-BIN'} else {'IN-BIN: ' + ($m -join ', ')}")
    return f"[recycle-bin] probe deleted (shim exit={proc.returncode}); Recycle Bin check -> {found}"


_COMMANDS = {
    "status": lambda argv: _cmd_status(),
    "open": lambda argv: _cmd_open(),
    "verify": lambda argv: _cmd_verify(argv),
}

_HELP = """\
/recycle-bin — route Hermes `rm` deletions into the Windows Recycle Bin

Subcommands:
  status    Show shim path, injection line, and bypass boundaries (default)
  verify    Delete a throwaway file through the shim, confirm it is in the Recycle Bin
  open      Open the Windows Recycle Bin

Disable entirely with: hermes plugins disable recycle-bin
"""


def _handle(raw_args: str) -> str:
    argv = (raw_args or "").strip().split()
    sub = (argv[0].lower() if argv else "status")
    if sub in {"help", "-h", "--help"}:
        return _HELP
    handler = _COMMANDS.get(sub)
    if handler is None:
        return f"Unknown subcommand: {sub}\n\n{_HELP}"
    return handler(argv)


def register(ctx) -> None:
    if platform.system().lower() != "windows":
        logger.info("recycle-bin plugin: Windows only; not registering on %s", platform.system())
        return
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_command("recycle-bin", handler=_handle,
                         description="Route rm deletions to the Windows Recycle Bin (status/verify/open).")
