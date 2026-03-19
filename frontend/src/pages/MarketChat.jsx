/**
 * MarketChat — Portfolio-aware AI chat with streaming responses.
 */
import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Square, Trash2, MessageSquare, Bot, User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useQuery } from '@tanstack/react-query'
import { useChat } from '../hooks/useChat'
import { chatAPI } from '../services/api'
import LoadingSpinner from '../components/common/LoadingSpinner'

const STARTER_PROMPTS = [
  'What are the top NSE large-cap opportunities right now?',
  'Analyze HDFC Bank vs ICICI Bank on key metrics',
  'Which sectors are showing the strongest momentum?',
  'Explain the FII/DII flow impact on Nifty',
  'Give me a risk assessment of holding only IT stocks',
]

function MessageBubble({ msg, isLast }) {
  const isUser = msg.role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
        ${isUser ? 'bg-accent/20 text-accent' : 'bg-bull/15 text-bull'}`}>
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed
        ${isUser
          ? 'bg-accent/15 text-text-base border border-accent/25 rounded-tr-sm'
          : 'bg-card text-text-base border border-border rounded-tl-sm'
        }`}>
        {isUser ? (
          <p>{msg.content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
        {msg.sources && msg.sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border flex flex-wrap gap-1">
            {msg.sources.map((s, i) => (
              <span key={i} className="badge badge-accent">{s.name}</span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

function StreamingBubble({ content }) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-bull/15 text-bull">
        <Bot size={14} />
      </div>
      <div className="max-w-[80%] bg-card text-text-base border border-border rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed">
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{content || '...'}</ReactMarkdown>
        </div>
        <span className="inline-block w-2 h-4 bg-accent animate-pulse ml-0.5 rounded-sm" />
      </div>
    </div>
  )
}

export default function MarketChat() {
  const { messages, isStreaming, streamingContent, sendMessage, clearChat, stopStreaming } = useChat()
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const { data: suggestions } = useQuery({
    queryKey: ['chat-suggestions'],
    queryFn: () => chatAPI.suggestions(),
    staleTime: 60_000,
  })

  const displaySuggestions = suggestions?.length > 0
    ? suggestions.slice(0, 5).map(s => s.question)
    : STARTER_PROMPTS

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const handleSubmit = (e) => {
    e?.preventDefault()
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    sendMessage(text, null, true)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-bull to-emerald-400 flex items-center justify-center">
            <MessageSquare size={16} className="text-black" />
          </div>
          <div>
            <div className="font-bold text-text-base text-sm">Market Chat</div>
            <div className="text-xs text-muted">Portfolio-aware · Tool-augmented · Claude Sonnet</div>
          </div>
        </div>
        {messages.length > 0 && (
          <button onClick={clearChat} className="btn-secondary text-xs px-3 py-1.5">
            <Trash2 size={12} />
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            {/* Welcome */}
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-bull to-emerald-400 flex items-center justify-center mx-auto mb-4">
                <Bot size={28} className="text-black" />
              </div>
              <h2 className="text-xl font-bold text-text-base mb-2">ET InvestorIQ AI</h2>
              <p className="text-muted text-sm max-w-md">
                Ask me anything about stocks, markets, or your portfolio.
                I'll use live data tools to give you informed answers.
              </p>
            </div>

            {/* Starter prompts */}
            <div className="w-full max-w-xl space-y-2">
              {displaySuggestions.map((prompt, i) => (
                <motion.button
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                  onClick={() => { setInput(prompt); sendMessage(prompt, null, true) }}
                  className="w-full text-left px-4 py-3 bg-card border border-border hover:border-accent/40 rounded-xl text-sm text-muted hover:text-text-base transition-all"
                >
                  {prompt}
                </motion.button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto w-full">
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} isLast={i === messages.length - 1} />
            ))}
            {isStreaming && streamingContent && <StreamingBubble content={streamingContent} />}
            {isStreaming && !streamingContent && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-bull/15 text-bull flex items-center justify-center">
                  <Bot size={14} />
                </div>
                <div className="bg-card border border-border rounded-xl px-4 py-3">
                  <LoadingSpinner size="sm" text="Thinking..." />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border px-4 py-3 flex-shrink-0">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSubmit} className="flex gap-2 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about stocks, market trends, or your portfolio..."
                rows={1}
                className="input-dark w-full resize-none text-sm pr-12 min-h-[44px] max-h-32 overflow-y-auto"
                style={{ height: 'auto' }}
                disabled={isStreaming}
              />
            </div>
            {isStreaming ? (
              <button
                type="button"
                onClick={stopStreaming}
                className="btn-secondary p-2.5 flex-shrink-0"
              >
                <Square size={16} className="text-bear" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                className="btn-primary p-2.5 flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Send size={16} />
              </button>
            )}
          </form>
          <div className="text-[10px] text-muted mt-1.5 text-center">
            Press Enter to send · Shift+Enter for new line · Uses live NSE/BSE data
          </div>
        </div>
      </div>
    </div>
  )
}
