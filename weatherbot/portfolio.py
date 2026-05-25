"""Portfolio reconstruction and paper PnL event helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from weatherbot.ledger import ImmutableLedger, LedgerEntry
from weatherbot.risk.exposure import ExposureBook, PositionExposure


@dataclass
class PortfolioPosition:
    market_id: str
    market_slug: str
    city: str
    event_date: str
    outcome: str
    shares: float
    cost_basis: float

    @property
    def average_cost(self) -> float:
        return self.cost_basis / self.shares if self.shares else 0.0


@dataclass
class PortfolioState:
    starting_cash: float
    cash: float
    positions: dict[tuple[str, str], PortfolioPosition]
    realized_total_pnl: float
    realized_daily_pnl: float
    duplicate_exposure_keys: list[tuple[str, str]]

    @property
    def open_position_count(self) -> int:
        return sum(1 for position in self.positions.values() if position.shares > 0 and position.cost_basis > 0)

    @property
    def exposure_book(self) -> ExposureBook:
        return ExposureBook(
            PositionExposure(
                market_id=position.market_id,
                city=position.city,
                event_date=position.event_date,
                outcome=position.outcome,
                dollars=position.cost_basis,
            )
            for position in self.positions.values()
            if position.shares > 0 and position.cost_basis > 0
        )


def rebuild_portfolio_from_ledger(path: str | Path, *, starting_cash: float, today: str | None = None) -> PortfolioState:
    """Rebuild paper cash, open positions, exposure, and PnL from ledger events."""

    entries = ImmutableLedger(path).read_entries()
    positions: dict[tuple[str, str], PortfolioPosition] = {}
    cash = float(starting_cash)
    realized_total = 0.0
    realized_daily = 0.0

    for entry in entries:
        payload = entry.get("payload") or {}
        event_type = entry.get("event_type")
        if event_type == "paper_fill":
            side = str(payload.get("side", "buy")).lower()
            market_id = str(payload.get("market_id", ""))
            outcome = str(payload.get("outcome", ""))
            key = (market_id, outcome)
            shares = float(payload.get("shares") or 0.0)
            dollars = float(payload.get("dollars") or 0.0)
            if side == "buy":
                cash -= dollars
                existing = positions.get(key)
                if existing is None:
                    positions[key] = PortfolioPosition(
                        market_id=market_id,
                        market_slug=str(payload.get("market_slug", "")),
                        city=str(payload.get("city", "")),
                        event_date=str(payload.get("event_date", "")),
                        outcome=outcome,
                        shares=shares,
                        cost_basis=dollars,
                    )
                else:
                    existing.shares += shares
                    existing.cost_basis += dollars
            elif side == "sell":
                cash += dollars
                _reduce_position(positions, key, shares, proceeds=dollars)
        elif event_type == "position_closed":
            market_id = str(payload.get("market_id", ""))
            outcome = str(payload.get("outcome", ""))
            proceeds = float(payload.get("proceeds") or 0.0)
            shares = float(payload.get("shares") or 0.0)
            pnl = float(payload.get("realized_pnl") or 0.0)
            cash += proceeds
            realized_total += pnl
            if today is None or str(entry.get("timestamp", ""))[:10] == today:
                realized_daily += pnl
            _reduce_position(positions, (market_id, outcome), shares, proceeds=proceeds)
        elif event_type == "realized_pnl":
            # `position_closed` is authoritative for cash/position accounting.
            continue
        elif event_type == "daily_pnl":
            continue

    positions = {key: pos for key, pos in positions.items() if pos.shares > 1e-12 and pos.cost_basis > 1e-12}
    return PortfolioState(
        starting_cash=float(starting_cash),
        cash=round(cash, 10),
        positions=positions,
        realized_total_pnl=round(realized_total, 10),
        realized_daily_pnl=round(realized_daily, 10),
        duplicate_exposure_keys=_duplicate_city_date_keys(positions),
    )


def record_unresolved_position_snapshot(
    ledger: ImmutableLedger,
    state: PortfolioState,
    *,
    run_id: str,
    config_hash: str,
) -> None:
    """Append an auditable snapshot of unresolved paper positions."""

    ledger.append(
        LedgerEntry(
            run_id=run_id,
            decision_id=f"{run_id}:unresolved-position-snapshot",
            event_type="unresolved_position_snapshot",
            config_hash=config_hash,
            payload={
                "cash": state.cash,
                "open_position_count": state.open_position_count,
                "realized_total_pnl": state.realized_total_pnl,
                "realized_daily_pnl": state.realized_daily_pnl,
                "duplicate_exposure_keys": [list(key) for key in state.duplicate_exposure_keys],
                "positions": [_position_payload(position) for position in state.positions.values()],
            },
        )
    )


def resolve_markets_to_pnl(
    *,
    ledger: ImmutableLedger,
    state: PortfolioState,
    resolved_outcomes: dict[str, str],
    run_id: str,
    config_hash: str,
) -> float:
    """Append resolution and PnL events for markets with known winning outcomes."""

    total_realized = 0.0
    for (market_id, outcome), position in list(state.positions.items()):
        if market_id not in resolved_outcomes:
            continue
        winning_outcome = resolved_outcomes[market_id]
        proceeds = position.shares if outcome == winning_outcome else 0.0
        realized = proceeds - position.cost_basis
        total_realized += realized
        resolution_payload: dict[str, Any] = {
            "market_id": market_id,
            "market_slug": position.market_slug,
            "winning_outcome": winning_outcome,
        }
        ledger.append(LedgerEntry(run_id, f"{run_id}:{market_id}:resolved", "market_resolved", config_hash, resolution_payload))
        ledger.append(
            LedgerEntry(
                run_id,
                f"{run_id}:{market_id}:{outcome}:closed",
                "position_closed",
                config_hash,
                {
                    "market_id": market_id,
                    "market_slug": position.market_slug,
                    "city": position.city,
                    "event_date": position.event_date,
                    "outcome": outcome,
                    "shares": position.shares,
                    "cost_basis": position.cost_basis,
                    "proceeds": proceeds,
                    "realized_pnl": realized,
                },
            )
        )
        ledger.append(
            LedgerEntry(
                run_id,
                f"{run_id}:{market_id}:{outcome}:realized-pnl",
                "realized_pnl",
                config_hash,
                {"market_id": market_id, "outcome": outcome, "realized_pnl": realized},
            )
        )
    ledger.append(
        LedgerEntry(
            run_id,
            f"{run_id}:daily-pnl",
            "daily_pnl",
            config_hash,
            {"realized_pnl": total_realized},
        )
    )
    return round(total_realized, 10)


def _reduce_position(
    positions: dict[tuple[str, str], PortfolioPosition],
    key: tuple[str, str],
    shares: float,
    *,
    proceeds: float,
) -> None:
    position = positions.get(key)
    if position is None or shares <= 0:
        return
    closed_cost = min(position.cost_basis, position.average_cost * shares)
    position.shares = max(0.0, position.shares - shares)
    position.cost_basis = max(0.0, position.cost_basis - closed_cost)
    if position.shares <= 1e-12 or position.cost_basis <= 1e-12:
        positions.pop(key, None)


def _duplicate_city_date_keys(positions: dict[tuple[str, str], PortfolioPosition]) -> list[tuple[str, str]]:
    counts: dict[tuple[str, str], int] = {}
    for position in positions.values():
        key = (position.city, position.event_date)
        counts[key] = counts.get(key, 0) + 1
    return sorted(key for key, count in counts.items() if count > 1)


def _position_payload(position: PortfolioPosition) -> dict[str, Any]:
    return {
        "market_id": position.market_id,
        "market_slug": position.market_slug,
        "city": position.city,
        "event_date": position.event_date,
        "outcome": position.outcome,
        "shares": position.shares,
        "cost_basis": position.cost_basis,
        "average_cost": position.average_cost,
    }
