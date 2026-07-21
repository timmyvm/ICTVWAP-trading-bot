"""
Key Levels Module — tracks important ICT price levels.

These levels act as Points of Interest (POI) and Draw on Liquidity (DOL) targets.
ICT teaches that price moves FROM liquidity TO liquidity — these levels help us
identify where price is likely heading (DOL) and where we should look for entries (POI).

Levels tracked:
1. 10:00 AM NY opening price — marks the transition from London to NY session.
   ICT notes this as a key manipulation point.
2. Midnight (00:00 NY) opening price — the "true day open" in ICT terminology.
3. NWOG (New Week Opening Gap) — the gap between Friday's close and Sunday's open.
   This gap represents institutional positioning over the weekend.
4. Sus Candles — candles with almost no wick (<5% of range). These indicate strong
   directional conviction and the level becomes a DOL target.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Optional

import pandas as pd
import pytz

import config

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")


@dataclass
class NWOG:
    """
    New Week Opening Gap.

    Anchor A = close of the 16:59:59 EST Friday candle (market "close")
    Anchor B = open of the 18:00:00 EST Sunday candle (market "open")
    CE = midpoint of the gap

    If price is above CE: the gap acts as SUPPORT
    If price is below CE: the gap acts as RESISTANCE
    """

    anchor_a: float  # Friday close
    anchor_b: float  # Sunday open
    ce: float  # Consequent Encroachment (midpoint)
    filled: bool = False  # Whether price has tapped the CE

    @property
    def direction(self) -> str:
        """Gap direction: 'UP' if Sunday opened above Friday close, else 'DOWN'."""
        return "UP" if self.anchor_b > self.anchor_a else "DOWN"


@dataclass
class SusCandle:
    """
    A "suspicious" candle — one with almost no wick, indicating strong conviction.

    ICT Concept: when a candle closes with < 5% wick relative to its range,
    it means there was no opposition to the move. The closing price of that
    candle becomes a Draw on Liquidity target — price will likely revisit it.
    """

    timestamp: object
    timeframe: str  # "15m" or "4h"
    price_level: float  # The close price (DOL target)
    direction: str  # "BULLISH" (no upper wick) or "BEARISH" (no lower wick)


@dataclass
class KeyLevels:
    """
    Tracks and refreshes all key ICT levels.

    Refreshed on schedule:
    - NY midnight open: once per day at 00:00 NY
    - 10 AM open: once per day at 10:00 NY
    - NWOG: once per week (calculated from Friday close / Sunday open)
    - Sus candles: on every new 15m and 4H candle close
    """

    midnight_open: Optional[float] = None
    ten_am_open: Optional[float] = None
    nwog: Optional[NWOG] = None
    sus_candles: list = field(default_factory=list)
    _logged_sus_keys: set = field(default_factory=set)  # (timestamp, timeframe) of already-logged sus candles
    dol_targets: list = field(default_factory=list)  # All Draw on Liquidity targets

    # Structural DOL targets from the docx:
    # - Old highs/lows: previous session extremes that haven't been revisited
    # - Internal highs/lows: swing points within the current structure
    # - News highs/lows: extremes printed during NFP/CPI (almost as powerful as equal highs)
    old_highs: list = field(default_factory=list)
    old_lows: list = field(default_factory=list)
    internal_highs: list = field(default_factory=list)
    internal_lows: list = field(default_factory=list)
    news_levels: list = field(default_factory=list)  # NFP/CPI extremes

    def update_session_opens(self, df_1m: pd.DataFrame, now: Optional[datetime] = None):
        """
        Extract the midnight and 10 AM NY opening prices from 1m data.

        These are checked once and cached for the current trading day.
        `now` is injectable so backtests can replay history.
        """
        if df_1m.empty:
            return

        now_ny = now if now is not None else datetime.now(NY_TZ)
        today = now_ny.date()

        # Vectorized lookups — the old per-row iterrows scan was O(n) per tick
        # and dominated runtime in backtests.
        idx = df_1m.index
        if idx.tz is None:
            idx = idx.tz_localize(NY_TZ)
        is_today = pd.Index(idx.date) == today

        # Midnight open: first 1m candle at 00:00 NY time today.
        # A change in midnight open marks a new session — reset sus tracking.
        mid_mask = is_today & (idx.hour == 0) & (idx.minute == 0)
        if mid_mask.any():
            open_px = float(df_1m.loc[mid_mask, "open"].iloc[0])
            if self.midnight_open != open_px:
                self._logged_sus_keys.clear()
                self.midnight_open = open_px
                logger.info("Midnight open set: %.2f", self.midnight_open)

        # 10:00 AM open: first 1m candle at 10:00 NY time today
        ten_mask = is_today & (idx.hour == 10) & (idx.minute == 0)
        if ten_mask.any():
            open_px = float(df_1m.loc[ten_mask, "open"].iloc[0])
            if self.ten_am_open != open_px:
                self.ten_am_open = open_px
                logger.info("10 AM open set: %.2f", self.ten_am_open)

    def update_nwog(self, df_1m: pd.DataFrame):
        """
        Calculate the New Week Opening Gap from 1m candle data.

        NWOG = gap between:
          Anchor A: close of the last 1m candle on Friday at 16:59 EST
          Anchor B: open of the first 1m candle on Sunday at 18:00 EST

        This gap represents the weekend positioning by institutions.
        An unfilled NWOG below price forces bearish bias.
        """
        if df_1m.empty:
            return

        friday_close = None
        sunday_open = None

        for ts, row in df_1m.iterrows():
            ts_ny = ts if ts.tzinfo else NY_TZ.localize(ts)

            # Friday 16:59 EST — last minute before market "close"
            if ts_ny.weekday() == 4 and ts_ny.hour == 16 and ts_ny.minute == 59:
                friday_close = row["close"]

            # Sunday 18:00 EST — market "open" for the new week
            if ts_ny.weekday() == 6 and ts_ny.hour == 18 and ts_ny.minute == 0:
                sunday_open = row["open"]

        if friday_close is not None and sunday_open is not None:
            ce = (friday_close + sunday_open) / 2
            self.nwog = NWOG(
                anchor_a=friday_close,
                anchor_b=sunday_open,
                ce=ce,
            )
            logger.info(
                "NWOG: Fri close=%.2f, Sun open=%.2f, CE=%.2f (%s gap)",
                friday_close,
                sunday_open,
                ce,
                self.nwog.direction,
            )

    def check_nwog_filled(self, current_price: float):
        """Mark NWOG as filled if price has tapped the CE."""
        if self.nwog and not self.nwog.filled:
            if self.nwog.direction == "DOWN" and current_price <= self.nwog.ce:
                self.nwog.filled = True
                logger.info("NWOG CE tapped at %.2f — gap filled", self.nwog.ce)
            elif self.nwog.direction == "UP" and current_price >= self.nwog.ce:
                self.nwog.filled = True
                logger.info("NWOG CE tapped at %.2f — gap filled", self.nwog.ce)

    def scan_sus_candles(self, df: pd.DataFrame, timeframe: str):
        """
        Scan for "sus candles" — candles with wicks < 5% of total range.

        ICT Concept: A candle that closes with virtually no wick means there
        was zero opposition to the move. The market "wants" to revisit that
        level. This makes it a strong DOL (Draw on Liquidity) target.

        We check the most recent closed candle only.
        """
        if df.empty or len(df) < 2:
            return

        # Check the last CLOSED candle (second to last, since last may be forming)
        candle = df.iloc[-2]
        candle_key = (df.index[-2], timeframe)

        # Skip if this candle was already evaluated
        if candle_key in self._logged_sus_keys:
            return
        self._logged_sus_keys.add(candle_key)

        total_range = candle["high"] - candle["low"]

        if total_range == 0:
            return

        # Calculate wick percentages
        if candle["close"] >= candle["open"]:
            # Bullish candle
            upper_wick = candle["high"] - candle["close"]
            lower_wick = candle["open"] - candle["low"]
        else:
            # Bearish candle
            upper_wick = candle["high"] - candle["open"]
            lower_wick = candle["close"] - candle["low"]

        upper_wick_pct = upper_wick / total_range
        lower_wick_pct = lower_wick / total_range

        threshold = config.NO_WICK_THRESHOLD

        # Bullish sus candle: no upper wick on a bullish body.
        # Body direction guard prevents a bearish marubozu (open=high, close=low,
        # therefore upper_wick=0) from being mis-classified as bullish.
        if upper_wick_pct < threshold and candle["close"] >= candle["open"]:
            sus = SusCandle(
                timestamp=df.index[-2],
                timeframe=timeframe,
                price_level=candle["close"],
                direction="BULLISH",
            )
            self.sus_candles.append(sus)
            self.dol_targets.append(candle["close"])
            self._prune_targets()
            logger.info(
                "Sus candle detected (%s): BULLISH at %.2f (upper wick=%.1f%%)",
                timeframe,
                candle["close"],
                upper_wick_pct * 100,
            )

        # Bearish sus candle: no lower wick on a bearish body.
        # Body direction guard prevents a bullish marubozu (open=low, close=high,
        # therefore lower_wick=0) from double-firing the same price as BEARISH.
        if lower_wick_pct < threshold and candle["close"] < candle["open"]:
            sus = SusCandle(
                timestamp=df.index[-2],
                timeframe=timeframe,
                price_level=candle["close"],
                direction="BEARISH",
            )
            self.sus_candles.append(sus)
            self.dol_targets.append(candle["close"])
            self._prune_targets()
            logger.info(
                "Sus candle detected (%s): BEARISH at %.2f (lower wick=%.1f%%)",
                timeframe,
                candle["close"],
                lower_wick_pct * 100,
            )

    def _prune_targets(self, max_len: int = 100):
        """Cap unbounded growth — a multi-day process otherwise accumulates
        stale sus-candle levels forever and they pollute nearest-DOL selection."""
        if len(self.dol_targets) > max_len:
            self.dol_targets = self.dol_targets[-max_len:]
        if len(self.sus_candles) > max_len:
            self.sus_candles = self.sus_candles[-max_len:]

    def scan_structural_levels(self, df_1h: pd.DataFrame, df_4h: pd.DataFrame):
        """
        Extract old highs/lows and internal swing highs/lows from HTF data.

        ICT Concept: Price moves FROM liquidity TO liquidity. Old highs/lows
        are pools of resting liquidity (stop losses). Internal highs/lows are
        intermediate targets within the current leg.

        Docx: "Internal highs / lows, Old highs / old lows" are primary DOL targets.
        """
        if not df_1h.empty:
            self._extract_swing_levels(df_1h, "1h")
        if not df_4h.empty:
            self._extract_swing_levels(df_4h, "4h")

    def _extract_swing_levels(self, df: pd.DataFrame, timeframe: str):
        """
        Identify swing highs/lows from a DataFrame and categorize them.

        Old highs/lows = extremes from older candles (>20 bars ago)
        Internal highs/lows = more recent swing points within the current structure
        """
        lookback = 3  # Simpler swing detection for DOL purposes
        highs = df["high"]
        lows = df["low"]

        for i in range(lookback, len(df) - lookback):
            window_h = highs.iloc[i - lookback: i + lookback + 1]
            window_l = lows.iloc[i - lookback: i + lookback + 1]

            is_swing_high = highs.iloc[i] == window_h.max()
            is_swing_low = lows.iloc[i] == window_l.min()

            age = len(df) - i  # How many bars ago

            if is_swing_high:
                level = float(highs.iloc[i])
                if age > 20:
                    if level not in self.old_highs:
                        self.old_highs.append(level)
                else:
                    if level not in self.internal_highs:
                        self.internal_highs.append(level)

            if is_swing_low:
                level = float(lows.iloc[i])
                if age > 20:
                    if level not in self.old_lows:
                        self.old_lows.append(level)
                else:
                    if level not in self.internal_lows:
                        self.internal_lows.append(level)

        # Keep lists manageable — only the most recent 20 of each
        self.old_highs = self.old_highs[-20:]
        self.old_lows = self.old_lows[-20:]
        self.internal_highs = self.internal_highs[-20:]
        self.internal_lows = self.internal_lows[-20:]

        logger.debug(
            "Structural levels (%s): %d old highs, %d old lows, "
            "%d internal highs, %d internal lows",
            timeframe,
            len(self.old_highs), len(self.old_lows),
            len(self.internal_highs), len(self.internal_lows),
        )

    def record_news_level(self, price: float, event: str):
        """
        Record a high or low printed during a news event (NFP, CPI).

        Docx V4: "News highs/lows (e.g. NFP low) are almost as powerful as
        equal highs/lows as DOL targets."

        Called externally when a news event is detected and the extreme
        price during that window is known.
        """
        entry = {"price": price, "event": event}
        if entry not in self.news_levels:
            self.news_levels.append(entry)
            self.dol_targets.append(price)
            logger.info("News level recorded: %s at %.2f", event, price)

    def get_nearest_dol(self, price: float, direction: str) -> Optional[float]:
        """
        Get the nearest Draw on Liquidity target in the given direction.

        Combines ALL DOL sources per the docx:
        - NWOG CE
        - Midnight Open
        - 10 AM Open
        - Sus candles (15m/4H no-wick)
        - Old highs/lows
        - Internal highs/lows
        - News highs/lows

        For LONGS: find nearest DOL ABOVE current price (upside target)
        For SHORTS: find nearest DOL BELOW current price (downside target)
        """
        # Combine all DOL sources
        all_targets = list(self.dol_targets)
        if self.midnight_open:
            all_targets.append(self.midnight_open)
        if self.ten_am_open:
            all_targets.append(self.ten_am_open)
        if self.nwog and not self.nwog.filled:
            all_targets.append(self.nwog.ce)

        # Add structural levels
        all_targets.extend(self.old_highs)
        all_targets.extend(self.old_lows)
        all_targets.extend(self.internal_highs)
        all_targets.extend(self.internal_lows)

        # Add news levels
        all_targets.extend(nl["price"] for nl in self.news_levels)

        if not all_targets:
            return None

        # Deduplicate
        all_targets = list(set(all_targets))

        if direction == "LONG":
            above = [t for t in all_targets if t > price]
            return min(above) if above else None
        else:
            below = [t for t in all_targets if t < price]
            return max(below) if below else None

    def load_news_levels(self):
        """
        Load manually configured NEWS_LEVELS from config into DOL targets.

        Powell V4: "News highs/lows (e.g. NFP low) are almost as powerful as
        equal highs/lows as DOL targets."
        """
        for nl in config.NEWS_LEVELS:
            level = nl.get("level")
            ntype = nl.get("type", "news")
            if level is not None:
                entry = {"price": level, "event": ntype}
                if entry not in self.news_levels:
                    self.news_levels.append(entry)
                    self.dol_targets.append(level)
                    logger.info("Config news level loaded: %s at %.2f", ntype, level)

    def get_all_levels(self) -> dict:
        """Return a summary of all tracked levels."""
        return {
            "midnight_open": self.midnight_open,
            "ten_am_open": self.ten_am_open,
            "nwog_ce": self.nwog.ce if self.nwog else None,
            "nwog_filled": self.nwog.filled if self.nwog else None,
            "sus_candle_count": len(self.sus_candles),
            "old_highs": len(self.old_highs),
            "old_lows": len(self.old_lows),
            "internal_highs": len(self.internal_highs),
            "internal_lows": len(self.internal_lows),
            "news_levels": len(self.news_levels),
            "dol_targets": self.dol_targets[-10:],  # Last 10
        }


class ATRModeSwitcher:
    """
    ATR-based auto mode switching between 1m and 5m entry timeframes.

    ICT Concept: When volatility (ATR) is high, the 5m timeframe gives
    wider stops but more reliable signals. When ATR is low, 1m provides
    precision entries with tighter stops.

    Logic:
    - If 5m ATR exceeds ATR_HIGH_THRESHOLD × 20-period average → switch to "5m"
    - If ATR falls below ATR_LOW_THRESHOLD for ATR_COOLDOWN_CANDLES → switch to "1m"
    """

    def __init__(self):
        self.current_mode: str = config.ENTRY_MODE
        self._low_atr_count: int = 0
        self._high_atr_count: int = 0  # Hysteresis counter for 5m switch

    def evaluate(self, df_5m: pd.DataFrame) -> str:
        """
        Check ATR and decide if mode should switch.

        Both directions require ATR_COOLDOWN_CANDLES consecutive candles above/below
        threshold before switching — prevents thrashing on a single spike.

        Args:
            df_5m: 5-minute OHLCV DataFrame.

        Returns:
            The recommended entry mode: "1m" or "5m".
        """
        if df_5m.empty or len(df_5m) < config.ATR_PERIOD + 1:
            return self.current_mode

        # Calculate ATR (True Range) on 5m
        highs = df_5m["high"]
        lows = df_5m["low"]
        closes = df_5m["close"].shift(1)

        tr = pd.concat([
            highs - lows,
            (highs - closes).abs(),
            (lows - closes).abs(),
        ], axis=1).max(axis=1)

        atr = tr.rolling(window=config.ATR_PERIOD).mean()

        if atr.iloc[-1] is None or pd.isna(atr.iloc[-1]):
            return self.current_mode

        current_atr = atr.iloc[-1]
        avg_atr = atr.iloc[-config.ATR_PERIOD:].mean()

        if avg_atr == 0 or current_atr <= 0 or pd.isna(current_atr):
            return self.current_mode

        ratio = current_atr / avg_atr

        if ratio >= config.ATR_HIGH_THRESHOLD:
            self._high_atr_count += 1
            self._low_atr_count = 0
            if self._high_atr_count >= config.ATR_COOLDOWN_CANDLES and self.current_mode != "5m":
                logger.info(
                    "ATR high for %d candles (ratio=%.2f >= %.2f) — switching to 5m mode",
                    self._high_atr_count, ratio, config.ATR_HIGH_THRESHOLD,
                )
                self.current_mode = "5m"
                self._high_atr_count = 0

        elif ratio <= config.ATR_LOW_THRESHOLD:
            self._low_atr_count += 1
            self._high_atr_count = 0
            if self._low_atr_count >= config.ATR_COOLDOWN_CANDLES and self.current_mode != "1m":
                logger.info(
                    "ATR low for %d candles (ratio=%.2f <= %.2f) — switching to 1m mode",
                    self._low_atr_count, ratio, config.ATR_LOW_THRESHOLD,
                )
                self.current_mode = "1m"
                self._low_atr_count = 0
        else:
            self._low_atr_count = 0
            self._high_atr_count = 0

        return self.current_mode
