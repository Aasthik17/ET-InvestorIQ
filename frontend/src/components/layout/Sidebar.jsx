/**
 * Sidebar — Left navigation panel with module links.
 */
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Radar, BarChart2, MessageSquare, Video
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', tooltip: 'Overview' },
  { to: '/radar', icon: Radar, label: 'Radar', tooltip: 'Opportunity Radar' },
  { to: '/charts', icon: BarChart2, label: 'Charts', tooltip: 'Chart Intelligence' },
  { to: '/chat', icon: MessageSquare, label: 'Chat', tooltip: 'AI Market Chat' },
  { to: '/video', icon: Video, label: 'Video', tooltip: 'Video Engine' },
]

export default function Sidebar() {
  return (
    <nav className="w-16 lg:w-56 bg-card border-r border-border flex flex-col flex-shrink-0 h-screen">
      {/* Logo (mobile only — desktop shows in navbar) */}
      <div className="h-14 flex items-center justify-center lg:hidden border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
          <span className="text-white font-bold text-xs">ET</span>
        </div>
      </div>

      {/* Brand (desktop) */}
      <div className="hidden lg:flex items-center gap-3 px-4 h-14 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent-light flex items-center justify-center">
          <span className="text-white font-bold text-sm">ET</span>
        </div>
        <div>
          <div className="text-sm font-bold text-text-base leading-none">InvestorIQ</div>
          <div className="text-xs text-muted">AI Market Intelligence</div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 py-4 px-2 flex flex-col gap-1">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            title={label}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group
              ${isActive
                ? 'bg-accent/15 text-accent border border-accent/30'
                : 'text-muted hover:text-text-base hover:bg-border'
              }`
            }
          >
            <Icon size={18} className="flex-shrink-0" />
            <span className="hidden lg:block text-sm font-medium">{label}</span>
          </NavLink>
        ))}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border">
        <div className="hidden lg:block text-xs text-muted text-center">
          <div className="font-semibold text-text-base">ET InvestorIQ</div>
          <div className="text-muted mt-0.5">Gen AI Hackathon 2026</div>
        </div>
      </div>
    </nav>
  )
}
