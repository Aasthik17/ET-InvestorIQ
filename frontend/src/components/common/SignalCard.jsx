/**
 * SignalCard — Displays an individual market signal with confidence meter.
 */
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { motion } from 'framer-motion'

const SIGNAL_TYPE_LABELS = {
  INSIDER_TRADE: 'Insider',
  BULK_DEAL: 'Bulk Deal',
  FILING: 'Filing',
  FII_ACCUMULATION: 'FII Flow',
  CORPORATE_ACTION: 'Corp. Action',
  EARNINGS_SURPRISE: 'Earnings',
  PROMOTER_PLEDGE_CHANGE: 'Pledge',
}

export default function SignalCard({ signal, onClick, index = 0 }) {
  const isBull = signal.expected_impact === 'BULLISH'
  const isBear = signal.expected_impact === 'BEARISH'
  const Icon = isBull ? TrendingUp : isBear ? TrendingDown : Minus
  const confidence = Math.round((signal.confidence_score || 0) * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      onClick={onClick}
      className={`card cursor-pointer hover:border-accent/40 transition-all duration-200
        ${isBull ? 'signal-border-bull' : isBear ? 'signal-border-bear' : 'signal-border-neutral'}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
            ${isBull ? 'bg-bull/15' : isBear ? 'bg-bear/15' : 'bg-muted/15'}`}>
            <Icon size={16} className={isBull ? 'text-bull' : isBear ? 'text-bear' : 'text-muted'} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-bold text-text-base text-sm">{signal.symbol}</span>
              <span className={`badge ${isBull ? 'badge-bull' : isBear ? 'badge-bear' : 'badge-neutral'}`}>
                {signal.expected_impact}
              </span>
              <span className="badge badge-accent text-[10px]">
                {SIGNAL_TYPE_LABELS[signal.signal_type] || signal.signal_type}
              </span>
            </div>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <div className="text-xl font-bold text-text-base">{confidence}%</div>
          <div className="text-[10px] text-muted">Confidence</div>
        </div>
      </div>

      {/* Headline */}
      <p className="text-sm text-text-base font-medium leading-snug mb-2 line-clamp-2">
        {signal.headline}
      </p>

      {/* Confidence bar */}
      <div className="confidence-bar mb-2">
        <motion.div
          className={`confidence-fill ${isBull ? 'bg-bull' : isBear ? 'bg-bear' : 'bg-muted'}`}
          initial={{ width: 0 }}
          animate={{ width: `${confidence}%` }}
          transition={{ delay: index * 0.05 + 0.2, duration: 0.5 }}
        />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted">
        <span>{signal.signal_date || ''}</span>
        {signal.stock_price_at_signal && (
          <span>₹{signal.stock_price_at_signal?.toLocaleString('en-IN')}</span>
        )}
      </div>

      {/* AI analysis snippet */}
      {signal.ai_analysis && (
        <div className="mt-2 pt-2 border-t border-border">
          <p className="text-xs text-muted line-clamp-2 italic">
            "{signal.ai_analysis}"
          </p>
        </div>
      )}
    </motion.div>
  )
}
