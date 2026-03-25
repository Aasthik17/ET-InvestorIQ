/**
 * VideoEngine — Content studio: config left, preview right.
 * Agent trace replaces the old job polling flow.
 */
import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import AgentTracePanel from '../components/agent/AgentTracePanel'
import Logo from '../components/layout/Logo'

const VIDEO_TYPES = [
  { type: 'MARKET_WRAP', label: 'Market Wrap (Daily)', desc: 'End-of-day summary with top movers' },
  { type: 'SECTOR_ROTATION', label: 'Sector Rotation', desc: 'Sector performance heatmap + flow' },
  { type: 'FII_DII_FLOW', label: 'FII / DII Flow', desc: 'Institutional money movement chart' },
  { type: 'BAR_RACE', label: 'Bar Race Chart', desc: 'Animated stock performance race' },
  { type: 'IPO_TRACKER', label: 'IPO Tracker', desc: 'Upcoming IPO pipeline overview' },
  { type: 'STOCK_DEEP_DIVE', label: 'Stock Deep Dive', desc: 'Full fundamental + technical analysis' },
]

const DATE_RANGES = ['1W', '1M', '3M']
const DURATIONS = ['30s', '60s', '90s']
const NSE_SYMBOLS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'BAJFINANCE', 'SBIN', 'ITC', 'TATAMOTORS', 'SUNPHARMA']

export default function VideoEngine() {
  const [selectedVideoType, setSelectedVideoType] = useState('MARKET_WRAP')
  const [dateRange, setDateRange] = useState('1M')
  const [duration, setDuration] = useState('60s')
  const [symbols, setSymbols] = useState(['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK'])
  const [portfolio] = useState({
    holdings: [],
    risk_profile: 'MODERATE',
  })
  const [scriptOpen, setScriptOpen] = useState(false)
  const [videoUrl, setVideoUrl] = useState('')
  const [narration, setNarration] = useState('')
  const [mediaKind, setMediaKind] = useState('video')

  const typeInfo = VIDEO_TYPES.find(t => t.type === selectedVideoType) || VIDEO_TYPES[0]
  const isRace = selectedVideoType === 'BAR_RACE'

  useEffect(() => {
    setVideoUrl('')
    setNarration('')
    setScriptOpen(false)
    setMediaKind('video')
  }, [selectedVideoType])

  const toggleSymbol = sym => {
    setSymbols(prev => (prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym].slice(0, 8)))
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{
        width: '360px',
        minWidth: '360px',
        background: '#1E222D',
        borderRight: '1px solid #2A2E39',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'auto',
        flexShrink: 0,
      }}>
        <div className="panel-header">
          <span className="label">Video Type</span>
        </div>

        {VIDEO_TYPES.map(vt => {
          const active = selectedVideoType === vt.type
          return (
            <div
              key={vt.type}
              onClick={() => setSelectedVideoType(vt.type)}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                padding: '8px 12px',
                cursor: 'pointer',
                borderLeft: `2px solid ${active ? '#2962FF' : 'transparent'}`,
                background: active ? '#1E2B4D' : 'transparent',
                borderBottom: '1px solid #1E222D',
                transition: 'background 100ms',
              }}
            >
              <div style={{
                width: '14px',
                height: '14px',
                borderRadius: '50%',
                flexShrink: 0,
                marginTop: '2px',
                border: `2px solid ${active ? '#2962FF' : '#4C525E'}`,
                background: active ? '#2962FF' : 'transparent',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                {active && <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#131722' }} />}
              </div>
              <div>
                <div style={{ fontSize: '13px', color: active ? '#D1D4DC' : '#787B86', fontWeight: active ? 500 : 400 }}>
                  {vt.label}
                </div>
                <div className="text-xs" style={{ color: '#4C525E' }}>{vt.desc}</div>
              </div>
            </div>
          )
        })}

        <div className="divider-h" style={{ margin: '8px 0' }} />

        <div style={{ padding: '0 12px 12px' }}>
          <div className="label" style={{ marginBottom: '6px' }}>Date Range</div>
          <div className="toggle-group" style={{ marginBottom: '12px' }}>
            {DATE_RANGES.map(d => (
              <button
                key={d}
                className={`toggle-btn${dateRange === d ? ' active' : ''}`}
                onClick={() => setDateRange(d)}
                style={{ flex: 1, fontSize: '11px' }}
              >
                {d}
              </button>
            ))}
          </div>

          <div className="label" style={{ marginBottom: '6px' }}>Duration</div>
          <div className="toggle-group" style={{ marginBottom: '12px' }}>
            {DURATIONS.map(d => (
              <button
                key={d}
                className={`toggle-btn${duration === d ? ' active' : ''}`}
                onClick={() => setDuration(d)}
                style={{ flex: 1, fontSize: '11px' }}
              >
                {d}
              </button>
            ))}
          </div>

          {isRace && (
            <>
              <div className="label" style={{ marginBottom: '6px' }}>Stocks to Race ({symbols.length}/8)</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '12px' }}>
                {NSE_SYMBOLS.map(s => (
                  <button
                    key={s}
                    onClick={() => toggleSymbol(s)}
                    style={{
                      height: '22px',
                      padding: '0 7px',
                      fontSize: '11px',
                      fontFamily: "'JetBrains Mono', monospace",
                      background: symbols.includes(s) ? '#1E2B4D' : 'transparent',
                      color: symbols.includes(s) ? '#2962FF' : '#787B86',
                      border: `1px solid ${symbols.includes(s) ? '#2962FF40' : '#2A2E39'}`,
                      borderRadius: '3px',
                      cursor: 'pointer',
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </>
          )}

          <div style={{
            padding: '10px 12px',
            borderRadius: 6,
            border: '1px solid #2A2E39',
            background: '#131722',
            fontSize: 11,
            color: '#787B86',
            lineHeight: 1.6,
          }}>
            Agent mode runs the full video pipeline end to end: market snapshot, Claude script, chart rendering, and final asset assembly.
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="panel-header">
          <span className="label">Preview — {typeInfo.label}</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <AgentTracePanel
            key={selectedVideoType}
            pipeline="Video Engine"
            endpoint="/api/agent/video/stream"
            payload={{ video_type: selectedVideoType, portfolio }}
            onComplete={(run) => {
              if (run.context?.video_path) {
                setVideoUrl(`/api/video/serve/${run.run_id}`)
                const ext = (run.context.video_path.split('.').pop() || '').toLowerCase()
                setMediaKind(ext === 'gif' || ext === 'png' ? 'image' : 'video')
              }
              if (run.context?.narration) {
                setNarration(run.context.narration)
              }
            }}
          />

          {!videoUrl && (
            <div style={{
              flex: 1,
              minHeight: '280px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid #2A2E39',
              borderRadius: '6px',
              background: '#131722',
            }}>
              <div style={{ textAlign: 'center' }}>
                <Logo collapsed />
                <div style={{ marginTop: '12px', fontSize: '13px', color: '#4C525E' }}>
                  Configure and run your market video agent
                </div>
                <div className="text-xs" style={{ color: '#4C525E', marginTop: '4px' }}>
                  {typeInfo.desc}
                </div>
              </div>
            </div>
          )}

          {videoUrl && (
            <div style={{ width: '100%', maxWidth: '720px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ background: '#0D1117', borderRadius: '4px', overflow: 'hidden', border: '1px solid #2A2E39' }}>
                {mediaKind === 'image' ? (
                  <img src={videoUrl} alt="Generated market visual" style={{ width: '100%', display: 'block' }} />
                ) : (
                  <video controls autoPlay style={{ width: '100%', display: 'block' }} src={videoUrl} />
                )}
              </div>

              {narration && (
                <div style={{ border: '1px solid #2A2E39', borderRadius: '4px', overflow: 'hidden' }}>
                  <button
                    onClick={() => setScriptOpen(open => !open)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      padding: '8px 12px',
                      background: '#1E222D',
                      border: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    <span className="label">Narration Script</span>
                    {scriptOpen ? <ChevronDown size={13} style={{ color: '#787B86' }} /> : <ChevronRight size={13} style={{ color: '#787B86' }} />}
                  </button>
                  {scriptOpen && (
                    <div style={{ padding: '12px', background: '#131722', fontSize: '12px', color: '#787B86', lineHeight: '1.7' }}>
                      {narration}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
