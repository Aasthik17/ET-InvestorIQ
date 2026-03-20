/**
 * Logo — ET InvestorIQ brand mark.
 * Logomark: radar arc SVG (signal detection metaphor)
 * Wordmark: ET in brand orange + InvestorIQ in text-primary
 */
export default function Logo({ collapsed = false }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
      {/* Radar arc logomark */}
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" style={{ flexShrink: 0 }}>
        <path d="M6 22 Q6 6 22 6"  stroke="#2962FF" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity="0.3"/>
        <path d="M6 22 Q6 11 17 11" stroke="#2962FF" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity="0.6"/>
        <path d="M6 22 Q6 16 12 16" stroke="#2962FF" strokeWidth="2.5" strokeLinecap="round" fill="none" opacity="1"/>
        <circle cx="6" cy="22" r="2.5" fill="#2962FF"/>
      </svg>
      {/* Wordmark — only shown in expanded sidebar / navbar */}
      {!collapsed && (
        <span style={{ display: 'flex', alignItems: 'baseline', gap: '0px', lineHeight: 1 }}>
          <span style={{
            color: '#F26522',
            fontWeight: 600,
            fontSize: '15px',
            letterSpacing: '-0.03em',
            fontFamily: 'Inter, sans-serif',
          }}>ET</span>
          <span style={{
            color: '#D1D4DC',
            fontWeight: 400,
            fontSize: '15px',
            letterSpacing: '-0.03em',
            marginLeft: '4px',
            fontFamily: 'Inter, sans-serif',
          }}>InvestorIQ</span>
        </span>
      )}
    </div>
  )
}
