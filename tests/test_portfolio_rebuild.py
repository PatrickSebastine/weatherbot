import json
from pathlib import Path

from weatherbot.ledger import ImmutableLedger, LedgerEntry
from weatherbot.portfolio import (
    PortfolioState,
    rebuild_portfolio_from_ledger,
    record_unresolved_position_snapshot,
    resolve_markets_to_pnl,
)


def append(path: Path, event_type: str, payload: dict, *, ts="2026-06-02T00:00:00+00:00", decision_id="d1"):
    record = {
        "timestamp": ts,
        "run_id": "run-1",
        "decision_id": decision_id,
        "event_type": event_type,
        "config_hash": "cfg",
        "payload": payload,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def read(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_rebuild_portfolio_from_ledger_restores_cash_positions_exposure_and_daily_pnl(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append(ledger, "paper_fill", {"market_id": "m1", "market_slug": "nyc-70-74", "city": "Nyc", "event_date": "2026-06-01", "outcome": "YES", "side": "buy", "shares": 2.0, "dollars": 1.0, "fill_price": 0.5})
    append(ledger, "paper_fill", {"market_id": "m2", "market_slug": "chi-70-78", "city": "Chicago", "event_date": "2026-06-01", "outcome": "YES", "side": "buy", "shares": 4.0, "dollars": 2.0, "fill_price": 0.5})
    append(ledger, "position_closed", {"market_id": "m1", "outcome": "YES", "shares": 2.0, "cost_basis": 1.0, "proceeds": 2.0, "realized_pnl": 1.0}, ts="2026-06-02T01:00:00+00:00")

    state = rebuild_portfolio_from_ledger(ledger, starting_cash=10.0, today="2026-06-02")

    assert isinstance(state, PortfolioState)
    assert state.cash == 9.0
    assert state.realized_daily_pnl == 1.0
    assert state.open_position_count == 1
    assert state.positions[("m2", "YES")].shares == 4.0
    assert state.exposure_book.city_exposure("Chicago") == 2.0
    assert state.duplicate_exposure_keys == []


def test_record_unresolved_snapshot_writes_current_open_positions_to_ledger(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    append(ledger_path, "paper_fill", {"market_id": "m1", "market_slug": "nyc-70-74", "city": "Nyc", "event_date": "2026-06-01", "outcome": "YES", "side": "buy", "shares": 2.0, "dollars": 1.0, "fill_price": 0.5})
    state = rebuild_portfolio_from_ledger(ledger_path, starting_cash=10.0, today="2026-06-02")

    record_unresolved_position_snapshot(ImmutableLedger(ledger_path), state, run_id="run-2", config_hash="cfg")

    entries = read(ledger_path)
    assert entries[-1]["event_type"] == "unresolved_position_snapshot"
    assert entries[-1]["payload"]["open_position_count"] == 1
    assert entries[-1]["payload"]["positions"][0]["market_id"] == "m1"


def test_resolve_markets_to_pnl_writes_resolution_close_realized_and_daily_events(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    append(ledger_path, "paper_fill", {"market_id": "m1", "market_slug": "nyc-70-74", "city": "Nyc", "event_date": "2026-06-01", "outcome": "YES", "side": "buy", "shares": 2.0, "dollars": 1.0, "fill_price": 0.5})
    state = rebuild_portfolio_from_ledger(ledger_path, starting_cash=10.0, today="2026-06-02")

    realized = resolve_markets_to_pnl(
        ledger=ImmutableLedger(ledger_path),
        state=state,
        resolved_outcomes={"m1": "YES"},
        run_id="resolve-1",
        config_hash="cfg",
    )

    assert realized == 1.0
    entries = read(ledger_path)
    assert [entry["event_type"] for entry in entries[-4:]] == ["market_resolved", "position_closed", "realized_pnl", "daily_pnl"]
    assert entries[-3]["payload"]["realized_pnl"] == 1.0
    assert entries[-1]["payload"]["realized_pnl"] == 1.0
