/**
 * StockBadge — always the same style, no sector colors.
 * bg-tertiary, JetBrains Mono, 3px border-radius.
 */
export default function StockBadge({ symbol }) {
  const clean = symbol?.replace('.NS', '').replace('.BO', '') || '—'
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      height: '18px',
      padding: '0 6px',
      background: '#2A2E39',
      borderRadius: '3px',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '11px',
      fontWeight: 500,
      color: '#D1D4DC',
      letterSpacing: '-0.01em',
      whiteSpace: 'nowrap',
    }}>
      {clean}
    </span>
  )
}
