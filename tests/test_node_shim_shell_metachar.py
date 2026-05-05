import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "agentpress.js"


def make_fake_python(tmp_path: Path) -> Path:
    fake = tmp_path / "fake-python3"
    fake.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

if sys.argv[1:] == ['--version']:
    print('Python 3.11.9')
    raise SystemExit(0)

Path(os.environ['AGENTPRESS_ARG_LOG']).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    return fake


def test_node_shim_passes_shell_metacharacters_as_plain_argv(tmp_path):
    fake_python = make_fake_python(tmp_path)
    arg_log = tmp_path / "argv.json"
    injected_file = tmp_path / "should_not_exist"
    metachar_arg = f"docs;touch {injected_file}"

    env = {**os.environ, "PYTHON": str(fake_python), "AGENTPRESS_ARG_LOG": str(arg_log)}
    result = subprocess.run(
        ["node", str(BIN), "verify", metachar_arg, "--json"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert not injected_file.exists()
    forwarded = json.loads(arg_log.read_text(encoding="utf-8"))
    assert forwarded[0].endswith("scripts/agentpress.py")
    assert forwarded[1:] == ["verify", metachar_arg, "--json"]
