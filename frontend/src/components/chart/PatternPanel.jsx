import React, { useState } from 'react';

export default function PatternPanel({ patterns, onPatternClick }) {
  if (!patterns || patterns.length === 0) return null;

  return (
    <div className="flex flex-col space-y-4 pr-2">
      {patterns.map(pattern => {
        const isBull = pattern.direction === 'BULLISH';
        const borderColor = isBull ? 'border-l-[#26A69A]' : 'border-l-[#EF5350]';
        const badgeBg = isBull ? 'bg-[#26A69A1A]' : 'bg-[#EF53501A]';
        const badgeText = isBull ? 'text-[#26A69A]' : 'text-[#EF5350]';
        const badgeStr = isBull ? '▲ BULLISH' : '▼ BEARISH';
        
        // Confidence bar logic
        let confColor = '#EF5350';
        if (pattern.confidence > 0.7) confColor = '#26A69A';
        else if (pattern.confidence > 0.5) confColor = '#F59E0B';
        
        return (
          <div key={pattern.id} className={`flex flex-col p-3 bg-[#1E222D] border border-transparent border-l-2 ${borderColor} border-opacity-100 rounded-sm hover:bg-[#2A2E39] hover:border-[#363A45] transition-colors`}>
            
            <div className="flex items-center justify-between mb-2">
              <span className="text-[#D1D4DC] text-sm font-medium">{pattern.pattern_type.replace(/_/g, ' ')}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-sm ${badgeBg} ${badgeText}`}>
                {badgeStr}
              </span>
            </div>
            
            <div className="flex items-center space-x-2 mb-2">
              <div className="h-[3px] flex-1 bg-[#2A2E39] rounded-full overflow-hidden">
                <div className="h-full" style={{ width: `${Math.round(pattern.confidence * 100)}%`, backgroundColor: confColor }} />
              </div>
              <span className="text-[#D1D4DC] font-mono text-[11px]">{Math.round(pattern.confidence * 100)}%</span>
            </div>
            
            <div className="text-[11px] text-[#787B86] mb-3">
              Win rate: {Math.round(pattern.backtest.win_rate * 100)}% · Avg {pattern.backtest.avg_return_pct > 0 ? '+' : ''}{pattern.backtest.avg_return_pct}% · {pattern.backtest.sample_size} trades
            </div>
            
            <div className="text-[#787B86] text-xs leading-5 line-clamp-2 mb-3">
              {pattern.description}
            </div>
            
            <div className="text-[11px] text-[#D1D4DC] font-mono mb-3 bg-[#2A2E39] p-2 rounded-sm grid grid-cols-2 gap-2">
              <div><span className="text-[#4C525E]">SUP </span>₹{pattern.key_levels.support.toLocaleString('en-IN')}</div>
              <div><span className="text-[#4C525E]">RES </span>₹{pattern.key_levels.resistance.toLocaleString('en-IN')}</div>
              <div><span className="text-[#4C525E]">TGT </span>₹{pattern.key_levels.target.toLocaleString('en-IN')}</div>
              <div><span className="text-[#4C525E]">STP </span>₹{pattern.key_levels.stop_loss.toLocaleString('en-IN')}</div>
            </div>
            
            <button 
              className="text-[#2962FF] text-[11px] font-medium hover:text-[#507CFF] text-left transition-colors"
              onClick={() => onPatternClick(pattern)}
            >
              View Analysis
            </button>
            
          </div>
        )
      })}
    </div>
  )
}
