"""Read-only live data fetchers for real-data paper scans.

These helpers only perform HTTP GET requests and return parsed data for the
paper engine. They do not sign, submit, cancel, or settle any live orders.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Callable, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from weatherbot.data.polymarket import ParsedPolymarketMarket, parse_gamma_event_markets
from weatherbot.data.stations import get_city_station
from weatherbot.data.weather import (
    ForecastSnapshot,
    build_open_meteo_daily_url,
    normalize_open_meteo_daily_highs,
)
from weatherbot.scan import city_slug_from_market_city

HttpGet = Callable[[str], Any]

GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"
CLOB_BOOK_URL = "https://clob.polymarket.com/book"


def default_http_get(url: str) -> Any:
    """Fetch JSON with a conservative user-agent and timeout."""

    request = Request(url, headers={"User-Agent": "weatherbot-paper-scanner/1.0"})
    with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed HTTPS endpoints, read-only GET
        return json.loads(response.read().decode("utf-8"))


def fetch_weather_gamma_events(*, http_get: HttpGet = default_http_get, limit: int = 100) -> list[dict[str, Any]]:
    """Fetch active Gamma events and keep only weather temperature candidates."""

    if limit <= 0:
        raise ValueError("limit must be positive")
    url = GAMMA_EVENTS_URL + "?" + urlencode({"active": "true", "closed": "false", "limit": limit})
    payload = http_get(url)
    events = _event_list(payload)
    return [event for event in events if _looks_like_weather_temperature_event(event)]


def fetch_clob_books(token_ids: Iterable[str], *, http_get: HttpGet = default_http_get) -> dict[str, dict[str, Any]]:
    """Fetch CLOB books keyed by YES token id.

    Tokens that return unusable payloads are skipped. The parser can still fall
    back to Gamma outcomePrices, but real paper scans should prefer CLOB books.
    """

    books: dict[str, dict[str, Any]] = {}
    for token_id in dict.fromkeys(str(token).strip() for token in token_ids if str(token).strip()):
        url = CLOB_BOOK_URL + "?" + urlencode({"token_id": token_id})
        book = http_get(url)
        if isinstance(book, dict):
            books[token_id] = book
    return books


def fetch_open_meteo_forecasts_for_markets(
    markets: Iterable[ParsedPolymarketMarket],
    *,
    http_get: HttpGet = default_http_get,
    fetched_at: str | None = None,
    forecast_days: int = 14,
) -> list[ForecastSnapshot]:
    """Fetch Open-Meteo forecasts for each market city and keep market dates."""

    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    needed_dates_by_city: dict[str, set[str]] = {}
    for market in markets:
        city_slug = city_slug_from_market_city(market.city)
        needed_dates_by_city.setdefault(city_slug, set()).add(market.event_date)

    snapshots: list[ForecastSnapshot] = []
    for city_slug, needed_dates in needed_dates_by_city.items():
        station = get_city_station(city_slug)
        url = build_open_meteo_daily_url(station, forecast_days=forecast_days)
        payload = http_get(url)
        normalized = normalize_open_meteo_daily_highs(
            payload,
            station=station,
            source="ecmwf",
            fetched_at=fetched_at,
        )
        snapshots.extend(snapshot for snapshot in normalized if snapshot.forecast_date in needed_dates)
    return snapshots


def fetch_real_paper_inputs(
    *,
    http_get: HttpGet = default_http_get,
    min_liquidity_usd: float = 0.0,
    gamma_limit: int = 100,
    fetched_at: str | None = None,
) -> tuple[list[ParsedPolymarketMarket], list[ForecastSnapshot]]:
    """Fetch real Gamma events, CLOB books, and Open-Meteo forecasts for paper scans."""

    events = fetch_weather_gamma_events(http_get=http_get, limit=gamma_limit)
    preliminary_markets: list[ParsedPolymarketMarket] = []
    for event in events:
        preliminary_markets.extend(parse_gamma_event_markets(event, min_liquidity_usd=min_liquidity_usd))

    books = fetch_clob_books((market.yes_token_id for market in preliminary_markets), http_get=http_get)
    parsed_markets: list[ParsedPolymarketMarket] = []
    for event in events:
        parsed_markets.extend(
            parse_gamma_event_markets(
                event,
                books_by_yes_token=books,
                min_liquidity_usd=min_liquidity_usd,
            )
        )
    forecasts = fetch_open_meteo_forecasts_for_markets(parsed_markets, http_get=http_get, fetched_at=fetched_at)
    return parsed_markets, forecasts


def _event_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [event for event in payload if isinstance(event, dict)]
    if isinstance(payload, dict):
        for key in ("events", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [event for event in value if isinstance(event, dict)]
    raise ValueError("Gamma response did not contain an event list")


def _looks_like_weather_temperature_event(event: dict[str, Any]) -> bool:
    text = " ".join(str(event.get(key, "")) for key in ("slug", "title", "description")).lower()
    if "temperature" not in text and "weather" not in text:
        return False
    if "highest" not in text and "high" not in text:
        return False
    return bool(event.get("markets"))
