import React, { useEffect, useMemo, useRef, useState } from 'react'

const COLORS = {
  bgCard: '#1E222D',
  bgElevated: '#2A2E39',
  border: '#2A2E39',
  textPrimary: '#D1D4DC',
  textSecond: '#787B86',
  textMuted: '#4C525E',
  bull: '#26A69A',
  bear: '#EF5350',
  accent: '#2962FF',
}

const MONO = 'JetBrains Mono, monospace'

function formatMs(value) {
  const ms = Number(value || 0)
  return `${ms.toLocaleString('en-IN')}ms`
}

function statusColors(status) {
  if (status === 'complete') {
    return { bg: 'rgba(38,166,154,0.14)', color: COLORS.bull, border: `${COLORS.bull}33` }
  }
  if (status === 'partial') {
    return { bg: 'rgba(249,168,37,0.14)', color: '#F9A825', border: 'rgba(249,168,37,0.22)' }
  }
  if (status === 'failed') {
    return { bg: 'rgba(239,83,80,0.14)', color: COLORS.bear, border: `${COLORS.bear}33` }
  }
  return { bg: 'rgba(120,123,134,0.14)', color: COLORS.textSecond, border: `${COLORS.textSecond}22` }
}

function actionColors(action) {
  const normalized = String(action || '').toUpperCase()
  if (normalized.includes('BUY')) return { bg: 'rgba(38,166,154,0.16)', color: COLORS.bull }
  if (normalized.includes('SELL')) return { bg: 'rgba(239,83,80,0.16)', color: COLORS.bear }
  return { bg: 'rgba(120,123,134,0.16)', color: COLORS.textSecond }
}

function StepIcon({ status }) {
  if (status === 'running') {
    return (
      <div
        style={{
          width: 16,
          height: 16,
          borderRadius: '50%',
          border: `2px solid ${COLORS.bgElevated}`,
          borderTopColor: COLORS.accent,
          boxSizing: 'border-box',
          animation: 'agent-spin 0.9s linear infinite',
        }}
      />
    )
  }

  if (status === 'success') {
    return (
      <div
        style={{
          width: 16,
          height: 16,
          borderRadius: '50%',
          background: COLORS.bull,
          color: '#fff',
          fontSize: 10,
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        ✓
      </div>
    )
  }

  if (status === 'failed') {
    return (
      <div
        style={{
          width: 16,
          height: 16,
          borderRadius: '50%',
          background: COLORS.bear,
          color: '#fff',
          fontSize: 10,
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        ✗
      </div>
    )
  }

  return (
    <div
      style={{
        width: 16,
        height: 16,
        borderRadius: '50%',
        border: `1px solid ${COLORS.textMuted}`,
        boxSizing: 'border-box',
      }}
    />
  )
}

function TradeChips({ levels }) {
  const chips = []
  if (levels?.entry_low != null || levels?.entry_high != null) {
    const entryLabel = levels.entry_low != null && levels.entry_high != null
      ? `Entry ₹${levels.entry_low} - ₹${levels.entry_high}`
      : `Entry ₹${levels.entry_low ?? levels.entry_high}`
    chips.push({ key: 'entry_zone', label: entryLabel, color: COLORS.accent })
  }
  if (levels?.entry != null) chips.push({ key: 'entry', label: `Entry ₹${levels.entry}`, color: COLORS.accent })
  if (levels?.target != null) chips.push({ key: 'target', label: `Target ₹${levels.target}`, color: COLORS.bull })
  if (levels?.stop_loss != null) chips.push({ key: 'stop_loss', label: `Stop ₹${levels.stop_loss}`, color: COLORS.bear })
  if (levels?.horizon) chips.push({ key: 'horizon', label: String(levels.horizon), color: COLORS.textSecond })

  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {chips.map(chip => (
        <span
          key={chip.key}
          style={{
            fontSize: 10,
            padding: '3px 7px',
            borderRadius: 999,
            background: `${chip.color}1A`,
            color: chip.color,
            border: `1px solid ${chip.color}33`,
            fontFamily: MONO,
          }}
        >
          {chip.label}
        </span>
      ))}
    </div>
  )
}

export default function AgentTracePanel({
  pipeline,
  endpoint,
  payload,
  onAlerts,
  onComplete,
}) {
  const abortRef = useRef(null)
  const [runState, setRunState] = useState('idle')
  const [steps, setSteps] = useState([])
  const [summary, setSummary] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState('')
  const [expandedAlerts, setExpandedAlerts] = useState({})

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  const hasFinished = runState === 'complete' || runState === 'failed'
  const showRetry = runState === 'failed'
  const badgeStyle = useMemo(() => statusColors(summary?.status), [summary?.status])

  const resetState = () => {
    setRunState('running')
    setSteps([])
    setSummary(null)
    setAlerts([])
    setExpandedAlerts({})
    setError('')
  }

  const upsertStep = (incoming, status) => {
    setSteps(prev => {
      const next = [...prev]
      const idx = next.findIndex(step => step.step_index === incoming.step_index)
      const base = {
        step_index: incoming.step_index,
        step_name: incoming.step_name,
        description: incoming.description || '',
        status: status || 'pending',
        duration_ms: incoming.duration_ms || null,
        output_summary: incoming.output_summary || '',
        error: incoming.error || '',
      }

      if (idx === -1) {
        next.push(base)
      } else {
        next[idx] = {
          ...next[idx],
          ...base,
          status: status || next[idx].status,
          duration_ms: incoming.duration_ms ?? next[idx].duration_ms,
          output_summary: incoming.output_summary ?? next[idx].output_summary,
          error: incoming.error ?? next[idx].error,
        }
      }

      next.sort((a, b) => a.step_index - b.step_index)
      return next
    })
  }

  const handleEvent = (event) => {
    if (!event?.type) return

    if (event.type === 'pipeline_start') {
      setSummary({
        run_id: event.run_id,
        total_steps: event.total_steps,
        total_ms: null,
        status: 'running',
      })
      return
    }

    if (event.type === 'step_start') {
      upsertStep(event, 'running')
      return
    }

    if (event.type === 'step_complete') {
      upsertStep(event, event.status === 'failed' ? 'failed' : 'success')
      return
    }

    if (event.type === 'pipeline_complete') {
      setSummary(prev => ({
        ...(prev || {}),
        run_id: event.run_id,
        status: event.status,
        total_ms: event.total_ms,
      }))
      setRunState(event.status === 'failed' ? 'failed' : 'complete')
      return
    }

    if (event.type === 'alerts') {
      setAlerts(event.alerts || [])
      onAlerts?.(event.alerts || [])
      return
    }

    if (event.type === 'run_complete') {
      onComplete?.(event.run)
      return
    }

    if (event.type === 'error') {
      setError(event.error || 'Agent stream failed.')
      setRunState('failed')
    }
  }

  const runAgent = async () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    resetState()

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload || {}),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      if (!response.body) {
        throw new Error('Streaming response body unavailable.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            handleEvent(JSON.parse(line.slice(6)))
          } catch {
            // Ignore malformed event chunks.
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Agent stream failed.')
        setRunState('failed')
      }
    }
  }

  const toggleAlert = (key) => {
    setExpandedAlerts(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div
      style={{
        background: COLORS.bgCard,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 8,
        padding: 14,
        color: COLORS.textPrimary,
        fontFamily: 'inherit',
      }}
    >
      <style>{`
        @keyframes agent-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div style={{ fontSize: 10, letterSpacing: '0.08em', color: COLORS.textMuted }}>LIVE AGENT TRACE</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: COLORS.textPrimary }}>{pipeline}</div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {summary?.status && summary.status !== 'running' && (
            <span
              style={{
                fontSize: 10,
                padding: '4px 8px',
                borderRadius: 999,
                background: badgeStyle.bg,
                color: badgeStyle.color,
                border: `1px solid ${badgeStyle.border}`,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              {summary.status}
            </span>
          )}

          {(runState === 'idle' || hasFinished) && (
            <button
              onClick={runAgent}
              style={{
                height: 32,
                padding: '0 14px',
                borderRadius: 6,
                border: 'none',
                background: COLORS.accent,
                color: COLORS.textPrimary,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {showRetry ? 'Retry Agent' : hasFinished ? 'Run Again' : 'Run Agent'}
            </button>
          )}
        </div>
      </div>

      {summary?.total_ms != null && (
        <div style={{ marginTop: 8, fontSize: 11, color: COLORS.textSecond }}>
          Total time <span style={{ fontFamily: MONO, color: COLORS.textPrimary }}>{formatMs(summary.total_ms)}</span>
        </div>
      )}

      {runState === 'running' && steps.length === 0 && (
        <div style={{ marginTop: 14, fontSize: 12, color: COLORS.textSecond }}>
          Waiting for the first pipeline event…
        </div>
      )}

      {steps.length > 0 && (
        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {steps.map(step => (
            <div
              key={step.step_index}
              style={{
                display: 'grid',
                gridTemplateColumns: '20px minmax(0, 1fr) auto',
                gap: 10,
                alignItems: 'flex-start',
                minHeight: 40,
                padding: '10px 12px',
                borderRadius: 8,
                background: 'rgba(42,46,57,0.45)',
                border: `1px solid ${COLORS.border}`,
              }}
            >
              <div style={{ paddingTop: 1 }}>
                <StepIcon status={step.status} />
              </div>

              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, color: COLORS.textPrimary }}>{step.step_name}</div>
                {(step.output_summary || step.error) && (
                  <div style={{ marginTop: 4, fontSize: 11, color: step.error ? COLORS.bear : COLORS.textSecond, lineHeight: 1.45 }}>
                    {step.output_summary || step.error}
                  </div>
                )}
              </div>

              <div
                style={{
                  fontSize: 11,
                  color: COLORS.textMuted,
                  fontFamily: MONO,
                  whiteSpace: 'nowrap',
                  textAlign: 'right',
                  paddingTop: 1,
                }}
              >
                {step.duration_ms != null ? formatMs(step.duration_ms) : ''}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div
          style={{
            marginTop: 12,
            padding: '10px 12px',
            borderRadius: 8,
            background: 'rgba(239,83,80,0.08)',
            color: COLORS.bear,
            fontSize: 12,
            border: `1px solid ${COLORS.bear}22`,
          }}
        >
          {error}
        </div>
      )}

      {alerts.length > 0 && (
        <div style={{ marginTop: 18 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.08em', color: COLORS.textMuted, marginBottom: 10 }}>
            ACTIONABLE ALERTS
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {alerts.map(alert => {
              const actionStyle = actionColors(alert.action)
              const key = `${alert.symbol}-${alert.rank}`
              const expanded = !!expandedAlerts[key]
              const reasoning = alert.reasoning || alert.explanation || 'No reasoning available.'

              return (
                <div
                  key={key}
                  style={{
                    borderRadius: 8,
                    background: COLORS.bgElevated,
                    border: `1px solid ${COLORS.border}`,
                    padding: 12,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                      <span
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: '50%',
                          background: `${COLORS.accent}1A`,
                          color: COLORS.accent,
                          fontSize: 11,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontFamily: MONO,
                        }}
                      >
                        #{alert.rank}
                      </span>

                      <div style={{ minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <span style={{ fontFamily: MONO, fontSize: 13, fontWeight: 700, color: COLORS.textPrimary }}>
                            {alert.symbol}
                          </span>
                          {alert.company_name && (
                            <span style={{ fontSize: 12, color: COLORS.textSecond }}>{alert.company_name}</span>
                          )}
                        </div>
                        <div style={{ marginTop: 3, fontSize: 11, color: COLORS.textSecond }}>
                          {alert.headline || alert.pattern || alert.signal_type}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      <span
                        style={{
                          fontSize: 10,
                          padding: '4px 8px',
                          borderRadius: 999,
                          background: actionStyle.bg,
                          color: actionStyle.color,
                          fontWeight: 700,
                        }}
                      >
                        {alert.action}
                      </span>
                      {alert.conviction && (
                        <span
                          style={{
                            fontSize: 10,
                            padding: '4px 8px',
                            borderRadius: 999,
                            background: 'rgba(120,123,134,0.16)',
                            color: COLORS.textPrimary,
                          }}
                        >
                          {alert.conviction}
                        </span>
                      )}
                    </div>
                  </div>

                  {alert.portfolio_note && (
                    <div style={{ marginTop: 9, fontSize: 11, color: COLORS.textSecond, fontStyle: 'italic' }}>
                      {alert.portfolio_note}
                    </div>
                  )}

                  <div style={{ marginTop: 10 }}>
                    <TradeChips levels={alert.trade_levels} />
                  </div>

                  <div style={{ marginTop: 10 }}>
                    <div
                      style={{
                        fontSize: 11,
                        color: COLORS.textSecond,
                        lineHeight: 1.5,
                        display: '-webkit-box',
                        WebkitBoxOrient: 'vertical',
                        WebkitLineClamp: expanded ? 'unset' : 3,
                        overflow: expanded ? 'visible' : 'hidden',
                      }}
                    >
                      {reasoning}
                    </div>
                    {reasoning.length > 160 && (
                      <button
                        onClick={() => toggleAlert(key)}
                        style={{
                          marginTop: 6,
                          border: 'none',
                          background: 'transparent',
                          color: COLORS.accent,
                          cursor: 'pointer',
                          padding: 0,
                          fontSize: 11,
                        }}
                      >
                        {expanded ? 'Show less' : 'Show more'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
