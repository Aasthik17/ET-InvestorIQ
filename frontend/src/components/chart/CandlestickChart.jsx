import React from 'react';
import {
  ResponsiveContainer, ComposedChart, LineChart, BarChart,
  CartesianGrid, XAxis, YAxis, Tooltip, Bar, Line, ReferenceLine
} from 'recharts';

const CandlestickBar = (props) => {
  const { x, y, width, payload, yAxis } = props
  if (!payload || !yAxis) return null

  const { open, high, low, close } = payload
  const isBull = close >= open
  const color  = isBull ? '#26A69A' : '#EF5350'

  // Convert price values to pixel positions using yAxis scale
  const yOpen  = yAxis.scale(open)
  const yClose = yAxis.scale(close)
  const yHigh  = yAxis.scale(high)
  const yLow   = yAxis.scale(low)

  const bodyTop    = Math.min(yOpen, yClose)
  const bodyBottom = Math.max(yOpen, yClose)
  const bodyHeight = Math.max(bodyBottom - bodyTop, 1)
  const centerX    = x + width / 2

  return (
    <g>
      {/* Upper wick */}
      <line
        x1={centerX} y1={yHigh}
        x2={centerX} y2={bodyTop}
        stroke="#787B86" strokeWidth={1}
      />
      {/* Lower wick */}
      <line
        x1={centerX} y1={bodyBottom}
        x2={centerX} y2={yLow}
        stroke="#787B86" strokeWidth={1}
      />
      {/* Candle body */}
      <rect
        x={x + 1}
        y={bodyTop}
        width={Math.max(width - 2, 1)}
        height={bodyHeight}
        fill={isBull ? '#26A69A' : '#EF5350'}
        stroke={color}
        strokeWidth={0.5}
      />
    </g>
  )
}

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isBull = data.close >= data.open;
    const color = isBull ? 'text-[#26A69A]' : 'text-[#EF5350]';
    
    const d = new Date(data.date);
    const dateStr = `${d.getDate().toString().padStart(2, '0')} ${d.toLocaleString('default', { month: 'short' })} ${d.getFullYear()}`;
    
    let volFormat = data.volume;
    if (volFormat >= 10000000) volFormat = (volFormat / 10000000).toFixed(2) + 'Cr';
    else if (volFormat >= 100000) volFormat = (volFormat / 100000).toFixed(2) + 'L';
    else if (volFormat >= 1000) volFormat = (volFormat / 1000).toFixed(1) + 'k';

    const change = data.close - data.open;
    const changeColor = change >= 0 ? 'text-[#26A69A]' : 'text-[#EF5350]';
    
    return (
      <div style={{
        position: 'absolute',
        background: '#2A2E39', 
        border: '1px solid #363A45', 
        borderRadius: '4px', 
        padding: '10px 14px', 
        fontSize: '12px',
        color: '#D1D4DC',
        zIndex: 100,
        pointerEvents: 'none'
      }}>
        <div style={{ color: '#787B86', marginBottom: '6px' }}>{dateStr}</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px', fontFamily: "'JetBrains Mono', monospace" }}>
          <div>O: {data.open.toFixed(2)}</div>
          <div>H: {data.high.toFixed(2)}</div>
          <div>L: {data.low.toFixed(2)}</div>
          <div>C: <span className={color}>{data.close.toFixed(2)}</span></div>
        </div>
        <div style={{ marginTop: '6px', fontFamily: "'JetBrains Mono', monospace" }}>Vol: {volFormat}</div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace" }}>Change: <span className={changeColor}>{change > 0 ? '+' : ''}{change.toFixed(2)}</span></div>
      </div>
    );
  }
  return null;
}

export default function CandlestickChart({ data, indicators = {} }) {
  const { 
    showEMA20 = true, 
    showEMA50 = true, 
    showEMA200 = true, 
    showBollinger = true, 
    showVolume = true 
  } = indicators;

  if (!data || data.length === 0) return null;

  const minLow = Math.min(...data.map(d => d.low));
  const maxHigh = Math.max(...data.map(d => d.high));
  const padding = (maxHigh - minLow) * 0.05;
  const yDomain = [minLow - padding, maxHigh + padding];
  
  const formatDate = (tick) => {
    const d = new Date(tick);
    return `${d.getDate().toString().padStart(2, '0')} ${d.toLocaleString('default', { month: 'short' })}`;
  };

  const xTicks = data.filter((_, i) => i % 20 === 0).map(d => d.date);

  const CustomVolBar = (props) => {
    const { x, y, width, height, payload } = props;
    if (!payload) return null;
    const isBull = payload.close >= payload.open;
    const fill = isBull ? '#26A69A33' : '#EF535033';
    const stroke = isBull ? '#26A69A' : '#EF5350';
    return <rect x={x} y={y} width={width} height={height} fill={fill} stroke={stroke} strokeWidth={0.5} />;
  }
  
  const CustomMacdBar = (props) => {
    const { x, y, width, height, payload } = props;
    if (!payload || payload.macdHist === undefined || payload.macdHist === null) return null;
    const isPos = payload.macdHist >= 0;
    const fill = isPos ? '#26A69A66' : '#EF535066';
    return <rect x={x} y={y} width={width} height={height} fill={fill} />;
  }

  return (
    <div className="flex flex-col w-full h-full space-y-1">
      {/* Main Chart */}
      <div className="relative w-full" style={{ height: 420 }}>
        <div className="absolute top-2 left-2 z-10 text-[10px] font-medium tracking-[0.06em] text-[#4C525E]">PRICE</div>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#1E222D" strokeDasharray="0" />
            <XAxis 
              dataKey="date" 
              ticks={xTicks} 
              tickFormatter={formatDate}
              tick={{ fill: '#4C525E', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              height={20}
            />
            <YAxis 
              domain={yDomain} 
              orientation="right"
              tickFormatter={(v) => `₹${v.toLocaleString('en-IN')}`}
              tick={{ fill: '#4C525E', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#363A45', strokeWidth: 1, strokeDasharray: '3 3' }} />
            
            <Bar dataKey="close" shape={<CandlestickBar />} isAnimationActive={false} />
            
            {showEMA20 && <Line type="monotone" dataKey="ema20" dot={false} stroke="#F59E0B" strokeWidth={1} isAnimationActive={false} />}
            {showEMA50 && <Line type="monotone" dataKey="ema50" dot={false} stroke="#2962FF" strokeWidth={1.5} isAnimationActive={false} />}
            {showEMA200 && <Line type="monotone" dataKey="ema200" dot={false} stroke="#8B5CF6" strokeWidth={1.5} isAnimationActive={false} />}
            
            {showBollinger && (
              <>
                <Line type="monotone" dataKey="bbUpper" stroke="#787B86" strokeWidth={0.5} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="bbMiddle" stroke="#787B86" strokeWidth={0.5} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="bbLower" stroke="#787B86" strokeWidth={0.5} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Volume Subchart */}
      {showVolume && (
        <div className="relative w-full" style={{ height: 80 }}>
          <div className="absolute top-1 left-2 z-10 text-[10px] font-medium tracking-[0.06em] text-[#4C525E]">VOLUME</div>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 60, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} horizontal={true} stroke="#1E222D" strokeDasharray="0" />
              <XAxis dataKey="date" hide={true} />
              <YAxis hide={true} domain={[0, 'dataMax']} />
              <Tooltip cursor={{ stroke: '#363A45', strokeWidth: 1, strokeDasharray: '3 3' }} content={() => null} />
              <ReferenceLine y={Math.max(...data.map(d=>d.volume))/2} stroke="#1E222D" />
              <Bar dataKey="volume" shape={<CustomVolBar />} isAnimationActive={false} />
              <Line type="monotone" dataKey="volumeMA" stroke="#787B86" strokeWidth={1} dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* RSI Subchart */}
      <div className="relative w-full" style={{ height: 80 }}>
        <div className="absolute top-1 left-2 z-10 text-[10px] font-medium tracking-[0.06em] text-[#4C525E]">RSI (14)</div>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
            <XAxis dataKey="date" hide={true} />
            <YAxis 
              domain={[0, 100]} 
              orientation="right"
              ticks={[30, 70]}
              tick={{ fill: '#4C525E', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip cursor={{ stroke: '#363A45', strokeWidth: 1, strokeDasharray: '3 3' }} content={() => null} />
            <ReferenceLine y={70} stroke="#EF535066" strokeDasharray="3 3" />
            <ReferenceLine y={50} stroke="#2A2E39" />
            <ReferenceLine y={30} stroke="#26A69A66" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="rsi" stroke="#2962FF" strokeWidth={1} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* MACD Subchart */}
      <div className="relative w-full" style={{ height: 80 }}>
        <div className="absolute top-1 left-2 z-10 text-[10px] font-medium tracking-[0.06em] text-[#4C525E]">MACD (12, 26, 9)</div>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 5, right: 60, left: 0, bottom: 0 }}>
            <XAxis dataKey="date" hide={true} />
            <YAxis hide={true} />
            <Tooltip cursor={{ stroke: '#363A45', strokeWidth: 1, strokeDasharray: '3 3' }} content={() => null} />
            <ReferenceLine y={0} stroke="#363A45" />
            <Bar dataKey="macdHist" shape={<CustomMacdBar />} isAnimationActive={false} />
            <Line type="monotone" dataKey="macdLine" stroke="#2962FF" strokeWidth={1} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="macdSig" stroke="#F59E0B" strokeWidth={1} dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
