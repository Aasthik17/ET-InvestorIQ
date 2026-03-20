/**
 * OpportunityRadar — Bloomberg-style signal terminal.
 * Left: filter panel. Right: row-based signal feed with accordion expand.
 */
import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, SlidersHorizontal } from 'lucide-react'
import { radarAPI } from '../services/api'
import SignalRow from '../components/common/SignalRow'
import LoadingSpinner from '../components/common/LoadingSpinner'

const SIGNAL_TYPES = [
  { key: 'INSIDER_TRADE',    label: 'Insider Trade',     color: '#F59E0B' },
  { key: 'BULK_DEAL',        label: 'Bulk Deal',         color: '#787B86' },
  { key: 'FII_ACCUMULATION', label: 'FII / DII Flow',    color: '#10B981' },
  { key: 'FILING',           label: 'Corporate Filing',  color: '#8B5CF6' },
  { key: 'TECHNICAL',        label: 'Technical Signal',  color: '#06B6D4' },
]

const FEED_COLS = ['SYMBOL', 'TYPE', 'SIGNAL', 'CONFIDENCE', 'TIME', '']

export default function OpportunityRadar() {
  const qc = useQueryClient()
  const [direction, setDirection] = useState('ALL')
  const [minConf, setMinConf] = useState(0)
  const [enabledTypes, setEnabledTypes] = useState(new Set(SIGNAL_TYPES.map(t => t.key)))

  const { data: raw, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ['radar', 'signals'],
    queryFn: () => radarAPI.signals({ limit: 50 }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const refreshMutation = useMutation({
    mutationFn: radarAPI.refresh,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['radar', 'signals'] }),
  })

  const signals = useMemo(() => {
    const all = Array.isArray(raw) ? raw : raw?.signals || []
    return all.filter(s => {
      const dir = (s.direction || '').toUpperCase()
      if (direction === 'BULLISH' && !['BULLISH', 'BUY'].includes(dir)) return false
      if (direction === 'BEARISH' && !['BEARISH', 'SELL'].includes(dir)) return false
      if (!enabledTypes.has(s.signal_type)) return false
      if ((s.confidence_score ?? 0) * 100 < minConf) return false
      return true
    })
  }, [raw, direction, minConf, enabledTypes])

  const bullCount    = signals.filter(s => ['BULLISH','BUY'].includes((s.direction||'').toUpperCase())).length
  const bearCount    = signals.filter(s => ['BEARISH','SELL'].includes((s.direction||'').toUpperCase())).length
  const neutralCount = signals.length - bullCount - bearCount

  const lastUpdate = dataUpdatedAt
    ? (() => { const s = Math.round((Date.now() - dataUpdatedAt) / 1000); return s < 60 ? 'Just now' : `${Math.round(s/60)}m ago` })()
    : '—'

  const toggleType = key => {
    setEnabledTypes(prev => {
      const n = new Set(prev)
      n.has(key) ? n.delete(key) : n.add(key)
      return n
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Stats bar ──────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        height: '44px',
        background: '#1E222D',
        borderBottom: '1px solid #2A2E39',
        padding: '0 16px',
        gap: '24px',
        flexShrink: 0,
      }}>
        {[
          { label: 'Signals Scanned', val: (Array.isArray(raw) ? raw.length : raw?.total || 0) + ' scanned' },
          { label: 'Actionable Today', val: `${signals.length} signals` },
          { label: 'Direction',        val: <><span className="bull">{bullCount} Bull</span> · <span className="bear">{bearCount} Bear</span> · <span style={{color:'#787B86'}}>{neutralCount} Neutral</span></> },
          { label: 'Updated',          val: lastUpdate },
        ].map(({ label, val }, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '1px', borderRight: i < 3 ? '1px solid #2A2E39' : 'none', paddingRight: i < 3 ? '24px' : 0 }}>
            <span className="label">{label}</span>
            {typeof val === 'string' || typeof val === 'number'
              ? <span className="price text-xs" style={{ color: '#D1D4DC' }}>{val}</span>
              : <span className="text-xs" style={{ color: '#D1D4DC' }}>{val}</span>
            }
          </div>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
          <button
            className="btn-secondary"
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending || isFetching}
          >
            <RefreshCw size={12} style={{ animation: (refreshMutation.isPending || isFetching) ? 'spin 0.8s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Main: filter panel + feed ─────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Filter panel — 264px */}
        <div style={{
          width: '264px', minWidth: '264px',
          background: '#1E222D',
          borderRight: '1px solid #2A2E39',
          overflow: 'auto',
          flexShrink: 0,
        }}>
          <div style={{ padding: '12px' }}>

            {/* Signal Type */}
            <div className="label" style={{ marginBottom: '8px' }}>Signal Type</div>
            {SIGNAL_TYPES.map(t => (
              <label key={t.key} style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                height: '28px', cursor: 'pointer',
              }}>
                <input
                  type="checkbox"
                  checked={enabledTypes.has(t.key)}
                  onChange={() => toggleType(t.key)}
                  style={{ accentColor: '#2962FF', width: '13px', height: '13px' }}
                />
                <span className="text-xs" style={{ color: enabledTypes.has(t.key) ? '#D1D4DC' : '#787B86' }}>
                  {t.label}
                </span>
              </label>
            ))}

            <div className="divider-h" style={{ margin: '12px 0' }} />

            {/* Direction */}
            <div className="label" style={{ marginBottom: '8px' }}>Direction</div>
            <div className="toggle-group">
              {['ALL', 'BULLISH', 'BEARISH'].map(d => (
                <button
                  key={d}
                  className={`toggle-btn${direction === d ? ' active' : ''}`}
                  onClick={() => setDirection(d)}
                  style={{ fontSize: '11px' }}
                >
                  {d === 'BULLISH' ? '▲ Bull' : d === 'BEARISH' ? '▼ Bear' : 'All'}
                </button>
              ))}
            </div>

            <div className="divider-h" style={{ margin: '12px 0' }} />

            {/* Min confidence */}
            <div className="label" style={{ marginBottom: '8px' }}>
              Min Confidence <span className="price" style={{ color: '#D1D4DC', marginLeft: '4px' }}>≥ {minConf}%</span>
            </div>
            <input
              type="range" min={0} max={90} step={5} value={minConf}
              onChange={e => setMinConf(+e.target.value)}
              style={{ width: '100%', accentColor: '#2962FF', margin: 0 }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-xs" style={{ color: '#4C525E' }}>0%</span>
              <span className="text-xs" style={{ color: '#4C525E' }}>90%</span>
            </div>
          </div>
        </div>

        {/* Signal feed — right panel */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Feed header */}
          <div style={{
            display: 'flex',
            height: '32px',
            background: '#1E222D',
            borderBottom: '1px solid #2A2E39',
            alignItems: 'center',
            padding: '0 12px',
            flexShrink: 0,
          }}>
            {[
              { label: 'SYMBOL', w: '80px' },
              { label: 'TYPE',   w: '90px' },
              { label: 'SIGNAL', flex: 1 },
              { label: 'CONFIDENCE', w: '80px' },
              { label: 'TIME',  w: '64px', right: true },
              { label: '',      w: '24px' },
            ].map((col, i) => (
              <div
                key={i}
                className="label"
                style={{
                  width: col.w,
                  flex: col.flex,
                  textAlign: col.right ? 'right' : 'left',
                  flexShrink: 0,
                  paddingRight: col.flex ? '12px' : 0,
                }}
              >
                {col.label}
              </div>
            ))}
          </div>

          {/* Rows */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {isFetching && signals.length === 0 ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '32px' }}>
                <LoadingSpinner size={18} text="Loading signals..." />
              </div>
            ) : signals.length === 0 ? (
              <div style={{ padding: '32px 16px', textAlign: 'center' }}>
                <SlidersHorizontal size={20} style={{ color: '#4C525E', margin: '0 auto 8px' }} />
                <div className="text-xs" style={{ color: '#4C525E' }}>No signals match your filters</div>
              </div>
            ) : (
              signals.map((s, i) => <SignalRow key={s.signal_id || i} signal={s} />)
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
