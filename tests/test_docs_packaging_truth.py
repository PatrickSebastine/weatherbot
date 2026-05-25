from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_requirements_declares_runtime_and_test_dependencies():
    req = ROOT / "requirements.txt"
    assert req.exists()
    content = req.read_text(encoding="utf-8")
    assert "requests" in content
    assert "pytest" in content


def test_readme_clearly_labels_demo_status_and_real_data_gate():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "demo runner uptime and ledger smoke test" in readme
    assert "scripts/run_paper.sh" in readme
    assert "live mode is not wired" in readme
    assert "bot_v1.py" in readme and "legacy" in readme
    assert "bot_v2.py" in readme and "legacy" in readme
    assert "config.json" in readme and "legacy" in readme
