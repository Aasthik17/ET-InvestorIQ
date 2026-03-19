/**
 * OpportunityRadar — Signal discovery and insider intelligence page.
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, Filter, X, TrendingUp, TrendingDown, Users, Activity } from 'lucide-react'
import { useSignals, useRefreshSignals, useInsiderTrades, useFiiDii, useRadarSummary } from '../hooks/useSignals'
import SignalCard from '../components/common/SignalCard'
import LoadingSpinner from '../components/common/LoadingSpinner'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, CartesianGrid, Legend
} from 'recharts'

const FILTER_OPTIONS = ['All', 'BULLISH', 'BEARISH', 'NEUTRAL']
const TYPE_FILTERS = ['All', 'INSIDER_TRADE', 'BULK_DEAL', 'FILING', 'FII_ACCUMULATION', 'CORPORATE_ACTION']

function SignalDetailModal({ signal, onClose }) {
  if (!signal) return null
  const isBull = signal.expected_impact === 'BULLISH'
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
        className="card max-w-2xl w-full max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl font-bold text-text-base">{signal.symbol}</span>
              <span className={`badge ${isBull ? 'badge-bull' : 'badge-bear'}`}>{signal.expected_impact}</span>
            </div>
            <p className="text-muted text-sm">{signal.signal_date}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-border transition-colors">
            <X size={18} className="text-muted" />
          </button>
        </div>

        <h3 className="text-base font-semibold text-text-base mb-3 leading-snug">{signal.headline}</h3>
        <p className="text-sm text-muted mb-4 leading-relaxed">{signal.detail}</p>

        {signal.ai_analysis && (
          <div className={`p-4 rounded-xl mb-4 ${isBull ? 'bg-bull/8 border border-bull/20' : 'bg-bear/8 border border-bear/20'}`}>
            <div className="text-xs font-bold text-muted uppercase tracking-wider mb-2">🤖 AI Analysis</div>
            <p className="text-sm text-text-base leading-relaxed">{signal.ai_analysis}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="card-hover p-3">
            <div className="text-muted text-xs mb-1">Confidence</div>
            <div className="text-xl font-bold text-text-base">{Math.round((signal.confidence_score || 0) * 100)}%</div>
          </div>
          <div className="card-hover p-3">
            <div className="text-muted text-xs mb-1">Price at Signal</div>
            <div className="text-xl font-bold text-text-base">₹{(signal.stock_price_at_signal || 0).toLocaleString('en-IN')}</div>
          </div>
        </div>

        {signal.tags && (
          <div className="flex flex-wrap gap-1.5 mt-4">
            {signal.tags.map(tag => (
              <span key={tag} className="badge badge-neutral">{tag}</span>
            ))}
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}

export default function OpportunityRadar() {
  const [direction, setDirection] = useState('All')
  const [signalType, setSignalType] = useState('All')
  const [selected, setSelected] = useState(null)
  const [activeTab, setActiveTab] = useState('signals')

  const filters = {
    direction: direction !== 'All' ? direction : undefined,
    signal_types: signalType !== 'All' ? signalType : undefined,
  }

  const { data: signalData, isLoading } = useSignals(filters)
  const { data: summary } = useRadarSummary()
  const { data: fiiData } = useFiiDii(30)
  const refreshMutation = useRefreshSignals()

  const signals = signalData?.signals || []
  const bullish = signals.filter(s => s.expected_impact === 'BULLISH').length
  const bearish = signals.filter(s => s.expected_impact === 'BEARISH').length

  // FII chart
  const fiiChart = Array.isArray(fiiData) ? fiiData.slice(-14).map(d => ({
    date: d.date?.slice(5),
    FII: parseFloat(d.fii_net || 0),
    DII: parseFloat(d.dii_net || 0),
  })) : []

  return (
    <div className="p-4 lg:p-6 space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-base">Opportunity Radar</h1>
          <p className="text-muted text-sm mt-0.5">
            {signals.length} signals · {bullish} bullish · {bearish} bearish
          </p>
        </div>
        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="btn-primary text-sm"
        >
          <RefreshCw size={14} className={refreshMutation.isPending ? 'animate-spin' : ''} />
          {refreshMutation.isPending ? 'Scanning...' : 'Refresh'}
        </button>
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="card">
            <div className="stat-label mb-1">Insider Buys</div>
            <div className="text-2xl font-bold text-bull">{summary.total_buys}</div>
          </div>
          <div className="card">
            <div className="stat-label mb-1">Insider Sells</div>
            <div className="text-2xl font-bold text-bear">{summary.total_sells}</div>
          </div>
          <div className="card">
            <div className="stat-label mb-1">Buy Value</div>
            <div className="text-xl font-bold text-bull">₹{(summary.total_buy_value_cr || 0).toFixed(0)} Cr</div>
          </div>
          <div className="card">
            <div className="stat-label mb-1">Net Sentiment</div>
            <div className={`text-xl font-bold ${summary.net_sentiment === 'BULLISH' ? 'text-bull' : summary.net_sentiment === 'BEARISH' ? 'text-bear' : 'text-muted'}`}>
              {summary.net_sentiment}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border pb-0">
        {[['signals', 'Signals'], ['fii', 'FII/DII Flow'], ['insider', 'Insiders']].map(([tab, label]) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px
              ${activeTab === tab ? 'border-accent text-accent' : 'border-transparent text-muted hover:text-text-base'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Signals Tab */}
      {activeTab === 'signals' && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <Filter size={14} className="text-muted self-center" />
            <div className="flex gap-1.5 flex-wrap">
              {FILTER_OPTIONS.map(f => (
                <button
                  key={f}
                  onClick={() => setDirection(f)}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors
                    ${direction === f
                      ? f === 'BULLISH' ? 'bg-bull text-black' : f === 'BEARISH' ? 'bg-bear text-white' : 'bg-accent text-white'
                      : 'bg-card border border-border text-muted hover:text-text-base'
                    }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Signal grid */}
          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner text="Scanning market signals..." />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {signals.map((signal, i) => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  index={i}
                  onClick={() => setSelected(signal)}
                />
              ))}
              {signals.length === 0 && (
                <div className="col-span-3 text-center py-12 text-muted">No signals found for selected filters.</div>
              )}
            </div>
          )}
        </>
      )}

      {/* FII/DII Tab */}
      {activeTab === 'fii' && (
        <div className="card">
          <div className="section-title">FII/DII Net Flow — Last 14 Trading Days (₹ Cr)</div>
          {fiiChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={fiiChart}>
                <CartesianGrid stroke="#21262D" strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#8B949E' }} />
                <YAxis tick={{ fontSize: 10, fill: '#8B949E' }} />
                <Tooltip
                  contentStyle={{ background: '#161B22', border: '1px solid #21262D', borderRadius: 8 }}
                  formatter={(v) => [`₹${v.toFixed(0)} Cr`, '']}
                />
                <Legend />
                <Bar dataKey="FII" fill="#00C896" radius={[3, 3, 0, 0]} />
                <Bar dataKey="DII" fill="#0066FF" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex justify-center py-12"><LoadingSpinner /></div>
          )}
        </div>
      )}

      {/* Insider Tab */}
      {activeTab === 'insider' && (
        <InsiderTab />
      )}

      {/* Detail Modal */}
      <AnimatePresence>
        {selected && <SignalDetailModal signal={selected} onClose={() => setSelected(null)} />}
      </AnimatePresence>
    </div>
  )
}

function InsiderTab() {
  const { data: trades, isLoading } = useInsiderTrades()
  if (isLoading) return <div className="flex justify-center py-12"><LoadingSpinner /></div>
  const tradeList = Array.isArray(trades) ? trades : []
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-muted">
            <th className="text-left pb-2 font-medium">Date</th>
            <th className="text-left pb-2 font-medium">Symbol</th>
            <th className="text-left pb-2 font-medium">Person</th>
            <th className="text-left pb-2 font-medium">Category</th>
            <th className="text-left pb-2 font-medium">Type</th>
            <th className="text-right pb-2 font-medium">Value (₹ Cr)</th>
          </tr>
        </thead>
        <tbody>
          {tradeList.map((trade, i) => (
            <tr key={i} className="border-b border-border/40 hover:bg-surface/50 transition-colors">
              <td className="py-2 text-muted">{trade.date || trade.acq_from_date || '—'}</td>
              <td className="py-2 font-semibold text-text-base">{trade.stock_name || trade.symbol || '—'}</td>
              <td className="py-2 text-muted">{trade.person_name || '—'}</td>
              <td className="py-2"><span className="badge badge-neutral">{trade.category || '—'}</span></td>
              <td className="py-2">
                <span className={`badge ${trade.trade_type === 'Buy' ? 'badge-bull' : 'badge-bear'}`}>
                  {trade.trade_type || '—'}
                </span>
              </td>
              <td className="py-2 text-right font-semibold">
                {trade.value_cr ? `₹${parseFloat(trade.value_cr).toFixed(2)}` : '—'}
              </td>
            </tr>
          ))}
          {tradeList.length === 0 && (
            <tr><td colSpan={6} className="py-8 text-center text-muted">No insider trades found.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
