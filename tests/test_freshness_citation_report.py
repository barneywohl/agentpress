import argparse
import importlib.util
import json
import pathlib

_SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location("agentpress", _SCRIPTS / "agentpress.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

freshness_citation_report = _MOD.freshness_citation_report


def _args(root, out, **kw):
    defaults = dict(
        root=str(root),
        out=str(out),
        base_url="https://example.com/agentpress/",
        include_files=False,
        min_citation_ratio=0.0,
        min_canonical_json_ratio=0.0,
        max_unknown_machine=None,
        strict=True,
        no_write=False,
        json=True,
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def test_freshness_citation_report_passes_with_thresholds(tmp_path, capsys):
    (tmp_path / "agentpress").mkdir()
    (tmp_path / "llms.txt").write_text("source-map freshness citation\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("canonical source citation\n", encoding="utf-8")
    (tmp_path / "agentpress" / "surface.json").write_text(json.dumps({
        "canonical_url": "https://example.com/agentpress/agentpress/surface.json",
        "generated_utc": "2026-05-05T00:00:00Z",
        "source": "fixture",
    }), encoding="utf-8")
    out = tmp_path / "report.json"

    rc = freshness_citation_report(_args(tmp_path, out, min_citation_ratio=0.5, min_canonical_json_ratio=1.0, max_unknown_machine=0))
    data = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert data["status"] == "ok"
    assert data["findings"] == []
    assert json.loads(out.read_text())["coverage"]["canonical_json_ratio"] == 1.0


def test_freshness_citation_report_strict_fails_when_thresholds_missed(tmp_path, capsys):
    (tmp_path / "agentpress").mkdir()
    (tmp_path / "llms.txt").write_text("plain text\n", encoding="utf-8")
    (tmp_path / "agentpress" / "surface.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")
    out = tmp_path / "report.json"

    rc = freshness_citation_report(_args(tmp_path, out, min_citation_ratio=0.9, min_canonical_json_ratio=1.0, max_unknown_machine=0))
    data = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert data["status"] == "fail"
    assert {f["code"] for f in data["findings"]} >= {
        "citation_ratio_below_threshold",
        "canonical_json_ratio_below_threshold",
        "unknown_machine_count_above_threshold",
    }
