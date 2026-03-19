/**
 * LoadingSpinner — Animated loading indicator.
 */
import { RefreshCw } from 'lucide-react'

export default function LoadingSpinner({ size = 'md', text = '' }) {
  const sizes = { sm: 14, md: 20, lg: 32 }
  const px = sizes[size] || 20

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <RefreshCw size={px} className="text-accent animate-spin" />
      {text && <p className="text-muted text-sm">{text}</p>}
    </div>
  )
}
