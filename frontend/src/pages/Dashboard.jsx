/**
 * Dashboard — Main landing page with market overview.
 */
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { TrendingUp, TrendingDown, Activity, ArrowRight, Radar, BarChart2, MessageSquare, Video, RefreshCw } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from 'recharts'
import { useMarketOverview, useSectors } from '../hooks/useMarketData'
import { useSignals } from '../hooks/useSignals'
import LoadingSpinner from '../components/common/LoadingSpinner'
import SignalCard from '../components/common/SignalCard'

const MODULE_CARDS = [
  { to: '/radar', icon: Radar, title: 'Opportunity Radar', desc: 'Insider trades, bulk deals & FII signals', color: 'from-accent to-accent-light' },
  { to: '/charts', icon: BarChart2, title: 'Chart Intelligence', desc: 'AI-detected technical patterns', color: 'from-purple-600 to-purple-400' },
  { to: '/chat', icon: MessageSquare, title: 'Market Chat', desc: 'Portfolio-aware AI advisor', color: 'from-bull to-emerald-400' },
  { to: '/video', icon: Video, title: 'Video Engine', desc: 'AI-narrated market videos', color: 'from-gold to-yellow-400' },
]

function StatCard({ label, value, change, up }) {
  return (
    <div className="card">
      <div className="stat-label mb-1">{label}</div>
      <div className="flex items-end gap-2">
        <div className="text-2xl font-bold text-text-base">{value}</div>
        {change !== undefined && (
          <span className={`text-sm font-semibold mb-0.5 ${up ? 'text-bull' : 'text-bear'}`}>
            {up ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%
          </span>
        )}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: market, isLoading: marketLoading, refetch } = useMarketOverview()
  const { data: sectors } = useSectors()
  const { data: signalData } = useSignals({ page_size: 4 })

  const nifty = market?.nifty50 || {}
  const topGainers = market?.top_gainers?.slice(0, 5) || []
  const topLosers = market?.top_losers?.slice(0, 5) || []
  const signals = signalData?.signals || []

  // Build sector chart data
  const sectorChart = (Array.isArray(sectors) ? sectors : []).slice(0, 8).map(s => ({
    name: s.sector?.substring(0, 6),
    value: parseFloat(s.return_1d_pct || 0),
  }))

  return (
    <div className="p-4 lg:p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-base">Market Dashboard</h1>
          <p className="text-muted text-sm mt-0.5">NSE/BSE · Live Intelligence</p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary text-sm px-3 py-1.5">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Market indices */}
      {marketLoading ? (
        <div className="flex items-center justify-center h-24">
          <LoadingSpinner text="Loading market data..." />
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            label="NIFTY 50"
            value={nifty?.level?.toLocaleString('en-IN', { maximumFractionDigits: 0 }) || '—'}
            change={nifty?.change_pct}
            up={(nifty?.change_pct || 0) >= 0}
          />
          <StatCard
            label="SENSEX"
            value={(market?.sensex?.level || 73800).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            change={market?.sensex?.change_pct || 0.4}
            up={(market?.sensex?.change_pct || 0.4) >= 0}
          />
          <div className="card">
            <div className="stat-label mb-1">FII Net Today</div>
            <div className={`text-2xl font-bold ${(market?.fii_net_today || 0) >= 0 ? 'text-bull' : 'text-bear'}`}>
              ₹{Math.abs(market?.fii_net_today || 0).toLocaleString('en-IN')} Cr
            </div>
            <div className="text-xs text-muted mt-0.5">
              {(market?.fii_net_today || 0) >= 0 ? 'Inflow' : 'Outflow'}
            </div>
          </div>
          <div className="card">
            <div className="stat-label mb-1">India VIX</div>
            <div className={`text-2xl font-bold ${(market?.vix || 15) > 18 ? 'text-bear' : 'text-bull'}`}>
              {(market?.vix || 15).toFixed(1)}
            </div>
            <div className="text-xs text-muted mt-0.5">
              {(market?.vix || 15) > 18 ? 'High volatility' : 'Low volatility'}
            </div>
          </div>
        </div>
      )}

      {/* Gainers / Losers + Sector chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Top Gainers */}
        <div className="card">
          <div className="section-title flex items-center gap-2">
            <TrendingUp size={16} className="text-bull" />
            Top Gainers
          </div>
          <div className="space-y-2">
            {topGainers.map((s, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm font-semibold text-text-base">{s.symbol}</span>
                <span className="text-sm font-bold text-bull">+{(s.change_pct || 0).toFixed(2)}%</span>
              </div>
            ))}
            {topGainers.length === 0 && <div className="text-muted text-sm">Loading...</div>}
          </div>
        </div>

        {/* Top Losers */}
        <div className="card">
          <div className="section-title flex items-center gap-2">
            <TrendingDown size={16} className="text-bear" />
            Top Losers
          </div>
          <div className="space-y-2">
            {topLosers.map((s, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm font-semibold text-text-base">{s.symbol}</span>
                <span className="text-sm font-bold text-bear">{(s.change_pct || 0).toFixed(2)}%</span>
              </div>
            ))}
            {topLosers.length === 0 && <div className="text-muted text-sm">Loading...</div>}
          </div>
        </div>

        {/* Sector Performance */}
        <div className="card">
          <div className="section-title flex items-center gap-2">
            <Activity size={16} className="text-accent" />
            Sectors (1D)
          </div>
          {sectorChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={sectorChart} margin={{ left: -20 }}>
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#8B949E' }} />
                <YAxis tick={{ fontSize: 9, fill: '#8B949E' }} />
                <Tooltip
                  contentStyle={{ background: '#161B22', border: '1px solid #21262D', borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: '#E6EDF3' }}
                  formatter={(v) => [`${v.toFixed(2)}%`, 'Return']}
                />
                <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                  {sectorChart.map((entry, i) => (
                    <Cell key={i} fill={entry.value >= 0 ? '#00C896' : '#FF4757'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-32">
              <LoadingSpinner size="sm" />
            </div>
          )}
        </div>
      </div>

      {/* Module cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {MODULE_CARDS.map(({ to, icon: Icon, title, desc, color }) => (
          <motion.div key={to} whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
            <Link to={to} className="card card-hover block">
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center mb-3`}>
                <Icon size={18} className="text-white" />
              </div>
              <div className="text-sm font-bold text-text-base mb-1">{title}</div>
              <div className="text-xs text-muted leading-snug">{desc}</div>
              <div className="flex items-center gap-1 mt-3 text-xs text-accent font-medium">
                Open <ArrowRight size={10} />
              </div>
            </Link>
          </motion.div>
        ))}
      </div>

      {/* Live Signals Preview */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="section-title mb-0 flex items-center gap-2">
            <Radar size={16} className="text-accent" />
            Latest Signals
          </h2>
          <Link to="/radar" className="text-xs text-accent hover:text-accent-light flex items-center gap-1">
            View all <ArrowRight size={10} />
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {signals.slice(0, 4).map((signal, i) => (
            <SignalCard key={signal.id} signal={signal} index={i} />
          ))}
          {signals.length === 0 && (
            <div className="col-span-2 flex justify-center py-8">
              <LoadingSpinner text="Loading signals..." />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
