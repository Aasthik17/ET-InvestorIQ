/**
 * ConfidenceMeter — 3px bar, 64px wide, percentage below.
 * NO color animation, NO theatrics.
 * Colors: <50% neutral, 50-70% amber, >70% bull.
 */
export default function ConfidenceMeter({ score = 0, width = 64 }) {
  const pct = Math.round(score * 100)
  const color = pct >= 70 ? '#26A69A' : pct >= 50 ? '#F59E0B' : '#787B86'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', width }}>
      <div style={{
        height: '3px',
        background: '#2A2E39',
        borderRadius: '2px',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: color,
          borderRadius: '2px',
          transition: 'width 300ms ease',
        }} />
      </div>
      <span className="price" style={{ fontSize: '11px', color: '#4C525E' }}>{pct}%</span>
    </div>
  )
}
