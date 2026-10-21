"""End-to-end on the bundled synthetic fixture and the real demo patch file."""

import json
import shutil

from conftest import ROOT

from ruamel.yaml import YAML

from rightsized import vpa
from rightsized.cli import main
from rightsized.config import Policy
from rightsized.models import Snapshot

SNAP = ROOT / "examples" / "synthetic-snapshot.json"
VPA = ROOT / "examples" / "synthetic-vpa.json"
OFFLINE = ROOT / "examples" / "offline.yaml"


def test_analyze_writes_summary(tmp_path, capsys):
    out = tmp_path / "s.json"
    assert main(["-c", str(OFFLINE), "analyze", str(SNAP), "--json", str(out)]) == 0
    s = json.loads(out.read_text())
    assert "boutique/adservice/server" not in s["applied"]  # OOMing service is never auto-applied
    assert s["savings"]["nodes_after"] <= s["savings"]["nodes_before"]
    assert "don't touch" in capsys.readouterr().out


def test_pr_patches_demo_resources_file(tmp_path):
    repo = tmp_path / "repo"
    (repo / "deploy" / "boutique").mkdir(parents=True)
    shutil.copy(ROOT / "deploy" / "boutique" / "resources.guessed.yaml", repo / "deploy" / "boutique" / "resources.yaml")
    # Demo targets and node pool, but the real-cluster (default) policy the fixture was made for.
    raw = YAML(typ="safe").load((ROOT / "rightsized.yaml").read_text())
    raw.pop("policy")
    cfg = tmp_path / "cfg.yaml"
    YAML().dump(raw, cfg)
    body = tmp_path / "body.md"
    assert main(["-c", str(cfg), "pr", str(SNAP), "--repo", str(repo), "--body-out", str(body)]) == 0
    patched = (repo / "deploy" / "boutique" / "resources.yaml").read_text()
    assert "cpu: 165m" in patched  # frontend: safe, applied
    assert patched.count("memory: 256Mi") >= 2  # adservice: don't touch, request+limit left as guessed
    assert "deliberate under-sizings" in patched  # header comment survives
    text = body.read_text()
    assert "Applied in this PR" in text and "Not applied" in text and "Savings" in text


def test_compare_prints_both_arms(capsys):
    assert main(["-c", str(OFFLINE), "compare", str(SNAP), "--vpa", str(VPA)]) == 0
    out = capsys.readouterr().out
    assert "| rightsized |" in out and "| stock VPA |" in out


def test_vpa_targets_and_proportional_limits():
    snap = Snapshot.load(SNAP)
    recs = {r.key: r for r in vpa.recommendations(snap, json.loads(VPA.read_text()), Policy())}
    fe = recs["boutique/frontend/server"]
    assert fe.requests.cpu == 0.163
    assert fe.limits.cpu == 1.0 * 0.163 / 0.5  # scaled like VPA's RequestsAndLimits
    assert fe.source == "vpa"
