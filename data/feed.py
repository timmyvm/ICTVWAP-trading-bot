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

    # Interval code -> candle duration in seconds (for forming-candle detection)
    _INTERVAL_SECONDS = {
        "1": 60, "3": 180, "5": 300, "15": 900, "30": 1800,
        "60": 3600, "120": 7200, "240": 14400, "D": 86400,
    }

    def get_candles(
        self,
        interval: str,
        limit: int = 200,
        symbol: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        drop_forming: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV candles for a symbol.

        Args:
            interval: Bybit interval code ("1", "5", "15", "60", "240").
            limit: Number of candles to fetch (max 1000 per request).
            symbol: Override symbol (defaults to config.SYMBOL).
            start_ms/end_ms: Optional epoch-ms window for historical ranges.
            drop_forming: Drop the still-forming last candle. Bybit includes the
                in-progress candle as the newest row; every strategy module treats
                the last row as a CLOSED confirmation candle, so by default we
                only return closed candles.

        Returns:
            DataFrame with columns: open, high, low, close, volume
            indexed by NY-time datetime.
        """
        symbol = symbol or config.SYMBOL
        try:
            kwargs: dict = dict(
                category=config.CATEGORY,
                symbol=symbol,
                interval=interval,
                limit=limit,
            )
            if start_ms is not None:
                kwargs["start"] = start_ms
            if end_ms is not None:
                kwargs["end"] = end_ms
            resp = self.session.get_kline(**kwargs)
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

        # Drop the in-progress candle: its close/high/low keep changing until the
        # interval ends, which turns "confirmation candle" checks into noise.
        duration = self._INTERVAL_SECONDS.get(interval)
        if drop_forming and duration is not None and not df.empty:
            now_utc = pd.Timestamp.now(tz="UTC")
            last_close_time = df.index[-1].tz_convert("UTC") + pd.Timedelta(seconds=duration)
            if last_close_time > now_utc:
                df = df.iloc[:-1]

        return df

    def get_candles_by_tf(
        self, timeframe: str, limit: int = 200, symbol: str | None = None,
    ) -> pd.DataFrame:
        """Convenience wrapper that accepts human-readable timeframe like '1m', '5m', '1h'."""
        interval = config.TIMEFRAME_MAP.get(timeframe, timeframe)
        return self.get_candles(interval, limit, symbol=symbol)

    def get_weekend_candles_1m(self, symbol: str | None = None) -> pd.DataFrame:
        """
        Fetch the 1m candles needed to compute NWOG for the current week:
        a window around last Friday 16:59 NY (close anchor) and around last
        Sunday 18:00 NY (open anchor).

        A plain limit=200 fetch only spans ~3.3 hours, so unless the bot boots
        Sunday evening it can never see both anchors — this targets them directly.
        """
        now_ny = datetime.now(NY_TZ)

        # Most recent Sunday 18:00 NY at or before now
        days_since_sunday = (now_ny.weekday() - 6) % 7
        sunday = (now_ny - pd.Timedelta(days=days_since_sunday)).date()
        sunday_open = NY_TZ.localize(datetime(sunday.year, sunday.month, sunday.day, 18, 0))
        if sunday_open > now_ny:
            sunday_open -= pd.Timedelta(days=7)

        # The Friday 17:00 close preceding that Sunday open
        friday_close = sunday_open - pd.Timedelta(days=2, hours=1)

        frames = []
        for anchor_start, minutes in (
            (friday_close - pd.Timedelta(minutes=10), 15),   # Fri 16:50-17:05
            (sunday_open - pd.Timedelta(minutes=5), 10),     # Sun 17:55-18:05
        ):
            start_ms = int(anchor_start.timestamp() * 1000)
            end_ms = start_ms + minutes * 60 * 1000
            frame = self.get_candles(
                "1", limit=minutes + 5, symbol=symbol,
                start_ms=start_ms, end_ms=end_ms, drop_forming=False,
            )
            if not frame.empty:
                frames.append(frame)

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames).sort_index()

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
