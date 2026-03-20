/** LoadingSpinner — CSS border-based, no SVG paths. */
export default function LoadingSpinner({ size = 16, text = '' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
      <div
        className="spinner"
        style={{ width: size, height: size, borderWidth: size > 20 ? 3 : 2 }}
      />
      {text && (
        <span className="text-xs" style={{ color: '#4C525E' }}>{text}</span>
      )}
    </div>
  )
}
