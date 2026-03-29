import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import Navbar from './components/layout/Navbar'
import Sidebar from './components/layout/Sidebar'
import LoadingSpinner from './components/common/LoadingSpinner'

const Dashboard       = lazy(() => import('./pages/Dashboard'))
const OpportunityRadar = lazy(() => import('./pages/OpportunityRadar'))
const ChartIntelligence = lazy(() => import('./pages/ChartIntelligence'))
const MarketChat      = lazy(() => import('./pages/MarketChat'))
const VideoEngine     = lazy(() => import('./pages/VideoEngine'))
const ScenarioPack    = lazy(() => import('./pages/ScenarioPack'))

export default function App() {
  return (
    <BrowserRouter>
      {/* Full-height, no scroll on root */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: '#131722' }}>
        <Navbar />
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <Sidebar />
          <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <Suspense fallback={
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <LoadingSpinner size={20} text="Loading..." />
              </div>
            }>
              <Routes>
                <Route path="/"       element={<Dashboard />} />
                <Route path="/radar"  element={<OpportunityRadar />} />
                <Route path="/charts" element={<ChartIntelligence />} />
                <Route path="/chat"   element={<MarketChat />} />
                <Route path="/video"     element={<VideoEngine />} />
                <Route path="/scenarios" element={<ScenarioPack />} />
                <Route path="*"          element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
