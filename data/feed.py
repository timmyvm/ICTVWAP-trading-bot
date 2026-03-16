"""
Data feed module — fetches OHLCV candles from Bybit Testnet.

Uses pybit's HTTP session to pull kline data. All timestamps are converted
to New York time internally since ICT concepts (killzones, NWOG, key levels)
are anchored to the NY session.
"""

import logging
from datetime import datetime, timezone

import pandas as pd
import pytz
from pybit.unified_trading import HTTP

import config

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")


class DataFeed:
    """Wraps Bybit kline API and returns pandas DataFrames in NY time."""

    def __init__(self):
        self.session = HTTP(
            testnet=config.BYBIT_TESTNET,
            api_key=config.BYBIT_API_KEY,
            api_secret=config.BYBIT_API_SECRET,
        )

    def get_candles(
        self, interval: str, limit: int = 200, symbol: str | None = None,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV candles for a symbol.

        Args:
            interval: Bybit interval code ("1", "5", "15", "60", "240").
            limit: Number of candles to fetch (max 200 per request).
            symbol: Override symbol (defaults to config.SYMBOL).

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            indexed by NY-time datetime.
        """
        symbol = symbol or config.SYMBOL
        try:
            resp = self.session.get_kline(
                category=config.CATEGORY,
                symbol=symbol,
                interval=interval,
                limit=limit,
            )
            rows = resp["result"]["list"]
        except Exception as e:
            logger.error("Failed to fetch candles (%s, interval=%s): %s", symbol, interval, e)
            return pd.DataFrame()

        if not rows:
            return pd.DataFrame()

        # Bybit returns: [startTime, open, high, low, close, volume, turnover]
        # Rows come newest-first, so reverse for chronological order.
        df = pd.DataFrame(
            reversed(rows),
            columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"],
        )

        # Convert types
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms", utc=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        # Convert to NY time — all ICT levels reference NY session
        df["timestamp"] = df["timestamp"].dt.tz_convert(NY_TZ)
        df.set_index("timestamp", inplace=True)
        df.drop(columns=["turnover"], inplace=True)

        return df

    def get_candles_by_tf(
        self, timeframe: str, limit: int = 200, symbol: str | None = None,
    ) -> pd.DataFrame:
        """Convenience wrapper that accepts human-readable timeframe like '1m', '5m', '1h'."""
        interval = config.TIMEFRAME_MAP.get(timeframe, timeframe)
        return self.get_candles(interval, limit, symbol=symbol)

    def get_mark_price(self, symbol: str | None = None) -> float | None:
        """Fetch current mark price for position sizing / bias checks."""
        symbol = symbol or config.SYMBOL
        try:
            resp = self.session.get_tickers(
                category=config.CATEGORY,
                symbol=symbol,
            )
            return float(resp["result"]["list"][0]["markPrice"])
        except Exception as e:
            logger.error("Failed to fetch mark price for %s: %s", symbol, e)
            return None

    def get_symbols(self) -> list[str]:
        """
        Return the list of symbols to monitor based on active_params().

        In TESTING_MODE, this may include ETHUSDT alongside BTCUSDT.
        In LIVE mode, typically just BTCUSDT.
        """
        return config.active_params().get("symbols", [config.SYMBOL])

    def get_account_balance(self) -> float | None:
        """Fetch USDT wallet balance for position sizing."""
        try:
            resp = self.session.get_wallet_balance(
                accountType="UNIFIED",
                coin="USDT",
            )
            coins = resp["result"]["list"][0]["coin"]
            for coin in coins:
                if coin["coin"] == "USDT":
                    return float(coin["walletBalance"])
            return None
        except Exception as e:
            logger.error("Failed to fetch account balance: %s", e)
            return None
