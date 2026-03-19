import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import Navbar from './components/layout/Navbar'
import Sidebar from './components/layout/Sidebar'
import LoadingSpinner from './components/common/LoadingSpinner'

// Lazy load pages for performance
const Dashboard = lazy(() => import('./pages/Dashboard'))
const OpportunityRadar = lazy(() => import('./pages/OpportunityRadar'))
const ChartIntelligence = lazy(() => import('./pages/ChartIntelligence'))
const MarketChat = lazy(() => import('./pages/MarketChat'))
const VideoEngine = lazy(() => import('./pages/VideoEngine'))

/**
 * ET InvestorIQ — Root App Component
 * Provides routing, layout, and dark theme for all pages.
 */
export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-surface text-text-base overflow-hidden">
        {/* Sidebar navigation */}
        <Sidebar />

        {/* Main content area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Navbar />
          <main className="flex-1 overflow-y-auto">
            <Suspense fallback={
              <div className="flex items-center justify-center h-full">
                <LoadingSpinner size="lg" text="Loading module..." />
              </div>
            }>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/radar" element={<OpportunityRadar />} />
                <Route path="/charts" element={<ChartIntelligence />} />
                <Route path="/chat" element={<MarketChat />} />
                <Route path="/video" element={<VideoEngine />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
