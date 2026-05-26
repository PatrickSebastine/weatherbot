import json
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_paper_trading_scripts_exist_are_executable_and_compile():
    for relative in ("scripts/paper_trade.py", "scripts/paper_performance.py"):
        script = ROOT / relative
        assert script.exists()
        assert script.stat().st_mode & stat.S_IXUSR
        subprocess.run(["python", "-m", "py_compile", str(script)], check=True)


def test_paper_trade_demo_writes_secret_safe_ledger_and_prints_scan_summary(tmp_path):
    ledger = tmp_path / "paper.jsonl"

    result = subprocess.run(
        [
            "python",
            "scripts/paper_trade.py",
            "--demo",
            "--ledger",
            str(ledger),
            "--bankroll",
            "10",
            "--no-telegram",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Weatherbot Paper Trading Run" in result.stdout
    assert "Scanned: 3" in result.stdout
    assert "Filled: 3" in result.stdout
    assert ledger.exists()
    entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert [entry["event_type"] for entry in entries] == ["decision", "paper_fill"] * 3 + ["unresolved_position_snapshot"]
    assert entries[-1]["payload"]["open_position_count"] == 3
    decision_cities = [entry["payload"]["city"] for entry in entries if entry["event_type"] == "decision"]
    assert set(decision_cities) == {"Nyc", "Chicago", "Miami"}
    assert all("token" not in json.dumps(entry).lower() for entry in entries)


def test_paper_watchdog_alerts_when_ledger_is_stale_and_runner_missing(tmp_path):
    ledger = tmp_path / "paper.jsonl"
    ledger.write_text("{}\n", encoding="utf-8")

    result = subprocess.run(
        [
            "bash",
            "scripts/paper_watchdog.sh",
            "--ledger",
            str(ledger),
            "--max-age-minutes",
            "0",
            "--process-pattern",
            "definitely-not-running-weatherbot-test-process",
            "--strict-exit",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "Weatherbot paper runner watchdog alert" in result.stdout
    assert "ledger stale" in result.stdout
    assert "runner process missing" in result.stdout


def test_paper_watchdog_script_exists_is_executable_and_compiles():
    script = ROOT / "scripts" / "paper_watchdog.sh"
    assert script.exists()
    assert script.stat().st_mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(script)], check=True)


def test_paper_performance_cli_measures_fill_rates_edges_positions_and_pnl(tmp_path):
    ledger = tmp_path / "paper.jsonl"
    entries = [
        {
            "event_type": "decision",
            "payload": {"risk_approved": True, "edge": 0.20, "dollars": 1.0},
        },
        {
            "event_type": "decision",
            "payload": {"risk_approved": False, "edge": 0.05, "dollars": 0.0},
        },
        {
            "event_type": "paper_fill",
            "payload": {
                "market_id": "m1",
                "outcome": "YES",
                "side": "buy",
                "shares": 2.0,
                "dollars": 1.0,
            },
        },
        {"event_type": "daily_pnl", "payload": {"realized_pnl": 0.25}},
    ]
    ledger.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")

    result = subprocess.run(
        ["python", "scripts/paper_performance.py", "--ledger", str(ledger)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Weatherbot Paper Performance" in result.stdout
    assert "Decisions: 2" in result.stdout
    assert "Approval rate: 50.00%" in result.stdout
    assert "Fill rate: 100.00%" in result.stdout
    assert "Average edge: 12.50%" in result.stdout
    assert "Open positions: 1" in result.stdout
    assert "Realized PnL: $0.25" in result.stdout


def test_paper_trading_runbook_documents_safe_setup_and_measurement_commands():
    content = (ROOT / "docs" / "paper-trading.md").read_text(encoding="utf-8")

    assert "paper" in content.lower()
    assert "scripts/paper_trade.py --demo" in content
    assert "scripts/paper_performance.py" in content
    assert "execution.enable_live" in content
    assert "false" in content.lower()
    assert "data/paper_trades.jsonl" in content
    assert "logs/run_paper.log" in content
    assert "paper_watchdog.sh" in content
