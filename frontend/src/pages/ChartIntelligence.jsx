import React, { useState, useMemo, useEffect, useRef } from 'react';
import CandlestickChart from '../components/chart/CandlestickChart';
import PatternPanel from '../components/chart/PatternPanel';
import { STOCK_LIST, getStockData, getLatestQuote } from '../data/mockChartData';
import { getPatterns } from '../data/mockPatterns';
import { computeEMA, computeRSI, computeMACD, computeBollingerBands, computeVolumeMA } from '../utils/indicators';

export default function ChartIntelligence() {
  const [selectedSymbol, setSelectedSymbol] = useState("RELIANCE");
  const [timeframe, setTimeframe] = useState("1Y");
  const [indicators, setIndicators] = useState({ showEMA: true, showBB: true, showVOL: true });
  
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const searchRef = useRef(null);

  const [selectedPattern, setSelectedPattern] = useState(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowSearch(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const rawData = useMemo(() => getStockData(selectedSymbol), [selectedSymbol]);
  
  const filteredData = useMemo(() => {
    if (!rawData || rawData.length === 0) return [];
    let count = rawData.length;
    if (timeframe === '1W') count = 5;
    else if (timeframe === '1M') count = 22;
    else if (timeframe === '3M') count = 65;
    else if (timeframe === '6M') count = 130;
    else if (timeframe === '1Y') count = 180;
    return rawData.slice(-count);
  }, [rawData, timeframe]);

  const chartData = useMemo(() => {
    if (filteredData.length === 0) return [];
    
    const closes = filteredData.map(d => d.close);
    const volumes = filteredData.map(d => d.volume);
    
    const ema20 = computeEMA(closes, 20);
    const ema50 = computeEMA(closes, 50);
    const ema200 = computeEMA(closes, 200);
    const bBands = computeBollingerBands(closes);
    const rsi = computeRSI(closes);
    const macd = computeMACD(closes);
    const volumeMA = computeVolumeMA(volumes);
    
    return filteredData.map((candle, i) => ({
      ...candle,
      ema20:    ema20[i],
      ema50:    ema50[i],
      ema200:   ema200[i],
      bbUpper:  bBands[i]?.upper,
      bbMiddle: bBands[i]?.middle,
      bbLower:  bBands[i]?.lower,
      rsi:      rsi[i],
      macdLine: macd[i]?.macd,
      macdSig:  macd[i]?.signal,
      macdHist: macd[i]?.histogram,
      volumeMA: volumeMA[i],
    }));
  }, [filteredData]);

  const quote = useMemo(() => getLatestQuote(selectedSymbol), [selectedSymbol]);
  const patterns = useMemo(() => getPatterns(selectedSymbol), [selectedSymbol]);
  
  const searchResults = useMemo(() => {
    if (!searchQuery) return STOCK_LIST;
    const q = searchQuery.toLowerCase();
    return STOCK_LIST.filter(s => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q));
  }, [searchQuery]);

  const toggleInd = (key) => setIndicators(prev => ({ ...prev, [key]: !prev[key] }));

  const aggWinRate = patterns.length > 0 ? Math.round(patterns.reduce((sum, p) => sum + p.backtest.win_rate, 0) / patterns.length * 100) : 0;
  const aggReturn = patterns.length > 0 ? (patterns.reduce((sum, p) => sum + p.backtest.avg_return_pct, 0) / patterns.length).toFixed(1) : 0;

  return (
    <div className="h-full w-full flex flex-col bg-[#131722] text-[#D1D4DC] overflow-hidden">
      
      {/* Top Toolbar */}
      <div className="flex-none h-[48px] bg-[#1E222D] border-b border-[#2A2E39] flex items-center px-4 justify-between shrink-0 box-border">
        <div className="flex items-center space-x-6">
          
          {/* Search */}
          <div className="relative" ref={searchRef}>
            <input 
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setShowSearch(true)}
              placeholder="Search symbol... e.g. RELIANCE"
              className="w-[240px] h-[32px] bg-[#2A2E39] border border-[#363A45] rounded-sm px-3 text-[13px] text-[#D1D4DC] focus:outline-none focus:border-[#2962FF]"
            />
            {showSearch && (
              <div className="absolute top-[36px] left-0 w-full max-h-[200px] overflow-y-auto bg-[#1E222D] border border-[#2A2E39] rounded-sm z-50 shadow-xl">
                {searchResults.length === 0 ? (
                  <div className="p-3 text-[11px] text-[#787B86]">No results found</div>
                ) : (
                  searchResults.map(s => (
                    <div 
                      key={s.symbol}
                      className="h-[36px] px-3 flex flex-col justify-center cursor-pointer hover:bg-[#2A2E39] border-b border-[#2A2E39] last:border-0"
                      onClick={() => {
                        setSelectedSymbol(s.symbol);
                        setSearchQuery("");
                        setShowSearch(false);
                      }}
                    >
                      <div className="text-[13px] font-medium text-[#D1D4DC] leading-tight">{s.symbol}</div>
                      <div className="text-[10px] text-[#787B86] leading-tight truncate">{s.name}</div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Timeframe */}
          <div className="flex items-center border border-[#2A2E39] rounded-sm overflow-hidden">
            {['1W', '1M', '3M', '6M', '1Y'].map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`h-[32px] px-3 text-[12px] font-medium border-r border-[#2A2E39] last:border-r-0 transition-colors ${
                  timeframe === tf ? 'bg-[#1E2B4D] text-[#2962FF]' : 'bg-transparent text-[#787B86] hover:text-[#D1D4DC]'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Indicators */}
        <div className="flex items-center space-x-2">
          {[
            { key: 'showEMA', label: 'EMA' },
            { key: 'showBB', label: 'BB' },
            { key: 'showVOL', label: 'VOL' },
          ].map(ind => (
            <button
              key={ind.key}
              onClick={() => toggleInd(ind.key)}
              className={`h-[28px] px-2.5 text-[11px] font-medium rounded-[3px] transition-colors border ${
                indicators[ind.key] ? 'bg-[#1E2B4D] text-[#2962FF] border-[#2962FF33]' : 'bg-transparent text-[#787B86] border-[#2A2E39] hover:text-[#D1D4DC]'
              }`}
            >
              {ind.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        
        {/* Main Chart Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Quote Bar */}
          {quote && (
            <div className="flex-none h-[36px] bg-[#131722] px-4 flex items-center space-x-6 shrink-0 border-b border-[#1E222D]">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-[14px]">{selectedSymbol}</span>
                <span className="text-[12px] text-[#787B86]">{STOCK_LIST.find(s=>s.symbol===selectedSymbol)?.name}</span>
              </div>
              
              <div className="flex items-center space-x-2 font-mono text-[13px]">
                <span>₹{quote.close.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                <span className={quote.change >= 0 ? 'text-[#26A69A]' : 'text-[#EF5350]'}>
                  {quote.change >= 0 ? '+' : ''}{quote.change.toFixed(2)}
                </span>
                <span className={quote.change >= 0 ? 'text-[#26A69A]' : 'text-[#EF5350]'}>
                  ({quote.change >= 0 ? '+' : ''}{quote.change_pct.toFixed(2)}%)
                </span>
              </div>

              <div className="flex items-center space-x-4 font-mono text-[11px] text-[#787B86]">
                <span>O: <span className="text-[#D1D4DC]">{quote.open.toFixed(2)}</span></span>
                <span>H: <span className="text-[#D1D4DC]">{quote.high.toFixed(2)}</span></span>
                <span>L: <span className="text-[#D1D4DC]">{quote.low.toFixed(2)}</span></span>
                <span>C: <span className="text-[#D1D4DC]">{quote.close.toFixed(2)}</span></span>
                <span>Vol: <span className="text-[#D1D4DC]">{(quote.volume / 100000).toFixed(2)}L</span></span>
              </div>
            </div>
          )}

          <div className="flex-1 overflow-y-auto overflow-x-hidden p-2">
            <CandlestickChart 
              data={chartData} 
              indicators={{
                showEMA20: indicators.showEMA,
                showEMA50: indicators.showEMA,
                showEMA200: indicators.showEMA,
                showBollinger: indicators.showBB,
                showVolume: indicators.showVOL
              }} 
            />
          </div>
        </div>

        {/* Pattern Panel right side */}
        <div className="w-[280px] flex-none bg-[#1E222D] border-l border-[#2A2E39] flex flex-col overflow-hidden shrink-0">
          <div className="p-4 flex-1 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-medium tracking-[0.08em] uppercase text-[#4C525E]">PATTERNS DETECTED</span>
              <span className="bg-[#1E2B4D] text-[#2962FF] rounded-[3px] text-[10px] px-1.5 py-[1px] font-mono">
                {patterns.length}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
              {patterns.length === 0 ? (
                <div className="text-[12px] text-[#787B86]">No patterns detected for {selectedSymbol}</div>
              ) : (
                <PatternPanel patterns={patterns} onPatternClick={setSelectedPattern} />
              )}
            </div>

            {/* Backtest summary footer */}
            <div className="mt-4 pt-4 border-t border-[#2A2E39]">
              <div className="text-[10px] font-medium tracking-[0.08em] uppercase text-[#4C525E] mb-3">BACKTEST SUMMARY</div>
              <div className="grid grid-cols-2 gap-y-3 gap-x-2 text-[11px]">
                <div className="text-[#787B86]">Avg Win Rate:</div>
                <div className="text-[#D1D4DC] font-mono text-right">{aggWinRate}%</div>
                <div className="text-[#787B86]">Exp. Return:</div>
                <div className={`font-mono text-right ${aggReturn >= 0 ? 'text-[#26A69A]' : 'text-[#EF5350]'}`}>
                  {aggReturn >= 0 ? '+' : ''}{aggReturn}%
                </div>
                <div className="text-[#787B86]">Signals (30d):</div>
                <div className="text-[#D1D4DC] font-mono text-right">3</div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Pattern Modal Overlay */}
      {selectedPattern && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 backdrop-blur-sm">
          <div className="bg-[#1E222D] border border-[#2A2E39] rounded-sm w-[480px] max-h-[80vh] overflow-y-auto flex flex-col relative shadow-2xl">
            <button 
              className="absolute top-4 right-4 text-[#787B86] hover:text-[#D1D4DC] text-lg leading-none"
              onClick={() => setSelectedPattern(null)}
            >
              &times;
            </button>
            <div className="p-6">
              <div className="flex items-center space-x-3 mb-1">
                <span className="text-[#D1D4DC] text-lg font-semibold">{selectedPattern.symbol}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-sm font-medium ${selectedPattern.direction === 'BULLISH' ? 'bg-[#26A69A1A] text-[#26A69A]' : 'bg-[#EF53501A] text-[#EF5350]'}`}>
                  {selectedPattern.direction === 'BULLISH' ? '▲ BULLISH' : '▼ BEARISH'}
                </span>
              </div>
              <div className="text-[#787B86] text-[13px] mb-6">{selectedPattern.pattern_type.replace(/_/g, ' ')} · Detected on {new Date(selectedPattern.detected_on).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year:'numeric'})}</div>

              <div className="text-[10px] font-medium tracking-[0.08em] uppercase text-[#4C525E] mb-2">AI ANALYSIS</div>
              <p className="text-[#D1D4DC] text-[13px] leading-relaxed mb-6">
                {selectedPattern.description}
              </p>

              <div className="text-[10px] font-medium tracking-[0.08em] uppercase text-[#4C525E] mb-2">KEY LEVELS</div>
              <div className="grid grid-cols-2 gap-3 mb-6 font-mono text-[12px]">
                <div className="flex justify-between bg-[#2A2E39] p-3 rounded-sm border border-[#363A45]">
                  <span className="text-[#26A69A]">Support</span>
                  <span className="text-[#D1D4DC]">₹{selectedPattern.key_levels.support.toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between bg-[#2A2E39] p-3 rounded-sm border border-[#363A45]">
                  <span className="text-[#EF5350]">Resistance</span>
                  <span className="text-[#D1D4DC]">₹{selectedPattern.key_levels.resistance.toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between bg-[#2A2E39] p-3 rounded-sm border border-[#363A45]">
                  <span className="text-[#2962FF]">Target</span>
                  <span className="text-[#D1D4DC]">₹{selectedPattern.key_levels.target.toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between bg-[#2A2E39] p-3 rounded-sm border border-[#363A45]">
                  <span className="text-[#EF5350]">Stop Loss</span>
                  <span className="text-[#D1D4DC]">₹{selectedPattern.key_levels.stop_loss.toLocaleString('en-IN')}</span>
                </div>
              </div>

              <div className="text-[10px] font-medium tracking-[0.08em] uppercase text-[#4C525E] mb-2">BACKTEST PERFORMANCE</div>
              <div className="grid grid-cols-2 gap-3 font-mono text-[12px]">
                <div className="bg-[#2A2E39] p-3 rounded-sm border border-[#363A45]">
                  <div className="text-[#787B86] text-[10px] mb-1">WIN RATE</div>
                  <div className="text-[#D1D4DC]">{Math.round(selectedPattern.backtest.win_rate * 100)}%</div>
                </div>
                <div className="bg-[#2A2E39] p-3 rounded-sm border border-[#363A45]">
                  <div className="text-[#787B86] text-[10px] mb-1">AVG RETURN</div>
                  <div className={selectedPattern.backtest.avg_return_pct > 0 ? 'text-[#26A69A]' : 'text-[#EF5350]'}>
                    {selectedPattern.backtest.avg_return_pct > 0 ? '+' : ''}{selectedPattern.backtest.avg_return_pct}%
                  </div>
                </div>
                <div className="bg-[#2A2E39] p-3 rounded-sm border border-[#363A45]">
                  <div className="text-[#787B86] text-[10px] mb-1">AVG DAYS TO TARGET</div>
                  <div className="text-[#D1D4DC]">{selectedPattern.backtest.avg_days}</div>
                </div>
                <div className="bg-[#2A2E39] p-3 rounded-sm border border-[#363A45]">
                  <div className="text-[#787B86] text-[10px] mb-1">SAMPLE SIZE</div>
                  <div className="text-[#D1D4DC]">{selectedPattern.backtest.sample_size} occurrences</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
