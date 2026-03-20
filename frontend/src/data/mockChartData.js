function seededRandom(seed) {
  let s = seed
  return function() {
    s = (s * 1664525 + 1013904223) & 0xffffffff
    return (s >>> 0) / 0xffffffff
  }
}

const STOCK_PARAMS = {
  RELIANCE:  { start: 2850, baseVolume: 8500000,  name: "Reliance Industries Ltd" },
  TCS:       { start: 3900, baseVolume: 3200000,  name: "Tata Consultancy Services" },
  HDFCBANK:  { start: 1620, baseVolume: 12000000, name: "HDFC Bank Ltd" },
  INFY:      { start: 1780, baseVolume: 9800000,  name: "Infosys Ltd" },
  ICICIBANK: { start: 1050, baseVolume: 15000000, name: "ICICI Bank Ltd" }
};

export const STOCK_LIST = Object.keys(STOCK_PARAMS).map(symbol => ({ 
  symbol, 
  name: STOCK_PARAMS[symbol].name 
}));

function isWeekday(date) {
  const day = date.getDay();
  return day !== 0 && day !== 6;
}

function generateData(symbol, params) {
  // Use a string hash + arbitrary multiplier for the seed to ensure stability
  let seedVal = 0;
  for(let i = 0; i < symbol.length; i++){ seedVal += symbol.charCodeAt(i); }
  const random = seededRandom(seedVal * 1024 + params.start);
  
  const data = [];
  let currentDate = new Date('2024-01-02T00:00:00Z');
  let currentPrice = params.start;

  while(data.length < 180) {
    if (isWeekday(currentDate)) {
      const isBigMove = random() < 0.05;
      
      const rand1 = random();
      const rand2 = random();
      const rand3 = random();
      const rand4 = random();
      const rand5 = random();
      
      const dir = rand1 > 0.5 ? 1 : -1;
      
      const changePct = isBigMove 
        ? (rand2 * 0.03 + 0.03) * dir    // 3% to 6%
        : (rand2 * 0.02 + 0.005) * dir;  // 0.5% to 2.5%
      
      const open = currentPrice;
      const close = open * (1 + changePct);
      
      const wickHighPct = rand3 * 0.007 + 0.001; // 0.1% to 0.8%
      const wickLowPct = rand4 * 0.007 + 0.001;
      
      const maxPrice = Math.max(open, close);
      const minPrice = Math.min(open, close);
      
      const high = maxPrice * (1 + wickHighPct);
      const low = minPrice * (1 - wickLowPct);
      
      const volMultiplier = isBigMove ? (1.5 + rand5) : (1 + (rand5 - 0.5) * 0.8);
      const volume = Math.floor(params.baseVolume * volMultiplier);
      
      data.push({
        date: currentDate.toISOString().split('T')[0],
        open: Number(open.toFixed(2)),
        high: Number(high.toFixed(2)),
        low: Number(low.toFixed(2)),
        close: Number(close.toFixed(2)),
        volume: volume
      });
      currentPrice = close;
    }
    // Add 1 day
    currentDate.setDate(currentDate.getDate() + 1);
  }
  return data;
}

const CACHED_DATA = {};
Object.entries(STOCK_PARAMS).forEach(([symbol, params]) => {
  CACHED_DATA[symbol] = generateData(symbol, params);
});

export function getStockData(symbol) {
  return CACHED_DATA[symbol] || [];
}

export function getLatestQuote(symbol) {
  const data = CACHED_DATA[symbol];
  if (!data || data.length === 0) return null;
  
  const last = data[data.length - 1];
  const prev = data.length > 1 ? data[data.length - 2] : last;
  
  const close = last.close;
  const prev_close = prev.close;
  const change = close - prev_close;
  const change_pct = (change / prev_close) * 100;
  
  const last5 = data.slice(-5);
  const week_high = Math.max(...last5.map(d => d.high));
  const week_low = Math.min(...last5.map(d => d.low));
  
  const last20 = data.slice(-20);
  const avg_volume = Math.floor(last20.reduce((sum, d) => sum + d.volume, 0) / last20.length);
  
  return {
    ...last,
    change,
    change_pct,
    week_high,
    week_low,
    avg_volume
  };
}
