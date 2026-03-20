export const MOCK_PATTERNS = [
  {
    id:           "pattern_rel_1",
    symbol:       "RELIANCE",
    pattern_type: "GOLDEN_CROSS",
    direction:    "BULLISH",
    confidence:   0.82,
    detected_on:  "2024-08-15",
    description:  "50-day EMA crossed above 200-day EMA, signaling a potential sustained uptrend. Volume confirmation observed with 1.4x average volume on crossover day.",
    key_levels: { support: 2780, resistance: 3050, target: 3180, stop_loss: 2710 },
    backtest: { win_rate: 0.71, avg_return_pct: 8.4, avg_days: 34, sample_size: 17 }
  },
  {
    id:           "pattern_rel_2",
    symbol:       "RELIANCE",
    pattern_type: "BULL_FLAG",
    direction:    "BULLISH",
    confidence:   0.65,
    detected_on:  "2024-09-02",
    description:  "A continuation bull flag pattern identified after a strong upward rally. Price consolidation is nearing the upper trendline, indicating a potential upside breakout soon.",
    key_levels: { support: 2980, resistance: 3040, target: 3120, stop_loss: 2950 },
    backtest: { win_rate: 0.62, avg_return_pct: 4.1, avg_days: 12, sample_size: 28 }
  },
  {
    id:           "pattern_tcs_1",
    symbol:       "TCS",
    pattern_type: "DOUBLE_BOTTOM",
    direction:    "BULLISH",
    confidence:   0.88,
    detected_on:  "2024-08-28",
    description:  "Classic double bottom formation at the crucial support level of ₹3850. The second trough showed diminishing selling volume, preceded by a strong RSI bullish divergence.",
    key_levels: { support: 3820, resistance: 4050, target: 4180, stop_loss: 3790 },
    backtest: { win_rate: 0.76, avg_return_pct: 6.5, avg_days: 22, sample_size: 14 }
  },
  {
    id:           "pattern_tcs_2",
    symbol:       "TCS",
    pattern_type: "MACD_CROSSOVER",
    direction:    "BEARISH",
    confidence:   0.55,
    detected_on:  "2024-09-05",
    description:  "MACD line crossed below the signal line in overbought territory. This momentum shift suggests a short-term pullback before resuming the broader structural uptrend.",
    key_levels: { support: 4020, resistance: 4150, target: 3950, stop_loss: 4180 },
    backtest: { win_rate: 0.58, avg_return_pct: -3.2, avg_days: 8, sample_size: 42 }
  },
  {
    id:           "pattern_hdfc_1",
    symbol:       "HDFCBANK",
    pattern_type: "RESISTANCE_REJECTION",
    direction:    "BEARISH",
    confidence:   0.78,
    detected_on:  "2024-09-10",
    description:  "Multiple failed attempts to breach the heavy supply zone at ₹1680. Formed a shooting star candlestick on the daily timeframe with elevated volume, confirming the rejection.",
    key_levels: { support: 1580, resistance: 1680, target: 1540, stop_loss: 1700 },
    backtest: { win_rate: 0.65, avg_return_pct: -4.8, avg_days: 15, sample_size: 24 }
  },
  {
    id:           "pattern_infy_1",
    symbol:       "INFY",
    pattern_type: "RSI_DIVERGENCE",
    direction:    "BULLISH",
    confidence:   0.81,
    detected_on:  "2024-09-11",
    description:  "Price made a lower low while RSI formed a higher low. This bullish divergence indicates exhausting bearish momentum and a high probability of a trend reversal toward the 50-day EMA.",
    key_levels: { support: 1650, resistance: 1780, target: 1840, stop_loss: 1620 },
    backtest: { win_rate: 0.68, avg_return_pct: 5.2, avg_days: 18, sample_size: 31 }
  },
  {
    id:           "pattern_icici_1",
    symbol:       "ICICIBANK",
    pattern_type: "BREAKOUT",
    direction:    "BULLISH",
    confidence:   0.92,
    detected_on:  "2024-09-08",
    description:  "Decisive breakout above the multi-month ascending triangle resistance at ₹1120. Volume was 2.5x the 20-day average, strongly confirming institutional buying interest.",
    key_levels: { support: 1090, resistance: 1120, target: 1250, stop_loss: 1070 },
    backtest: { win_rate: 0.81, avg_return_pct: 9.5, avg_days: 25, sample_size: 11 }
  },
  {
    id:           "pattern_icici_2",
    symbol:       "ICICIBANK",
    pattern_type: "DEATH_CROSS",
    direction:    "BEARISH",
    confidence:   0.45,
    detected_on:  "2024-05-15",
    description:  "50-day EMA crossed below the 200-day EMA. However, the price has already retraced significantly and is nearing major historical support, reducing the reliability of this lagging signal.",
    key_levels: { support: 980, resistance: 1050, target: 920, stop_loss: 1080 },
    backtest: { win_rate: 0.48, avg_return_pct: -6.2, avg_days: 40, sample_size: 9 }
  }
];

export function getPatterns(symbol) {
  return MOCK_PATTERNS.filter(p => p.symbol === symbol);
}
