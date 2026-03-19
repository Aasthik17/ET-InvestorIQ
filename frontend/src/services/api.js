/**
 * ET InvestorIQ — API Service
 * Axios instance with interceptors + typed endpoint functions.
 */

import axios from 'axios'

// ─── Axios instance ─────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error normalization
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Request failed'
    console.error('[API Error]', message, error.config?.url)
    return Promise.reject(new Error(message))
  }
)

// ─── Market endpoints ────────────────────────────────────────────────────────
export const marketAPI = {
  overview: () => api.get('/market/overview'),
  sectors: () => api.get('/market/sectors'),
  ipos: () => api.get('/market/ipo'),
  stock: (symbol) => api.get(`/market/stock/${symbol}`),
  news: (symbol) => api.get(`/market/news/${symbol}`),
}

// ─── Opportunity Radar ───────────────────────────────────────────────────────
export const radarAPI = {
  signals: (params = {}) => api.get('/radar/signals', { params }),
  refresh: () => api.get('/radar/signals/refresh'),
  signal: (id) => api.get(`/radar/signals/${id}`),
  insider: (params = {}) => api.get('/radar/insider', { params }),
  bulkDeals: () => api.get('/radar/bulk-deals'),
  filings: (symbol) => api.get('/radar/filings', { params: { symbol } }),
  summary: () => api.get('/radar/summary'),
  fiiDii: (days) => api.get('/radar/fii-dii', { params: { days } }),
}

// ─── Chart Intelligence ──────────────────────────────────────────────────────
export const chartsAPI = {
  scan: (symbol, period = '1y') => api.get(`/charts/scan/${symbol}`, { params: { period } }),
  universe: (params = {}) => api.get('/charts/scan/universe/all', { params }),
  levels: (symbol) => api.get(`/charts/levels/${symbol}`),
  ohlcv: (symbol, period = '1y', interval = '1d') =>
    api.get(`/charts/ohlcv/${symbol}`, { params: { period, interval } }),
  explain: (patternData) => api.post('/charts/explain', patternData),
}

// ─── Market Chat ─────────────────────────────────────────────────────────────
export const chatAPI = {
  message: (request) => api.post('/chat/message', request),
  portfolioAnalyze: (portfolio) => api.post('/chat/portfolio/analyze', portfolio),
  suggestions: (symbol) => api.get('/chat/suggestions', { params: { symbol } }),
}

// ─── Video Engine ─────────────────────────────────────────────────────────────
export const videoAPI = {
  types: () => api.get('/video/types'),
  generate: (request) => api.post('/video/generate', request),
  job: (jobId) => api.get(`/video/job/${jobId}`),
  jobs: (limit = 20) => api.get('/video/jobs', { params: { limit } }),
  serveUrl: (jobId) => `/api/video/serve/${jobId}`,
}

// ─── Health check ────────────────────────────────────────────────────────────
export const healthCheck = () => api.get('/health')

// ─── SSE Streaming helper ────────────────────────────────────────────────────
/**
 * Open a Server-Sent Events connection for chat streaming.
 * @param {Object} request - ChatRequest payload
 * @param {Function} onChunk - Callback for each text chunk
 * @param {Function} onDone - Callback when stream completes
 * @param {Function} onError - Callback on error
 * @returns {Function} Cleanup function to abort the request
 */
export function streamChat(request, onChunk, onDone, onError) {
  const controller = new AbortController()

  fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        onDone?.()
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'text') onChunk?.(data.content)
            else if (data.type === 'done') onDone?.()
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError?.(err)
    }
  })

  return () => controller.abort()
}

export default api
