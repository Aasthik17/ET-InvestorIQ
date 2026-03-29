/**
 * ScenarioPack — Hackathon judge demo page.
 * Shows all 3 "Shared Scenario Pack" challenges as interactive cards.
 * Each card fires the real agent pipeline and streams the live trace.
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import AgentTracePanel from '../components/agent/AgentTracePanel'

// ─── Scenario definitions ─────────────────────────────────────────────────────

const SCENARIOS = [
  {
    id: 's1',
    number: '01',
    tag: 'Opportunity Radar',
    title: 'Promoter Bulk Deal — Distress or Routine?',
    rubric: 'Alert must cite the filing, not just surface a vague warning.',
    description:
      'A promoter of a mid-cap FMCG company has sold 4.2% of their stake via a bulk deal at a 6% discount to market price. The agent must retrieve the filing, classify whether this is likely distress selling or a routine block, cross-reference recent management commentary and earnings, and generate a risk-adjusted alert with a specific recommended action.',
    color: '#EF5350',
    gradient: 'linear-gradient(135deg, rgba(239,83,80,0.12) 0%, rgba(239,83,80,0.03) 100%)',
    pipeline: 'Opportunity Radar',
    endpoint: '/api/agent/radar/stream',
    payload: {
      portfolio: {
        holdings: [
          { symbol: 'HINDUNILVR', quantity: 50, avg_cost: 2400 },
          { symbol: 'ITC', quantity: 200, avg_cost: 450 },
          { symbol: 'NESTLEIND', quantity: 10, avg_cost: 25000 },
        ],
        risk_profile: 'MODERATE',
      },
    },
    prefilledChat: null,
    judgeNote: [
      'Checks for: deal_class = PROMOTER_DISTRESS',
      'Checks for: distress_probability score',
      'Checks for: filing_citation with exchange + date + subject',
      'Checks for: balanced risk assessment, not a binary SELL',
    ],
  },
  {
    id: 's2',
    number: '02',
    tag: 'Chart Intelligence',
    title: '52-Week Breakout vs. RSI + FII Conflict',
    rubric: 'Must quantify historical success rate and present a balanced recommendation.',
    description:
      'A large-cap IT stock has broken out above its 52-week high on above-average volume. However, the RSI is at 78 (overbought) and a key FII has reduced exposure in the last filing. The agent must detect the breakout pattern, quantify the historical success rate of this pattern for this stock, surface conflicting signals, and present a balanced, data-backed recommendation — not a binary buy/sell call.',
    color: '#F9A825',
    gradient: 'linear-gradient(135deg, rgba(249,168,37,0.12) 0%, rgba(249,168,37,0.03) 100%)',
    pipeline: 'Chart Intelligence',
    endpoint: '/api/agent/chart/stream',
    payload: { symbol: 'TCS' },
    prefilledChat: null,
    judgeNote: [
      'Checks for: action = BULLISH_WITH_CAVEATS (not binary BUY)',
      'Checks for: RSI_OVERBOUGHT conflict signal',
      'Checks for: FII_REDUCING_EXPOSURE conflict',
      'Checks for: breakout_historical_success.win_rate with n_samples',
    ],
  },
  {
    id: 's3',
    number: '03',
    tag: 'Market Chat',
    title: 'Two Simultaneous News Events — Which One Matters More?',
    rubric: 'Must quantify estimated ₹ P&L impact per holding, not a generic news summary.',
    description:
      'A user holds 8 stocks. Two major news events break simultaneously: an RBI repo rate cut and a sector-specific regulatory change affecting one of their holdings. The agent must identify which event is more financially material to this specific portfolio, quantify the estimated P&L impact on relevant holdings, and generate a prioritised alert with context.',
    color: '#26A69A',
    gradient: 'linear-gradient(135deg, rgba(38,166,154,0.12) 0%, rgba(38,166,154,0.03) 100%)',
    pipeline: null,
    endpoint: null,
    payload: null,
    prefilledChat: `Two major news events just broke simultaneously:

1. RBI announces a 25bps repo rate cut (rate now at 5.75%)
2. SEBI issues new regulatory guidelines tightening NBFC lending norms by capping loan-to-value ratios

My portfolio:
- HDFCBANK: 100 shares @ avg ₹1,580
- BAJFINANCE: 25 shares @ avg ₹7,200
- TCS: 30 shares @ avg ₹3,800
- INFY: 50 shares @ avg ₹1,400
- SUNPHARMA: 40 shares @ avg ₹1,650
- AXISBANK: 60 shares @ avg ₹1,020
- MARUTI: 8 shares @ avg ₹11,000
- RELIANCE: 20 shares @ avg ₹2,900

Which event is more financially material to MY portfolio? Quantify the estimated P&L impact per holding and tell me which stocks I should act on first.`,
    judgeNote: [
      'Checks for: use of prioritise_news_for_portfolio tool',
      'Checks for: ₹ P&L impact per holding (not % only)',
      'Checks for: priority ranking of the two events',
      'Checks for: specific holding names, not generic sector advice',
    ],
  },
]

// ─── Components ───────────────────────────────────────────────────────────────

function JudgeRubric({ notes }) {
  return (
    <div style={{
      marginTop: 12,
      padding: '8px 10px',
      background: 'rgba(41,98,255,0.06)',
      border: '1px solid rgba(41,98,255,0.2)',
      borderRadius: 4,
    }}>
      <div style={{ fontSize: 9, color: '#2962FF', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 700, marginBottom: 6 }}>
        Judge Evaluation Checklist
      </div>
      {notes.map((note, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, marginBottom: 3 }}>
          <span style={{ color: '#4C525E', fontSize: 10, marginTop: 1 }}>☐</span>
          <span style={{ fontSize: 10, color: '#787B86', lineHeight: 1.5 }}>{note}</span>
        </div>
      ))}
    </div>
  )
}

function ScenarioCard({ scenario, onRun }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div style={{
      background: '#1E222D',
      border: `1px solid ${scenario.color}33`,
      borderRadius: 6,
      overflow: 'hidden',
      transition: 'border-color 0.15s',
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = scenario.color + '77'}
      onMouseLeave={e => e.currentTarget.style.borderColor = scenario.color + '33'}
    >
      {/* Header */}
      <div style={{
        background: scenario.gradient,
        padding: '14px 16px',
        borderBottom: `1px solid ${scenario.color}22`,
        display: 'flex', alignItems: 'flex-start', gap: 12,
      }}>
        <div style={{
          fontSize: 28, fontWeight: 800, color: scenario.color + '40',
          fontVariantNumeric: 'tabular-nums', lineHeight: 1, minWidth: 36,
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {scenario.number}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <span style={{
              fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
              textTransform: 'uppercase', color: scenario.color,
              background: scenario.color + '18',
              border: `1px solid ${scenario.color}44`,
              borderRadius: 3, padding: '1px 6px',
            }}>
              {scenario.tag}
            </span>
          </div>
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#D1D4DC', lineHeight: 1.4 }}>
            {scenario.title}
          </h3>
          <p style={{
            margin: '4px 0 0', fontSize: 11, color: '#787B86', lineHeight: 1.5,
            fontStyle: 'italic',
          }}>
            Rubric: {scenario.rubric}
          </p>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '12px 16px' }}>
        <p style={{ margin: '0 0 10px', fontSize: 12, color: '#787B86', lineHeight: 1.6 }}>
          {scenario.description}
        </p>

        <JudgeRubric notes={scenario.judgeNote} />

        {/* Expand for details */}
        <button
          onClick={() => setExpanded(v => !v)}
          style={{
            marginTop: 10, width: '100%', padding: '5px 0',
            background: 'transparent', border: '1px solid var(--border-primary)',
            borderRadius: 3, cursor: 'pointer',
            fontSize: 11, color: '#4C525E',
            transition: 'all 0.1s',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = '#363A45'; e.currentTarget.style.color = '#787B86' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-primary)'; e.currentTarget.style.color = '#4C525E' }}
        >
          {expanded ? '▲ Hide payload' : '▼ See demo payload'}
        </button>

        {expanded && (
          <pre style={{
            marginTop: 8, padding: '8px 10px',
            background: '#131722', borderRadius: 3,
            fontSize: 10, color: '#787B86',
            lineHeight: 1.5, overflowX: 'auto',
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            {scenario.prefilledChat
              ? scenario.prefilledChat
              : JSON.stringify(scenario.payload, null, 2)}
          </pre>
        )}

        {/* Run button */}
        <button
          id={`run-scenario-${scenario.id}`}
          onClick={() => onRun(scenario)}
          style={{
            marginTop: 10, width: '100%', padding: '8px 0',
            background: scenario.color,
            border: 'none', borderRadius: 4, cursor: 'pointer',
            fontSize: 12, fontWeight: 600, color: '#131722',
            letterSpacing: '0.04em',
            transition: 'opacity 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          ▶ Run Live Demo
        </button>
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ScenarioPack() {
  const navigate = useNavigate()
  const [activeScenario, setActiveScenario] = useState(null)
  const [agentAlerts, setAgentAlerts] = useState([])

  const handleRun = useCallback((scenario) => {
    if (scenario.id === 's3') {
      // Scenario 3 uses MarketChat — navigate with pre-filled query
      navigate('/chat', { state: { prefill: scenario.prefilledChat } })
      return
    }
    setAgentAlerts([])
    setActiveScenario(scenario)
  }, [navigate])

  return (
    <div style={{ height: '100%', overflowY: 'auto', background: '#131722' }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px 16px',
        borderBottom: '1px solid var(--border-primary)',
        background: '#1E222D',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 18 }}>🎯</span>
          <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#D1D4DC' }}>
            Shared Scenario Packs
          </h1>
          <span style={{
            fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
            textTransform: 'uppercase', color: '#26A69A',
            background: 'rgba(38,166,154,0.12)',
            border: '1px solid rgba(38,166,154,0.3)',
            borderRadius: 3, padding: '2px 7px',
          }}>
            ET Gen AI Hackathon 2026
          </span>
        </div>
        <p style={{ margin: 0, fontSize: 12, color: '#787B86', lineHeight: 1.6 }}>
          Three mandatory judging scenarios for the <strong style={{ color: '#D1D4DC' }}>AI for the Indian Investor</strong> track.
          Each tests a different agent dimension — filing citation, conflict detection, and portfolio-aware news ranking.
          Click <strong style={{ color: '#D1D4DC' }}>Run Live Demo</strong> to fire the real pipeline and view the agent trace.
        </p>
      </div>

      <div style={{ padding: '20px 24px' }}>
        {/* Scenario cards grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 16, marginBottom: 24 }}>
          {SCENARIOS.map(scenario => (
            <ScenarioCard key={scenario.id} scenario={scenario} onRun={handleRun} />
          ))}
        </div>

        {/* Live agent trace (for S1 and S2) */}
        {activeScenario && activeScenario.endpoint && (
          <div style={{
            background: '#1E222D',
            border: '1px solid var(--border-primary)',
            borderRadius: 6,
            overflow: 'hidden',
          }}>
            <div style={{
              padding: '10px 16px',
              borderBottom: '1px solid var(--border-primary)',
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#26A69A', animation: 'pulse 1.5s infinite' }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: '#D1D4DC' }}>
                Live Agent Trace — Scenario {activeScenario.number}: {activeScenario.title}
              </span>
              <button
                onClick={() => setActiveScenario(null)}
                style={{ marginLeft: 'auto', background: 'transparent', border: 'none', cursor: 'pointer', color: '#4C525E', fontSize: 12 }}
              >
                ✕ Close
              </button>
            </div>
            <div style={{ padding: 12 }}>
              <AgentTracePanel
                pipeline={activeScenario.pipeline}
                endpoint={activeScenario.endpoint}
                payload={activeScenario.payload}
                onAlerts={(alerts) => setAgentAlerts(alerts)}
                onComplete={(run) => console.log('Scenario run complete:', run.run_id)}
              />
            </div>

            {/* Scenario 1 alerts: show filing citation badge */}
            {agentAlerts.length > 0 && (
              <div style={{ padding: '0 16px 16px' }}>
                <div style={{ fontSize: 11, color: '#787B86', marginBottom: 8 }}>Agent Alerts Generated:</div>
                {agentAlerts.map((alert, i) => (
                  <div key={i} style={{
                    padding: '10px 12px', marginBottom: 8,
                    background: '#131722', borderRadius: 4,
                    borderLeft: `3px solid ${alert.action?.includes('SELL') || alert.action?.includes('BEARISH') ? '#EF5350' : alert.action?.includes('BUY') || alert.action?.includes('BULLISH') ? '#26A69A' : '#F9A825'}`,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#D1D4DC' }}>{alert.symbol}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 5px', borderRadius: 2, fontWeight: 700,
                        background: 'rgba(239,83,80,0.12)', color: '#EF5350', border: '1px solid rgba(239,83,80,0.3)',
                      }}>
                        {alert.action}
                      </span>
                      {alert.deal_class && (
                        <span style={{
                          fontSize: 9, padding: '1px 5px', borderRadius: 2, fontWeight: 700,
                          background: 'rgba(249,168,37,0.12)', color: '#F9A825', border: '1px solid rgba(249,168,37,0.3)',
                        }}>
                          {alert.deal_class}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: '#787B86', lineHeight: 1.5 }}>{alert.headline}</div>

                    {/* Scenario 1: Filing citation badge */}
                    {alert.filing_citation && (
                      <div style={{
                        marginTop: 8, padding: '6px 8px',
                        background: 'rgba(41,98,255,0.08)',
                        border: '1px solid rgba(41,98,255,0.25)',
                        borderRadius: 3, fontSize: 10, color: '#2962FF',
                        fontFamily: "'JetBrains Mono', monospace",
                      }}>
                        📋 {alert.filing_citation.citation}
                      </div>
                    )}
                    {alert.distress_probability != null && (
                      <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 10, color: '#4C525E' }}>Distress score:</span>
                        <div style={{ height: 4, width: 80, background: '#2A2E39', borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${alert.distress_probability * 100}%`, background: '#EF5350', borderRadius: 2 }} />
                        </div>
                        <span style={{ fontSize: 10, color: '#EF5350', fontFamily: "'JetBrains Mono', monospace" }}>
                          {(alert.distress_probability * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}

                    {/* Scenario 2: Conflict signals */}
                    {alert.scenario2?.conflicting_signals?.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        {alert.scenario2.conflicting_signals.map((c, ci) => (
                          <div key={ci} style={{
                            marginBottom: 4, padding: '4px 8px',
                            background: 'rgba(239,83,80,0.06)',
                            border: '1px solid rgba(239,83,80,0.15)',
                            borderRadius: 3, fontSize: 10, color: '#EF5350',
                          }}>
                            ⚠ {c.signal}: {c.description}
                          </div>
                        ))}
                        {alert.scenario2.breakout_historical_success?.win_rate != null && (
                          <div style={{ fontSize: 10, color: '#4C525E', marginTop: 4 }}>
                            Historical 52W breakout success rate: {alert.scenario2.breakout_historical_success.win_rate}%
                            ({alert.scenario2.breakout_historical_success.n_samples} samples)
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  )
}
