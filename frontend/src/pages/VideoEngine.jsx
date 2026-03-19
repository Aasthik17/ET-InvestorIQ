/**
 * VideoEngine — AI market video generation page.
 */
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Video, Play, Loader2, Check, AlertCircle, RefreshCw } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { videoAPI } from '../services/api'
import LoadingSpinner from '../components/common/LoadingSpinner'

const STATUS_ICONS = {
  QUEUED: Loader2,
  PROCESSING: Loader2,
  COMPLETE: Check,
  FAILED: AlertCircle,
}

const STATUS_COLORS = {
  QUEUED: 'text-muted',
  PROCESSING: 'text-accent',
  COMPLETE: 'text-bull',
  FAILED: 'text-bear',
}

const PERIOD_OPTIONS = ['1W', '1M', '3M', '6M', '1Y']

const NSE_SYMBOLS_LIST = [
  'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
  'BAJFINANCE.NS', 'SBIN.NS', 'ITC.NS', 'TATAMOTORS.NS', 'SUNPHARMA.NS',
]

function VideoTypeCard({ vtype, selected, onClick }) {
  const isSelected = selected === vtype.video_type
  return (
    <motion.div
      whileHover={{ y: -2 }}
      onClick={onClick}
      className={`card cursor-pointer transition-all duration-200
        ${isSelected ? 'border-accent/60 bg-accent/8 glow-accent' : 'hover:border-accent/30'}`}
    >
      <div className="text-2xl mb-2">{vtype.icon}</div>
      <div className="text-sm font-bold text-text-base mb-1">{vtype.name}</div>
      <div className="text-xs text-muted mb-2 leading-snug">{vtype.description}</div>
      <div className="text-xs text-muted flex items-center gap-1">
        <Video size={10} /> {vtype.estimated_duration}
      </div>
    </motion.div>
  )
}

function JobCard({ job, onSelect }) {
  const StatusIcon = STATUS_ICONS[job.status] || Loader2
  const isProcessing = job.status === 'PROCESSING' || job.status === 'QUEUED'

  return (
    <div className={`card ${job.status === 'COMPLETE' ? 'card-hover cursor-pointer' : ''}`} onClick={() => job.status === 'COMPLETE' && onSelect(job)}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <StatusIcon
            size={16}
            className={`${STATUS_COLORS[job.status]} ${isProcessing ? 'animate-spin' : ''}`}
          />
          <span className="text-sm font-semibold text-text-base">{job.video_type}</span>
        </div>
        <span className={`badge ${job.status === 'COMPLETE' ? 'badge-bull' : job.status === 'FAILED' ? 'badge-bear' : 'badge-neutral'}`}>
          {job.status}
        </span>
      </div>

      <div className="text-xs text-muted mb-2">Job: {job.job_id}</div>

      {/* Progress bar (while processing) */}
      {isProcessing && (
        <div className="confidence-bar mb-2">
          <motion.div
            className="confidence-fill bg-accent"
            initial={{ width: '5%' }}
            animate={{ width: `${job.progress_pct || 20}%` }}
            transition={{ duration: 1 }}
          />
        </div>
      )}

      {/* Narration snippet */}
      {job.narration_script && (
        <p className="text-xs text-muted italic line-clamp-2 mt-1">
          "{job.narration_script.slice(0, 120)}..."
        </p>
      )}

      {/* Complete action */}
      {job.status === 'COMPLETE' && (
        <div className="mt-2 flex items-center gap-1 text-xs text-accent font-medium">
          <Play size={10} /> Click to view video
        </div>
      )}

      {job.error_message && (
        <div className="mt-2 text-xs text-bear">{job.error_message}</div>
      )}
    </div>
  )
}

function VideoPlayer({ job }) {
  const videoUrl = videoAPI.serveUrl(job.job_id)
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="card"
    >
      <div className="section-title">{job.video_type} — Generated Video</div>
      <div className="bg-surface rounded-xl overflow-hidden aspect-video flex items-center justify-center">
        <video
          src={videoUrl}
          controls
          autoPlay
          className="w-full h-full object-contain"
        >
          <source src={videoUrl} />
          {/* Fallback image for GIF/PNG */}
          <img src={videoUrl} alt="Generated market video" className="w-full h-full object-contain" />
        </video>
      </div>
      {job.narration_script && (
        <div className="mt-4 p-4 bg-surface rounded-xl border border-border">
          <div className="text-xs font-bold text-muted uppercase tracking-wider mb-2">📜 AI Narration Script</div>
          <p className="text-sm text-text-base leading-relaxed">{job.narration_script}</p>
        </div>
      )}
    </motion.div>
  )
}

export default function VideoEngine() {
  const [selectedType, setSelectedType] = useState('MARKET_WRAP')
  const [symbols, setSymbols] = useState(['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS'])
  const [period, setPeriod] = useState('1M')
  const [selectedJob, setSelectedJob] = useState(null)
  const [pollingId, setPollingId] = useState(null)

  const qc = useQueryClient()

  const { data: vtypes, isLoading: typesLoading } = useQuery({
    queryKey: ['video-types'],
    queryFn: videoAPI.types,
    staleTime: Infinity,
  })

  const { data: jobs } = useQuery({
    queryKey: ['video-jobs'],
    queryFn: () => videoAPI.jobs(10),
    refetchInterval: pollingId ? 3000 : false,
    staleTime: 0,
  })

  const { data: pollingJob } = useQuery({
    queryKey: ['video-job', pollingId],
    queryFn: () => videoAPI.job(pollingId),
    enabled: !!pollingId,
    refetchInterval: (data) => {
      if (!data) return 2000
      if (data.status === 'COMPLETE' || data.status === 'FAILED') return false
      return 2000
    },
    onSuccess: (data) => {
      if (data?.status === 'COMPLETE') {
        setPollingId(null)
        setSelectedJob(data)
        qc.invalidateQueries({ queryKey: ['video-jobs'] })
      }
    },
  })

  const generateMutation = useMutation({
    mutationFn: videoAPI.generate,
    onSuccess: (data) => {
      setPollingId(data.job_id)
      qc.invalidateQueries({ queryKey: ['video-jobs'] })
    },
  })

  const handleGenerate = () => {
    generateMutation.mutate({
      video_type: selectedType,
      symbols: symbols,
      duration_seconds: 60,
      date_range: period,
    })
  }

  const toggleSymbol = (sym) => {
    setSymbols(prev =>
      prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym].slice(0, 8)
    )
  }

  const types = Array.isArray(vtypes) ? vtypes : []
  const jobList = Array.isArray(jobs) ? jobs : []

  return (
    <div className="p-4 lg:p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-base">AI Market Video Engine</h1>
        <p className="text-muted text-sm mt-0.5">Generate narrated market analysis videos in seconds</p>
      </div>

      {/* Video type selector */}
      <div>
        <h2 className="section-title">Select Video Type</h2>
        {typesLoading ? (
          <div className="flex justify-center py-8"><LoadingSpinner /></div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
            {types.map(vt => (
              <VideoTypeCard
                key={vt.video_type}
                vtype={vt}
                selected={selectedType}
                onClick={() => setSelectedType(vt.video_type)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Options */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Symbol selection */}
        <div className="card">
          <div className="section-title text-sm">Stock Universe ({symbols.length} selected)</div>
          <div className="flex flex-wrap gap-1.5">
            {NSE_SYMBOLS_LIST.map(sym => (
              <button
                key={sym}
                onClick={() => toggleSymbol(sym)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors
                  ${symbols.includes(sym) ? 'bg-accent/20 text-accent border border-accent/40' : 'bg-surface border border-border text-muted hover:text-text-base'}`}
              >
                {sym.replace('.NS', '')}
              </button>
            ))}
          </div>
        </div>

        {/* Period + Generate */}
        <div className="card">
          <div className="section-title text-sm">Date Range</div>
          <div className="flex gap-1.5 flex-wrap mb-4">
            {PERIOD_OPTIONS.map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors
                  ${period === p ? 'bg-accent text-white' : 'bg-surface border border-border text-muted hover:text-text-base'}`}
              >
                {p}
              </button>
            ))}
          </div>

          <button
            onClick={handleGenerate}
            disabled={generateMutation.isPending || !!pollingId}
            className="btn-primary w-full justify-center disabled:opacity-50"
          >
            {generateMutation.isPending || pollingId ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Video size={16} />
                Generate Video
              </>
            )}
          </button>

          {/* Active job progress */}
          {pollingId && pollingJob && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-muted mb-1">
                <span>Processing…</span>
                <span>{pollingJob.progress_pct || 0}%</span>
              </div>
              <div className="confidence-bar">
                <motion.div
                  className="confidence-fill bg-accent"
                  animate={{ width: `${pollingJob.progress_pct || 10}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Video player */}
      <AnimatePresence>
        {selectedJob?.status === 'COMPLETE' && (
          <VideoPlayer key={selectedJob.job_id} job={selectedJob} />
        )}
      </AnimatePresence>

      {/* Job history */}
      {jobList.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="section-title mb-0">Recent Jobs</h2>
            <button onClick={() => qc.invalidateQueries({ queryKey: ['video-jobs'] })} className="text-xs text-muted hover:text-text-base flex items-center gap-1">
              <RefreshCw size={11} /> Refresh
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {jobList.map(job => (
              <JobCard key={job.job_id} job={job} onSelect={setSelectedJob} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
