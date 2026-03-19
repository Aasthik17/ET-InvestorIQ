/**
 * Navbar — Top navigation bar with market ticker and status.
 */
import { NavLink } from 'react-router-dom'
import { Activity, Bell, RefreshCw } from 'lucide-react'
import { useMarketOverview } from '../../hooks/useMarketData'

export default function Navbar() {
  const { data: market, isLoading } = useMarketOverview()

  const nifty = market?.nifty50 || {}
  const niftyUp = (nifty?.change_pct || 0) >= 0

  return (
    <header className="h-14 bg-card border-b border-border flex items-center px-4 gap-4 z-10 flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 mr-4">
        <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
          <Activity size={16} className="text-white" />
        </div>
        <div className="hidden sm:block">
          <div className="text-xs font-bold text-accent tracking-wider">ET</div>
          <div className="text-xs text-muted leading-none">InvestorIQ</div>
        </div>
      </div>

      {/* Market ticker */}
      <div className="flex-1 overflow-hidden">
        {!isLoading && market && (
          <div className="flex items-center gap-6 text-sm">
            <span className="flex items-center gap-1.5">
              <span className="text-muted font-medium">NIFTY</span>
              <span className="font-bold text-text-base">
                {nifty?.level?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
              <span className={`text-xs font-semibold ${niftyUp ? 'text-bull' : 'text-bear'}`}>
                {niftyUp ? '▲' : '▼'} {Math.abs(nifty?.change_pct || 0).toFixed(2)}%
              </span>
            </span>
            <span className="hidden md:flex items-center gap-1.5">
              <span className="text-muted font-medium">SENSEX</span>
              <span className="font-bold text-text-base">
                {(market?.sensex?.level || 73800).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
              <span className={`text-xs font-semibold ${(market?.sensex?.change_pct || 0) >= 0 ? 'text-bull' : 'text-bear'}`}>
                {(market?.sensex?.change_pct || 0) >= 0 ? '▲' : '▼'} {Math.abs(market?.sensex?.change_pct || 0).toFixed(2)}%
              </span>
            </span>
            <span className={`hidden lg:flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full font-bold
              ${market?.sentiment === 'BULLISH' ? 'bg-bull/15 text-bull' : market?.sentiment === 'BEARISH' ? 'bg-bear/15 text-bear' : 'bg-muted/15 text-muted'}`}>
              {market?.sentiment}
            </span>
          </div>
        )}
        {isLoading && (
          <div className="flex gap-2 items-center text-muted text-xs">
            <RefreshCw size={12} className="animate-spin" />
            Loading market data...
          </div>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <div className="w-2 h-2 rounded-full bg-bull animate-pulse" />
          <span className="hidden sm:block">Live</span>
        </div>
        <button className="relative p-2 rounded-lg hover:bg-border transition-colors" aria-label="Notifications">
          <Bell size={16} className="text-muted" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-bear" />
        </button>
      </div>
    </header>
  )
}
