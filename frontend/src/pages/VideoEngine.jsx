/**
 * VideoEngine — Content studio: config left, preview right.
 * Terminal-style generation progress log.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Circle, ChevronDown, ChevronRight } from 'lucide-react'
import { videoAPI } from '../services/api'
import LoadingSpinner from '../components/common/LoadingSpinner'
import Logo from '../components/layout/Logo'

const VIDEO_TYPES = [
  { type: 'MARKET_WRAP',      label: 'Market Wrap (Daily)',  desc: 'End-of-day summary with top movers' },
  { type: 'SECTOR_ROTATION',  label: 'Sector Rotation',      desc: 'Sector performance heatmap + flow' },
  { type: 'FII_DII_FLOW',     label: 'FII / DII Flow',       desc: 'Institutional money movement chart' },
  { type: 'BAR_RACE',         label: 'Bar Race Chart',        desc: 'Animated stock performance race' },
  { type: 'IPO_TRACKER',      label: 'IPO Tracker',          desc: 'Upcoming IPO pipeline overview' },
  { type: 'STOCK_DEEP_DIVE',  label: 'Stock Deep Dive',       desc: 'Full fundamental + technical analysis' },
]

const DATE_RANGES = ['1W', '1M', '3M']
const DURATIONS   = ['30s', '60s', '90s']

const NSE_SYMBOLS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'BAJFINANCE', 'SBIN', 'ITC', 'TATAMOTORS', 'SUNPHARMA']

function ProgressLog({ steps, activeIdx, progress }) {
  return (
    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', lineHeight: '2' }}>
      {steps.map((step, i) => {
        const done    = i < activeIdx
        const active  = i === activeIdx
        const pending = i > activeIdx
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px',
            color: done ? '#26A69A' : active ? '#D1D4DC' : '#4C525E' }}>
            <span style={{ width: '16px', textAlign: 'center' }}>
              {done ? '✓' : active ? '●' : '·'}
            </span>
            {step}
            {active && (
              <span style={{ marginLeft: '4px' }}>
                {[0, 1, 2].map(j => (
                  <span key={j} style={{
                    display: 'inline-block', width: '4px', height: '4px', borderRadius: '50%',
                    background: '#2962FF', marginRight: '3px',
                    animation: `pulse 1.2s ease-in-out ${j * 0.2}s infinite`,
                    verticalAlign: 'middle',
                  }} />
                ))}
              </span>
            )}
          </div>
        )
      })}
      {/* Progress bar */}
      <div style={{ marginTop: '12px', height: '3px', background: '#2A2E39', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{
          height: '100%', background: '#2962FF', borderRadius: '2px',
          width: `${progress}%`, transition: 'width 500ms ease',
        }} />
      </div>
      <style>{`@keyframes pulse { 0%,100%{opacity:0.2} 50%{opacity:1} }`}</style>
    </div>
  )
}

const PROGRESS_STEPS = [
  'Fetching NSE market data',
  'Running AI signal analysis',
  'Rendering chart frames',
  'Generating narration script',
  'Assembling video',
]

export default function VideoEngine() {
  const [selectedType, setSelectedType] = useState('MARKET_WRAP')
  const [dateRange, setDateRange]       = useState('1M')
  const [duration, setDuration]         = useState('60s')
  const [symbols, setSymbols]           = useState(['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK'])
  const [scriptOpen, setScriptOpen]     = useState(false)
  const [completedJob, setCompletedJob] = useState(null)
  const [generatingJob, setGeneratingJob] = useState(null)
  const [progressStep, setProgressStep] = useState(0)

  const qc = useQueryClient()

  // Poll generating job
  useQuery({
    queryKey: ['video-job', generatingJob],
    queryFn: () => videoAPI.job(generatingJob),
    enabled: !!generatingJob,
    refetchInterval: data => {
      if (!data) return 2000
      if (data.status === 'COMPLETE' || data.status === 'FAILED') return false
      return 2000
    },
    onSuccess: (data) => {
      if (!data) return
      const step = Math.floor((data.progress_pct || 0) / 20)
      setProgressStep(Math.min(step, PROGRESS_STEPS.length - 1))
      if (data.status === 'COMPLETE') {
        setCompletedJob(data)
        setGeneratingJob(null)
        qc.invalidateQueries({ queryKey: ['video-jobs'] })
      } else if (data.status === 'FAILED') {
        setGeneratingJob(null)
      }
    },
  })

  const { data: vtypes } = useQuery({
    queryKey: ['video-types'],
    queryFn: videoAPI.types,
    staleTime: Infinity,
  })

  const generateMutation = useMutation({
    mutationFn: videoAPI.generate,
    onSuccess: (data) => {
      setCompletedJob(null)
      setProgressStep(0)
      setGeneratingJob(data.job_id)
    },
  })

  const typeInfo = VIDEO_TYPES.find(t => t.type === selectedType) || VIDEO_TYPES[0]
  const isRace = selectedType === 'BAR_RACE'
  const isGenerating = !!generatingJob
  const progress = generatingJob ? (progressStep / PROGRESS_STEPS.length) * 100 : 0

  const toggleSymbol = sym => {
    setSymbols(prev => prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym].slice(0, 8))
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── Left: Configuration ───────────────────────────────────────── */}
      <div style={{
        width: '360px', minWidth: '360px',
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

        {/* Video type list — radio rows */}
        {VIDEO_TYPES.map(vt => {
          const active = selectedType === vt.type
          return (
            <div
              key={vt.type}
              onClick={() => setSelectedType(vt.type)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: '10px',
                padding: '8px 12px', cursor: 'pointer',
                borderLeft: `2px solid ${active ? '#2962FF' : 'transparent'}`,
                background: active ? '#1E2B4D' : 'transparent',
                borderBottom: '1px solid #1E222D',
                transition: 'background 100ms',
              }}
            >
              <div style={{
                width: '14px', height: '14px', borderRadius: '50%', flexShrink: 0, marginTop: '2px',
                border: `2px solid ${active ? '#2962FF' : '#4C525E'}`,
                background: active ? '#2962FF' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
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

        {/* Options */}
        <div style={{ padding: '0 12px 12px' }}>
          <div className="label" style={{ marginBottom: '6px' }}>Date Range</div>
          <div className="toggle-group" style={{ marginBottom: '12px' }}>
            {DATE_RANGES.map(d => (
              <button key={d} className={`toggle-btn${dateRange === d ? ' active' : ''}`}
                onClick={() => setDateRange(d)} style={{ flex: 1, fontSize: '11px' }}>
                {d}
              </button>
            ))}
          </div>

          <div className="label" style={{ marginBottom: '6px' }}>Duration</div>
          <div className="toggle-group" style={{ marginBottom: '12px' }}>
            {DURATIONS.map(d => (
              <button key={d} className={`toggle-btn${duration === d ? ' active' : ''}`}
                onClick={() => setDuration(d)} style={{ flex: 1, fontSize: '11px' }}>
                {d}
              </button>
            ))}
          </div>

          {isRace && (
            <>
              <div className="label" style={{ marginBottom: '6px' }}>Stocks to Race ({symbols.length}/8)</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '12px' }}>
                {NSE_SYMBOLS.map(s => (
                  <button key={s} onClick={() => toggleSymbol(s)} style={{
                    height: '22px', padding: '0 7px', fontSize: '11px',
                    fontFamily: "'JetBrains Mono', monospace",
                    background: symbols.includes(s) ? '#1E2B4D' : 'transparent',
                    color: symbols.includes(s) ? '#2962FF' : '#787B86',
                    border: `1px solid ${symbols.includes(s) ? '#2962FF40' : '#2A2E39'}`,
                    borderRadius: '3px', cursor: 'pointer',
                  }}>
                    {s}
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Generate button — full-width, the ONE primary CTA */}
          <button
            className="btn-primary"
            onClick={() => generateMutation.mutate({
              video_type: selectedType,
              symbols: symbols.map(s => s + '.NS'),
              duration_seconds: parseInt(duration),
              date_range: dateRange,
            })}
            disabled={isGenerating || generateMutation.isPending}
            style={{ width: '100%', justifyContent: 'center', height: '36px', fontSize: '13px', borderRadius: '4px' }}
          >
            {(isGenerating || generateMutation.isPending) ? (
              <><LoadingSpinner size={13} /> Generating...</>
            ) : 'Generate Video'}
          </button>
        </div>
      </div>

      {/* ── Right: Preview ────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="panel-header">
          <span className="label">Preview — {typeInfo.label}</span>
        </div>

        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
          {/* Idle state */}
          {!isGenerating && !completedJob && (
            <div style={{ textAlign: 'center' }}>
              <Logo collapsed />
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#4C525E' }}>
                Configure and generate your market video
              </div>
              <div className="text-xs" style={{ color: '#4C525E', marginTop: '4px' }}>
                {typeInfo.desc}
              </div>
            </div>
          )}

          {/* Generation in progress */}
          {isGenerating && (
            <div style={{ width: '360px' }}>
              <div className="label" style={{ marginBottom: '12px' }}>Generating…</div>
              <ProgressLog steps={PROGRESS_STEPS} activeIdx={progressStep} progress={progress} />
            </div>
          )}

          {/* Complete */}
          {completedJob?.status === 'COMPLETE' && !isGenerating && (
            <div style={{ width: '100%', maxWidth: '720px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Video player */}
              <div style={{ background: '#0D1117', borderRadius: '4px', overflow: 'hidden', border: '1px solid #2A2E39' }}>
                <video
                  controls
                  autoPlay
                  style={{ width: '100%', display: 'block' }}
                  src={`/videos/${completedJob.job_id}.mp4`}
                >
                  <img src={`/videos/${completedJob.job_id}.gif`} alt="Generated chart" style={{ width: '100%' }} />
                </video>
              </div>

              {/* Narration script — collapsible */}
              {completedJob.narration_script && (
                <div style={{ border: '1px solid #2A2E39', borderRadius: '4px', overflow: 'hidden' }}>
                  <button
                    onClick={() => setScriptOpen(o => !o)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      width: '100%', padding: '8px 12px', background: '#1E222D',
                      border: 'none', cursor: 'pointer',
                    }}
                  >
                    <span className="label">Narration Script</span>
                    {scriptOpen ? <ChevronDown size={13} style={{ color: '#787B86' }} /> : <ChevronRight size={13} style={{ color: '#787B86' }} />}
                  </button>
                  {scriptOpen && (
                    <div style={{ padding: '12px', background: '#131722', fontSize: '12px', color: '#787B86', lineHeight: '1.7' }}>
                      {completedJob.narration_script}
                    </div>
                  )}
                </div>
              )}

              <button className="btn-secondary" style={{ alignSelf: 'flex-start' }}>
                Export Video
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
