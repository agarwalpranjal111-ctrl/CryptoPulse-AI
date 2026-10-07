import logging
import os
import random
import time
from datetime import datetime

import requests


class CryptoService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache = {}              # key -> (data, timestamp)
        self.cache_duration = 300    # 5 minutes
        self.session = requests.Session()
        api_key = os.environ.get("COINGECKO_API_KEY")  # optional, avoids rate limits
        if api_key:
            self.session.headers["x-cg-demo-api-key"] = api_key

    # ---------- cache helpers ----------
    def _get_cached(self, key, allow_stale=False):
        item = self.cache.get(key)
        if not item:
            return None
        data, ts = item
        if allow_stale or time.time() - ts < self.cache_duration:
            return data
        return None

    def _set_cache(self, key, data):
        self.cache[key] = (data, time.time())

    # ---------- http ----------
    def _make_request(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            # Do NOT sleep here: a sleep would freeze the whole server.
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed ({endpoint}): {e}")
            raise

    def _cached_call(self, key, fetch):
        """Fresh cache -> API -> stale cache (if API fails) -> raise."""
        fresh = self._get_cached(key)
        if fresh is not None:
            return fresh
        try:
            result = fetch()
            self._set_cache(key, result)
            return result
        except Exception:
            stale = self._get_cached(key, allow_stale=True)
            if stale is not None:
                logging.warning(f"Serving stale data for {key}")
                return stale
            raise

    # ---------- public API ----------
    def get_market_overview(self):
        def fetch():
            coins = self._make_request("coins/markets", {
                "vs_currency": "usd", "order": "market_cap_desc",
                "per_page": 10, "page": 1, "sparkline": True,
                "price_change_percentage": "1h,24h,7d",
            })
            global_data = self._make_request("global")
            return {"coins": coins, "global": global_data["data"],
                    "timestamp": datetime.now().isoformat()}
        return self._cached_call("market_overview", fetch)

    def get_coin_history(self, coin_id, days=7):
        key = f"coin_history_{coin_id}_{days}"

        def fetch():
            data = self._make_request(f"coins/{coin_id}/market_chart",
                                      {"vs_currency": "usd", "days": days})
            return {"coin_id": coin_id, "prices": data["prices"],
                    "market_caps": data["market_caps"],
                    "total_volumes": data["total_volumes"],
                    "is_mock": False,
                    "timestamp": datetime.now().isoformat()}
        try:
            return self._cached_call(key, fetch)
        except Exception as e:
            logging.error(f"History for {coin_id} unavailable, using MOCK data: {e}")
            return self._get_mock_price_data(coin_id, days)

    def get_trending_coins(self):
        def fetch():
            data = self._make_request("search/trending")
            return {"trending": data["coins"], "timestamp": datetime.now().isoformat()}
        return self._cached_call("trending_coins", fetch)

    def get_defi_protocols(self):
        def fetch():
            data = self._make_request("coins/markets", {
                "vs_currency": "usd", "category": "decentralized-finance-defi",
                "order": "market_cap_desc", "per_page": 20, "page": 1,
                "sparkline": True, "price_change_percentage": "1h,24h,7d",
            })
            return {"protocols": data, "timestamp": datetime.now().isoformat()}
        return self._cached_call("defi_protocols", fetch)

    def _get_mock_price_data(self, coin_id, days=7):
        """Fake data used only when the API is unavailable. Flagged with is_mock."""
        base_price = 50000 if coin_id == "bitcoin" else 3000 if coin_id == "ethereum" else 100
        now = int(time.time() * 1000)
        prices, volumes, caps = [], [], []
        price = base_price
        for i in range(days * 24, 0, -1):          # oldest -> newest, random walk
            ts = now - i * 3600000
            price *= 1 + random.uniform(-0.01, 0.01)
            prices.append([ts, price])
            volumes.append([ts, random.uniform(1e6, 1e7)])
            caps.append([ts, price * 19000000])
        return {"coin_id": coin_id, "prices": prices, "market_caps": caps,
                "total_volumes": volumes, "is_mock": True,
                "timestamp": datetime.now().isoformat()}
