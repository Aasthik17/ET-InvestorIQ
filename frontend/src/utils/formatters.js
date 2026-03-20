/**
 * ET InvestorIQ — Number & Date Formatters
 * All formatting utilities for Indian financial data display.
 */

/**
 * Format a number in Indian number system (lakhs, crores).
 * 1234567 → "12,34,567"   1234567890 → "1,23,45,67,890"
 */
export function formatIndianNumber(num, decimals = 2) {
  if (num === null || num === undefined || num === '') return '—'
  const n = Number(num)
  if (isNaN(n)) return '—'
  return n.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/**
 * Format a rupee price with ₹ symbol and 2 decimal places.
 * 2934.55 → "₹2,934.55"
 */
export function formatPrice(num) {
  if (num === null || num === undefined || num === '') return '—'
  const n = Number(num)
  if (isNaN(n) || n === 0) return '—'
  return `₹${formatIndianNumber(n, 2)}`
}

/**
 * Format a value in crores with ₹ Cr suffix.
 * 1234.56 → "₹1,234.56 Cr"    1234567.89 → "₹1,234.57K Cr"
 */
export function formatCrores(cr) {
  if (cr === null || cr === undefined) return '—'
  const n = Number(cr)
  if (isNaN(n)) return '—'
  if (Math.abs(n) >= 1_00_000)
    return `₹${formatIndianNumber((n / 1_00_000).toFixed(2), 2)}L Cr`
  if (Math.abs(n) >= 1000)
    return `₹${formatIndianNumber((n / 1000).toFixed(2), 2)}K Cr`
  return `₹${formatIndianNumber(n.toFixed(2), 2)} Cr`
}

/**
 * Format a change percentage with sign.
 * Returns { text: '+2.34%', cls: 'text-bull' }
 */
export function formatPct(pct) {
  if (pct === null || pct === undefined) return { text: '—', cls: 'text-muted' }
  const n    = Number(pct)
  if (isNaN(n)) return { text: '—', cls: 'text-muted' }
  const sign = n >= 0 ? '+' : ''
  const cls  = n > 0 ? 'text-bull' : n < 0 ? 'text-bear' : 'text-muted'
  return { text: `${sign}${n.toFixed(2)}%`, cls }
}

/**
 * Format a number as volume shorthand.
 * 12345678 → "1.23 Cr"    123456 → "1.23 L"    1234 → "1.2K"
 */
export function formatVolume(vol) {
  if (!vol) return '—'
  const n = Number(vol)
  if (isNaN(n)) return '—'
  if (n >= 1e7) return `${(n / 1e7).toFixed(2)} Cr`
  if (n >= 1e5) return `${(n / 1e5).toFixed(2)} L`
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return String(n)
}

/**
 * Format relative time: "just now", "3m ago", "2h ago", "Mon 3:45 PM"
 */
export function formatRelativeTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return ''
  const now  = new Date()
  const diff = Math.floor((now - date) / 1000)
  if (diff < 60)    return 'just now'
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return date.toLocaleDateString('en-IN', {
    weekday: 'short', hour: '2-digit', minute: '2-digit'
  })
}

/**
 * Format a date string (DD-MMM-YYYY or ISO) to "17 Jan" compact display.
 */
export function formatShortDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) {
    // Try parsing DD-MMM-YYYY format (NSE format)
    const parts = String(dateStr).split('-')
    if (parts.length === 3) {
      return `${parts[0]} ${parts[1]}`
    }
    return dateStr
  }
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

/**
 * Format a large number in compact Indian notation.
 * 1965432 Cr → "₹196.54 T" (trillions)  or  "₹19.65 L Cr"
 */
export function formatMarketCap(crores) {
  if (!crores) return '—'
  const n = Number(crores)
  if (n >= 1_00_00_000) return `₹${(n / 1_00_00_000).toFixed(2)} T Cr`
  if (n >= 1_00_000)    return `₹${(n / 1_00_000).toFixed(2)} L Cr`
  if (n >= 1000)        return `₹${(n / 1000).toFixed(2)}K Cr`
  return `₹${n.toFixed(0)} Cr`
}

/**
 * Clamp a value between min and max.
 */
export function clamp(val, min, max) {
  return Math.min(Math.max(val, min), max)
}
