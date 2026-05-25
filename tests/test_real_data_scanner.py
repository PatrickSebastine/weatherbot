import json

from weatherbot.data.live import (
    fetch_clob_books,
    fetch_open_meteo_forecasts_for_markets,
    fetch_weather_gamma_events,
)
from weatherbot.data.polymarket import parse_gamma_event_markets


def test_fetch_weather_gamma_events_filters_active_temperature_markets_without_secrets():
    calls = []

    def fake_get(url):
        calls.append(url)
        return [
            {
                "id": "e1",
                "slug": "highest-temperature-in-nyc-on-june-1-2026",
                "title": "Highest temperature in New York City on June 1, 2026?",
                "markets": [
                    {
                        "id": "m1",
                        "slug": "nyc-70-74",
                        "question": "Will the highest temperature in New York City be between 70-74°F on June 1?",
                        "outcomes": '["Yes", "No"]',
                        "outcomePrices": '["0.44", "0.56"]',
                        "clobTokenIds": '["yes-token", "no-token"]',
                        "conditionId": "0xabc",
                        "liquidity": "250",
                        "volume": "500",
                        "active": True,
                        "closed": False,
                    }
                ],
            },
            {"id": "e2", "slug": "election-market", "title": "Election winner", "markets": []},
        ]

    events = fetch_weather_gamma_events(http_get=fake_get, limit=50)

    assert len(events) == 1
    assert events[0]["id"] == "e1"
    assert calls
    assert "gamma-api.polymarket.com" in calls[0]
    assert "active=true" in calls[0]
    assert "closed=false" in calls[0]


def test_fetch_clob_books_fetches_each_yes_token_and_keys_by_token_id():
    urls = []

    def fake_get(url):
        urls.append(url)
        return {"bids": [{"price": "0.43", "size": "100"}], "asks": [{"price": "0.44", "size": "80"}]}

    books = fetch_clob_books(["yes-token-1", "yes-token-2"], http_get=fake_get)

    assert sorted(books) == ["yes-token-1", "yes-token-2"]
    assert all("clob.polymarket.com/book" in url for url in urls)
    assert "token_id=yes-token-1" in urls[0]


def test_fetch_open_meteo_forecasts_matches_market_city_and_event_date():
    event = {
        "id": "e1",
        "slug": "highest-temperature-in-nyc-on-june-1-2026",
        "title": "Highest temperature in New York City on June 1, 2026?",
        "markets": [
            {
                "id": "m1",
                "slug": "nyc-70-74",
                "question": "Will the highest temperature in New York City be between 70-74°F on June 1?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.44", "0.56"]',
                "clobTokenIds": '["yes-token", "no-token"]',
                "conditionId": "0xabc",
                "liquidity": "250",
                "volume": "500",
                "active": True,
                "closed": False,
            }
        ],
    }
    markets = parse_gamma_event_markets(event)

    def fake_get(url):
        assert "api.open-meteo.com" in url
        assert "temperature_2m_max" in url
        return {"daily": {"time": ["2026-06-01", "2026-06-02"], "temperature_2m_max": [72.0, 75.0]}}

    forecasts = fetch_open_meteo_forecasts_for_markets(markets, http_get=fake_get, fetched_at="2026-05-31T12:00:00+00:00")

    assert len(forecasts) == 1
    assert forecasts[0].city_slug == "nyc"
    assert forecasts[0].forecast_date == "2026-06-01"
    assert forecasts[0].high_temperature == 72.0
    assert forecasts[0].metadata["provider"] == "open-meteo"
