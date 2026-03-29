/**
 * MarketChat — Purpose-built financial analyst tool.
 * NOT ChatGPT with a skin. Portfolio panel left, citation-style responses right.
 */
import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { Send, Plus, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useChat } from '../hooks/useChat'
import { chatAPI } from '../services/api'
import LoadingSpinner from '../components/common/LoadingSpinner'
import Logo from '../components/layout/Logo'

const QUICK_QUERIES = [
  'What are the top insider buying signals right now?',
  'Compare HDFC Bank vs ICICI Bank fundamentals',
  'Which sectors are showing FII accumulation?',
  'Give me RSI oversold stocks in Nifty 50',
  'Analyze Reliance Industries chart pattern',
]

const DEFAULT_HOLDINGS = [
  { symbol: 'HDFCBANK', qty: 25, avg: 1610, ltp: 1648 },
  { symbol: 'INFY',     qty: 40, avg: 1420, ltp: 1385 },
  { symbol: 'RELIANCE', qty: 15, avg: 2780, ltp: 2930 },
]

function PnLPct({ avg, ltp }) {
  const pct = ((ltp - avg) / avg) * 100
  const up = pct >= 0
  return (
    <span className={`price ${up ? 'bull' : 'bear'}`} style={{ fontSize: '11px' }}>
      {up ? '+' : ''}{pct.toFixed(2)}%
    </span>
  )
}

function HoldingRow({ h }) {
  const pnl = (h.ltp - h.avg) * h.qty
  const pnlUp = pnl >= 0
  return (
    <tr style={{ height: '28px', borderBottom: '1px solid #1E222D' }}>
      <td className="price" style={{ padding: '0 8px', fontSize: '11px', fontWeight: 600, color: '#D1D4DC' }}>{h.symbol}</td>
      <td className="price" style={{ padding: '0 8px', fontSize: '11px', color: '#787B86', textAlign: 'right' }}>{h.qty}</td>
      <td className="price" style={{ padding: '0 8px', fontSize: '11px', color: '#D1D4DC', textAlign: 'right' }}>₹{h.ltp.toLocaleString('en-IN')}</td>
      <td style={{ padding: '0 8px', textAlign: 'right' }}><PnLPct avg={h.avg} ltp={h.ltp} /></td>
    </tr>
  )
}

function UserMessage({ content, timestamp }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{
        background: '#2A2E39',
        borderLeft: '2px solid #2962FF',
        padding: '8px 12px',
        borderRadius: '0 4px 4px 0',
        maxWidth: '85%',
      }}>
        <p style={{ margin: 0, fontSize: '13px', color: '#D1D4DC', lineHeight: '1.5' }}>{content}</p>
      </div>
      <div className="price" style={{ fontSize: '10px', color: '#4C525E', marginTop: '3px', paddingLeft: '14px' }}>
        You · {timestamp}
      </div>
    </div>
  )
}

function AIMessage({ content, sources = [], toolCalls = [] }) {
  return (
    <div style={{ marginBottom: '20px' }}>
      {/* Tool calls header */}
      {toolCalls.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '6px' }}>
          {toolCalls.map((t, i) => (
            <span key={i} className="text-xs" style={{ color: '#4C525E' }}>
              ⊕ {t.name?.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}
      {/* Source label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
        <Logo collapsed />
        <span className="text-xs" style={{ color: '#4C525E' }}>ET InvestorIQ</span>
      </div>
      {/* Response text */}
      <div style={{
        fontSize: '13px', color: '#D1D4DC', lineHeight: '1.6',
        paddingLeft: '0',
      }}>
        <div className="prose-dark">
          <ReactMarkdown
            components={{
              p: ({ children }) => <p style={{ margin: '0 0 8px' }}>{children}</p>,
              strong: ({ children }) => <strong style={{ color: '#D1D4DC', fontWeight: 600 }}>{children}</strong>,
              code: ({ children }) => <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', background: '#2A2E39', padding: '1px 4px', borderRadius: '3px', color: '#D1D4DC' }}>{children}</code>,
              ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ul>,
              li: ({ children }) => <li style={{ marginBottom: '2px', color: '#787B86' }}>{children}</li>,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>
      {/* Sources as academic refs */}
      {sources.length > 0 && (
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '8px' }}>
          {sources.map((s, i) => (
            <span key={i} style={{
              fontSize: '11px', color: '#4C525E',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              [{i+1}] {s.name || s}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function MarketChat() {
  const { messages, isStreaming, streamingContent, sendMessage, clearChat } = useChat()
  const [input, setInput] = useState('')
  const [holdings, setHoldings] = useState(DEFAULT_HOLDINGS)
  const [riskProfile, setRiskProfile] = useState('Moderate')
  const [horizon, setHorizon] = useState('Medium')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const location = useLocation()

  // Scenario 3: auto-populate chat from /scenarios page navigation
  useEffect(() => {
    if (location.state?.prefill) {
      setInput(location.state.prefill)
      inputRef.current?.focus()
    }
  }, [location.state])

  const { data: suggestions } = useQuery({
    queryKey: ['chat-suggestions'],
    queryFn: () => chatAPI.suggestions(),
    staleTime: 300_000,
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const handleSend = (text) => {
    const t = (text || input).trim()
    if (!t || isStreaming) return
    setInput('')
    sendMessage(t, null, true)
  }

  const totalInvested = holdings.reduce((a, h) => a + h.avg * h.qty, 0)
  const currentValue  = holdings.reduce((a, h) => a + h.ltp * h.qty, 0)
  const totalPnL = currentValue - totalInvested

  const displayQueries = suggestions?.slice(0, 5).map(s => s.question) || QUICK_QUERIES

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── Left panel: portfolio + context ─────────────────────────── */}
      <div style={{
        width: '300px', minWidth: '300px',
        background: '#1E222D',
        borderRight: '1px solid #2A2E39',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        flexShrink: 0,
      }}>
        {/* Portfolio */}
        <div className="panel-header">
          <span className="label">My Portfolio</span>
          <button className="btn-ghost" style={{ fontSize: '11px', gap: '3px' }}>
            <Plus size={11} /> Add Holding
          </button>
        </div>
        <div style={{ overflow: 'auto', flexShrink: 0 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #2A2E39' }}>
                {['SYMBOL', 'QTY', 'LTP', 'P&L%'].map((h, i) => (
                  <th key={h} className="label" style={{ padding: '0 8px', height: '26px', textAlign: i > 1 ? 'right' : 'left' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, i) => <HoldingRow key={i} h={h} />)}
            </tbody>
          </table>
          {/* Portfolio summary */}
          <div style={{ padding: '8px', borderTop: '1px solid #2A2E39' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
              <span className="text-xs" style={{ color: '#787B86' }}>Invested</span>
              <span className="price text-xs" style={{ color: '#D1D4DC' }}>₹{(totalInvested/1000).toFixed(1)}K</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
              <span className="text-xs" style={{ color: '#787B86' }}>Current</span>
              <span className="price text-xs" style={{ color: '#D1D4DC' }}>₹{(currentValue/1000).toFixed(1)}K</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-xs" style={{ color: '#787B86' }}>P&L</span>
              <span className={`price text-xs ${totalPnL >= 0 ? 'bull' : 'bear'}`}>
                {totalPnL >= 0 ? '+' : ''}₹{Math.abs(totalPnL).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
            </div>
          </div>
        </div>

        <div className="divider-h" />

        {/* Analysis context */}
        <div style={{ padding: '10px 12px' }}>
          <div className="label" style={{ marginBottom: '8px' }}>Analysis Context</div>
          <div className="label" style={{ marginBottom: '4px', color: '#4C525E' }}>Risk Profile</div>
          <div className="toggle-group" style={{ width: '100%', marginBottom: '10px' }}>
            {['Conservative', 'Moderate', 'Aggressive'].map(r => (
              <button key={r} className={`toggle-btn${riskProfile === r ? ' active' : ''}`}
                onClick={() => setRiskProfile(r)} style={{ flex: 1, fontSize: '10px', padding: '0 4px' }}>
                {r.slice(0, 4)}
              </button>
            ))}
          </div>
          <div className="label" style={{ marginBottom: '4px', color: '#4C525E' }}>Horizon</div>
          <div className="toggle-group" style={{ width: '100%' }}>
            {['Short', 'Medium', 'Long'].map(h => (
              <button key={h} className={`toggle-btn${horizon === h ? ' active' : ''}`}
                onClick={() => setHorizon(h)} style={{ flex: 1, fontSize: '10px' }}>
                {h}
              </button>
            ))}
          </div>
        </div>

        <div className="divider-h" />

        {/* Quick queries */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          <div style={{ padding: '6px 12px' }}>
            <div className="label" style={{ marginBottom: '4px' }}>Quick Queries</div>
          </div>
          {displayQueries.map((q, i) => (
            <button key={i} onClick={() => handleSend(q)} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              width: '100%', height: '32px', padding: '0 12px',
              background: 'transparent', border: 'none', borderBottom: '1px solid #1E222D',
              textAlign: 'left', cursor: 'pointer', color: '#787B86', fontSize: '12px',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#363A45'; e.currentTarget.style.color = '#D1D4DC' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#787B86' }}
            >
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{q}</span>
              <span style={{ marginLeft: '6px', flexShrink: 0, fontSize: '10px' }}>→</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Right panel: chat ─────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
          {messages.length === 0 && !isStreaming ? (
            <div style={{ textAlign: 'center', marginTop: '60px' }}>
              <Logo collapsed />
              <div style={{ marginTop: '16px', fontSize: '13px', color: '#4C525E' }}>
                Select a quick query or type your question below.
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, i) => (
                msg.role === 'user'
                  ? <UserMessage key={i} content={msg.content}
                      timestamp={new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })} />
                  : <AIMessage key={i} content={msg.content} sources={msg.sources} toolCalls={msg.tool_calls} />
              ))}
              {isStreaming && streamingContent && <AIMessage content={streamingContent} />}
              {isStreaming && !streamingContent && (
                <div style={{ paddingLeft: '0' }}><LoadingSpinner size={14} text="Analyzing..." /></div>
              )}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        {/* Input bar */}
        <div style={{
          background: '#1E222D',
          borderTop: '1px solid #2A2E39',
          padding: '10px 16px',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              ref={inputRef}
              className="input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
              placeholder="Ask about markets, stocks, or your portfolio..."
              disabled={isStreaming}
              style={{ fontSize: '13px', background: '#2A2E39' }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isStreaming}
              style={{
                width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: input.trim() && !isStreaming ? '#2962FF' : 'transparent',
                border: 'none', borderRadius: '4px', cursor: input.trim() ? 'pointer' : 'default',
                flexShrink: 0, transition: 'background 150ms',
              }}
            >
              <Send size={14} style={{ color: input.trim() && !isStreaming ? '#131722' : '#4C525E' }} />
            </button>
          </div>
          <div className="text-xs" style={{ color: '#4C525E', marginTop: '4px' }}>
            Powered by Claude · Data from NSE/BSE
          </div>
        </div>
      </div>
    </div>
  )
}
