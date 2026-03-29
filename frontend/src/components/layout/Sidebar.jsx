/**
 * Sidebar — 220px left navigation, Kite/TradingView left-border convention.
 * Active nav uses 2px left border in accent (not a pill background).
 */
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Radio, CandlestickChart, MessageSquare, Video, Target,
} from 'lucide-react'
import Logo from './Logo'

const NAV_ITEMS = [
  { to: '/',       icon: LayoutDashboard,  label: 'Dashboard' },
  { to: '/radar',  icon: Radio,             label: 'Radar' },
  { to: '/charts', icon: CandlestickChart,  label: 'Charts' },
  { to: '/chat',   icon: MessageSquare,     label: 'Chat' },
  { to: '/video',      icon: Video,            label: 'Video' },
  { to: '/scenarios',  icon: Target,           label: 'Scenarios' },
]

function MarketStatusWidget() {
  const now = new Date()
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }))
  const h = ist.getHours(), m = ist.getMinutes()
  const day = ist.getDay()
  const mins = h * 60 + m
  const open = day >= 1 && day <= 5 && mins >= 555 && mins < 930

  const istStr = ist.toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata',
  })

  // Next event
  let nextEvent = ''
  if (!open) {
    nextEvent = day === 0 || day === 6 ? 'Opens Mon 9:15 AM' : mins < 555 ? 'Opens 9:15 AM' : 'Opens Mon 9:15 AM'
  } else {
    nextEvent = 'Closes 3:30 PM'
  }

  return (
    <div style={{ padding: '12px', borderTop: '1px solid #2A2E39' }}>
      <div className="label" style={{ marginBottom: '6px' }}>Market Status</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: open ? '#26A69A' : '#EF5350',
        }} />
        <span className="text-xs" style={{ color: open ? '#26A69A' : '#EF5350' }}>
          NSE {open ? 'Open' : 'Closed'}
        </span>
      </div>
      <div className="price text-xs" style={{ color: '#D1D4DC', marginBottom: '2px' }}>{istStr} IST</div>
      <div className="text-xs" style={{ color: '#4C525E' }}>{nextEvent}</div>
    </div>
  )
}

export default function Sidebar() {
  return (
    <nav style={{
      width: '220px',
      minWidth: '220px',
      height: '100%',
      background: '#1E222D',
      borderRight: '1px solid #2A2E39',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
    }}>
      {/* Nav items */}
      <div style={{ flex: 1, paddingTop: '8px' }}>
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Icon size={15} style={{ flexShrink: 0 }} />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>

      {/* Market status widget at bottom */}
      <MarketStatusWidget />
    </nav>
  )
}
