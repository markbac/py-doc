"""A stand-in for the vale program: prints canned JSON, so the tests run without Vale installed."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

SCRIPT = '''#!{python}
import json, sys
from pathlib import Path
args = sys.argv[1:]
log = Path({log!r})
with log.open("a") as handle:
    handle.write(json.dumps(args) + "\\n")
if "--version" in args:
    print("vale version {version}")
    raise SystemExit(0)
if "sync" in args:
    print("synced")
    raise SystemExit({sync_code})
if {crash!r}:
    print({crash!r}, file=sys.stderr)
    raise SystemExit(2)
files = [a for a in args if not a.startswith("-")]
canned = json.loads(Path({canned!r}).read_text()) if Path({canned!r}).exists() else {{}}
print(json.dumps({{f: canned.get(Path(f).name, []) for f in files}}))
'''


def install(folder: Path, monkeypatch, *, canned: dict | None = None, version="3.9.1", crash="", sync_code=0) -> Path:
    """Put a fake ``vale`` first on the PATH. ``canned`` maps a file name to the alerts to print for it."""
    import json

    folder.mkdir(parents=True, exist_ok=True)
    data = folder / "canned.json"
    data.write_text(json.dumps(canned or {}))
    log = folder / "calls.log"
    script = folder / ("vale.bat" if sys.platform == "win32" else "vale")
    body = SCRIPT.format(python=sys.executable, log=str(log), canned=str(data), version=version, crash=crash, sync_code=sync_code)
    if sys.platform == "win32":
        (folder / "vale.py").write_text(body.split("\n", 1)[1])
        script.write_text(f'@"{sys.executable}" "%~dp0vale.py" %*\n')
    else:
        script.write_text(body)
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{folder}{__import__('os').pathsep}{__import__('os').environ['PATH']}")
    return log


def alert(check="PyDoc.WeaselWords", line=1, message="'very' is a weasel word.", severity="suggestion", span=(3, 6), action=None):
    return {"Check": check, "Line": line, "Message": message, "Severity": severity, "Span": list(span), "Action": action or {"Name": "", "Params": None}}
