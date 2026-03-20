/**
 * SignalRow — Row-based signal display (Bloomberg/terminal style).
 * Replaces the old SignalCard. Accordion expand in-place.
 * Uses a 3px left border for severity, NOT a colored badge background.
 */
import { useState } from 'react'
import { ChevronRight } from 'lucide-react'
import ConfidenceMeter from './ConfidenceMeter'

const TYPE_BADGE = {
  INSIDER_TRADE:      { label: 'Insider',   cls: 'badge-insider' },
  BULK_DEAL:          { label: 'Bulk Deal', cls: 'badge-neutral' },
  BLOCK_DEAL:         { label: 'Block',     cls: 'badge-neutral' },
  FILING:             { label: 'Filing',    cls: 'badge-filing' },
  FII_ACCUMULATION:   { label: 'FII Flow',  cls: 'badge-fii' },
  DII_ACCUMULATION:   { label: 'DII Flow',  cls: 'badge-fii' },
  TECHNICAL:          { label: 'Technical', cls: 'badge-technical' },
  CORPORATE_ACTION:   { label: 'Corp Action', cls: 'badge-corporate' },
}

function fmt(ts) {
  try {
    const d = new Date(ts)
    const diff = (Date.now() - d.getTime()) / 1000
    if (diff < 3600)  return `${Math.round(diff / 60)}m ago`
    if (diff < 86400) return `${Math.round(diff / 3600)}h ago`
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
  } catch { return '—' }
}

export default function SignalRow({ signal }) {
  const [expanded, setExpanded] = useState(false)
  const dir = (signal.direction || '').toUpperCase()
  const isBull = dir === 'BULLISH' || dir === 'BUY'
  const isBear = dir === 'BEARISH' || dir === 'SELL'
  const dirClass = isBull ? 'bull' : isBear ? 'bear' : 'neutral'
  const badge = TYPE_BADGE[signal.signal_type] || { label: signal.signal_type, cls: 'badge-neutral' }

  return (
    <>
      {/* ── Main row ─────────────────────────────────────────────────── */}
      <div
        className={`signal-row ${dirClass}`}
        onClick={() => setExpanded(e => !e)}
        role="button"
        aria-expanded={expanded}
      >
        {/* Col 1 — Symbol + price */}
        <div style={{ width: '80px', flexShrink: 0 }}>
          <div className="price" style={{ fontSize: '13px', fontWeight: 600, color: '#D1D4DC' }}>
            {(signal.symbol || '').replace('.NS', '').replace('.BO', '')}
          </div>
          {signal.current_price && (
            <div className="price text-xs" style={{ color: '#787B86' }}>
              ₹{signal.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          )}
        </div>

        {/* Col 2 — Type badge */}
        <div style={{ width: '90px', flexShrink: 0, paddingRight: '8px' }}>
          <span className={`badge ${badge.cls}`}>{badge.label}</span>
        </div>

        {/* Col 3 — Headline + detail */}
        <div style={{ flex: 1, minWidth: 0, paddingRight: '12px' }}>
          <div style={{
            fontSize: '13px', color: '#D1D4DC', overflow: 'hidden',
            textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {signal.headline || signal.title || `${badge.label} signal detected`}
          </div>
          {signal.detail && (
            <div className="text-xs" style={{ color: '#787B86', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {signal.detail}
            </div>
          )}
        </div>

        {/* Col 4 — Confidence meter */}
        <div style={{ flexShrink: 0, marginRight: '16px' }}>
          <ConfidenceMeter score={signal.confidence_score ?? 0} width={60} />
        </div>

        {/* Col 5 — Timestamp */}
        <div style={{ width: '64px', flexShrink: 0, textAlign: 'right' }}>
          <span className="text-xs" style={{ color: '#4C525E' }}>{fmt(signal.detected_at)}</span>
        </div>

        {/* Col 6 — Chevron */}
        <div style={{ width: '24px', flexShrink: 0, display: 'flex', justifyContent: 'flex-end' }}>
          <ChevronRight
            size={14}
            style={{
              color: '#4C525E',
              transform: expanded ? 'rotate(90deg)' : 'none',
              transition: 'transform 150ms',
            }}
          />
        </div>
      </div>

      {/* ── Expanded AI analysis ────────────────────────────────────── */}
      {expanded && (
        <div className="signal-row-expanded" style={{ borderLeftColor: isBull ? '#26A69A' : isBear ? '#EF5350' : '#4C525E' }}>
          {signal.ai_analysis ? (
            <p style={{ fontSize: '12px', color: '#787B86', lineHeight: '1.6', margin: 0 }}>
              {signal.ai_analysis}
            </p>
          ) : (
            <p className="text-xs" style={{ color: '#4C525E', fontStyle: 'italic' }}>
              AI analysis not available. Run a refresh to generate.
            </p>
          )}
          {/* Sources */}
          {signal.sources?.length > 0 && (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '8px' }}>
              {signal.sources.map((s, i) => (
                <span key={i} className="btn-secondary" style={{ height: '20px', fontSize: '11px', cursor: 'default' }}>
                  {s.name || s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  )
}
