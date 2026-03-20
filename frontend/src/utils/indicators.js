export function computeEMA(closes, period) {
  const result = new Array(closes.length).fill(null);
  if (closes.length < period) return result;

  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += closes[i];
  }
  let prevEma = sum / period;
  result[period - 1] = prevEma;

  const multiplier = 2 / (period + 1);
  for (let i = period; i < closes.length; i++) {
    const ema = (closes[i] - prevEma) * multiplier + prevEma;
    result[i] = ema;
    prevEma = ema;
  }
  return result;
}

export function computeRSI(closes, period = 14) {
  const result = new Array(closes.length).fill(null);
  if (closes.length <= period) return result;

  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) gains += diff;
    else losses -= diff;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  result[period] = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));

  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;

    result[i] = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));
  }
  return result;
}

export function computeMACD(closes, fast = 12, slow = 26, signal = 9) {
  const result = new Array(closes.length).fill(null);
  const fastEma = computeEMA(closes, fast);
  const slowEma = computeEMA(closes, slow);
  
  const macdArray = new Array(closes.length).fill(null);
  const macdValidValues = [];
  const macdValidIndices = [];

  for (let i = 0; i < closes.length; i++) {
    if (fastEma[i] !== null && slowEma[i] !== null) {
      const macdVal = fastEma[i] - slowEma[i];
      macdArray[i] = macdVal;
      macdValidValues.push(macdVal);
      macdValidIndices.push(i);
    }
  }

  const signalEmaValid = computeEMA(macdValidValues, signal);
  
  for (let k = 0; k < signalEmaValid.length; k++) {
    const origIndex = macdValidIndices[k];
    const s = signalEmaValid[k];
    const m = macdArray[origIndex];
    if (s !== null) {
      result[origIndex] = {
        macd: m,
        signal: s,
        histogram: m - s
      };
    } else {
      result[origIndex] = { macd: m, signal: null, histogram: null };
    }
  }
  
  return result;
}

export function computeBollingerBands(closes, period = 20, stdDev = 2) {
  const result = new Array(closes.length).fill(null);
  if (closes.length < period) return result;

  for (let i = period - 1; i < closes.length; i++) {
    const slice = closes.slice(i - period + 1, i + 1);
    const sum = slice.reduce((a, b) => a + b, 0);
    const sma = sum / period;
    
    const variance = slice.reduce((acc, val) => acc + Math.pow(val - sma, 2), 0) / period;
    const sd = Math.sqrt(variance);
    
    result[i] = {
      middle: sma,
      upper: sma + stdDev * sd,
      lower: sma - stdDev * sd
    };
  }
  return result;
}

export function computeVolumeMA(volumes, period = 20) {
  const result = new Array(volumes.length).fill(null);
  if (volumes.length < period) return result;

  for (let i = period - 1; i < volumes.length; i++) {
    const slice = volumes.slice(i - period + 1, i + 1);
    const sum = slice.reduce((a, b) => a + b, 0);
    result[i] = sum / period;
  }
  return result;
}
