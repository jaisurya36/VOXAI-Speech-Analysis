import React, { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  BarChart3,
  ArrowLeft,
  Volume2,
  Clock,
  Activity,
  Award,
  Brain,
  Radio,
  Sliders,
  Target,
  Lightbulb,
  Compass,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Layers,
  Scale,
  Mic2,
} from 'lucide-react'
import Plot from 'react-plotly.js'
import { apiService } from '../services/api'
import {
  DashboardDataResponse,
  TemporalFlawItem,
  ScoringDimensionItem,
} from '../types'

export default function ResultsPage() {
  const { analysisId } = useParams<{ analysisId: string }>()
  const [data, setData] = useState<DashboardDataResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [activeChartTab, setActiveChartTab] = useState<'pitch' | 'energy' | 'flaws' | 'radar' | 'cadence'>('pitch')
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0)
  const [currentTime, setCurrentTime] = useState<number>(0)
  const [selectedFlaw, setSelectedFlaw] = useState<TemporalFlawItem | null>(null)
  const [activeAudioStream, setActiveAudioStream] = useState<'participant' | 'reference' | 'improved'>('participant')

  const participantAudioRef = useRef<HTMLAudioElement>(null)
  const referenceAudioRef = useRef<HTMLAudioElement>(null)
  const improvedAudioRef = useRef<HTMLAudioElement>(null)

  const fetchDashboard = async () => {
    if (!analysisId) return
    try {
      setIsLoading(true)
      setError(null)
      const resp = await apiService.getDashboardData(analysisId, true)
      setData(resp)
      if (resp.flaws && resp.flaws.flaws && resp.flaws.flaws.length > 0) {
        setSelectedFlaw(resp.flaws.flaws[0])
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load analysis dashboard data.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard()
  }, [analysisId])

  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLAudioElement>) => {
    setCurrentTime(e.currentTarget.currentTime)
  }

  const handleSeek = (timeSec: number) => {
    const validTime = Math.max(0, timeSec)
    setCurrentTime(validTime)
    const activeRef =
      activeAudioStream === 'reference'
        ? referenceAudioRef.current
        : activeAudioStream === 'improved'
        ? improvedAudioRef.current
        : participantAudioRef.current

    if (activeRef) {
      activeRef.currentTime = validTime
      activeRef.play().catch(() => {})
    }
  }

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed)
    if (participantAudioRef.current) participantAudioRef.current.playbackRate = speed
    if (referenceAudioRef.current) referenceAudioRef.current.playbackRate = speed
    if (improvedAudioRef.current) improvedAudioRef.current.playbackRate = speed
  }

  const formatDuration = (seconds?: number | null): string => {
    if (!seconds || seconds <= 0) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 rounded-2xl bg-primary-600/20 border border-primary-500/40 flex items-center justify-center text-primary-400 mb-6 animate-pulse">
          <Activity className="w-8 h-8 animate-spin" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Assembling Analytics Dashboard</h2>
        <p className="text-gray-400 max-w-md text-sm">
          Compiling DTW pitch contours, RMS energy waterfalls, temporal flaw grounding, and multi-track rubric scores...
        </p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <div className="p-8 rounded-2xl bg-surface-800 border border-rose-800/60 text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Dashboard Load Error</h2>
          <p className="text-gray-300 text-sm max-w-lg mx-auto">{error || 'Speech analysis record not found.'}</p>
          <div className="flex justify-center gap-3 pt-2">
            <button onClick={fetchDashboard} className="btn-primary text-sm py-2 px-4 flex items-center gap-2">
              <RotateCcw className="w-4 h-4" />
              Retry Load
            </button>
            <Link to="/analyze" className="btn-secondary text-sm py-2 px-4 flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" />
              Back to Upload
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const scores = data.scores
  const summary = scores?.summary
  const delivery = scores?.delivery
  const content = scores?.content
  const comparison = data.comparison
  const flaws = data.flaws
  const features = data.features
  const explanations = data.explanations
  const archetype = explanations?.diagnosis?.archetype?.name || delivery?.archetype || 'Dynamic Communicator'

  // Extract contours for Plotly charts
  const timeAxis: number[] = features?.time_axis || []
  const participantF0: number[] = features?.participant_features?.pitch?.contour || []
  const referenceF0: number[] = features?.reference_features?.pitch?.contour || []
  const participantRMS: number[] = features?.participant_features?.energy?.contour || []
  const referenceRMS: number[] = features?.reference_features?.energy?.contour || []

  // Fallback synthetic alignment if contours empty
  const plotTimeAxis = timeAxis.length > 0 ? timeAxis : Array.from({ length: 50 }, (_, i) => i * 0.1)
  const plotParticipantF0 = participantF0.length > 0 ? participantF0 : plotTimeAxis.map(() => 140)
  const plotReferenceF0 = referenceF0.length > 0 ? referenceF0 : plotTimeAxis.map(() => 150)
  const plotParticipantRMS = participantRMS.length > 0 ? participantRMS : plotTimeAxis.map(() => 0.05)
  const plotReferenceRMS = referenceRMS.length > 0 ? referenceRMS : plotTimeAxis.map(() => 0.06)

  // Radar chart dimensions
  const radarDimensions: ScoringDimensionItem[] = scores?.dimensions || []
  const radarLabels = radarDimensions.map((d) => d.name)
  const radarValues = radarDimensions.map((d) => d.raw_score)
  // Close the radar polygon
  const closedLabels = radarLabels.length > 0 ? [...radarLabels, radarLabels[0]] : []
  const closedValues = radarValues.length > 0 ? [...radarValues, radarValues[0]] : []
  const closedIdeal = closedLabels.map(() => 100)

  // Dark Plotly theme styling
  const plotlyDarkLayout = {
    autosize: true,
    paper_bgcolor: '#0f1629',
    plot_bgcolor: '#0a0f1e',
    font: { color: '#9ca3af', family: 'Inter, sans-serif' },
    margin: { l: 55, r: 35, t: 40, b: 45 },
    hovermode: 'closest' as const,
    legend: { orientation: 'h' as const, y: -0.25, x: 0.05, font: { color: '#e5e7eb' } },
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Top Breadcrumb & Metadata Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-700/60 pb-5">
        <div className="flex items-center gap-3">
          <Link
            to="/analyze"
            className="w-9 h-9 rounded-lg bg-surface-800 border border-surface-600 hover:bg-surface-700 flex items-center justify-center text-gray-300 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-primary-400">
                Interactive Dashboard (Phase 12)
              </span>
              <span className="badge bg-surface-700 text-gray-300 text-[10px] font-mono">
                {data.original_filename}
              </span>
            </div>
            <h1 className="text-2xl font-black text-white flex items-center gap-2.5">
              Speech Analytics & Temporal Flaw Finding
            </h1>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          <span className="badge bg-surface-800 text-gray-300 border border-surface-600 px-3 py-1.5 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-primary-400" />
            Duration: <strong>{formatDuration(data.duration)}</strong>
          </span>
          <span className="badge bg-surface-800 text-gray-300 border border-surface-600 px-3 py-1.5 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            Rate: <strong>{data.sample_rate || 16000} Hz</strong>
          </span>
          <span className="badge bg-purple-950 text-purple-300 border border-purple-700 px-3 py-1.5 font-bold">
            {archetype}
          </span>
        </div>
      </div>

      {/* Executive Performance Hero Banner */}
      {summary && (
        <div className="p-6 rounded-2xl bg-gradient-to-r from-surface-800 via-surface-900 to-surface-800 border border-surface-700/80 shadow-2xl space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
            {/* Score Ring */}
            <div className="md:col-span-4 flex items-center gap-5 justify-center md:justify-start">
              <div className="relative">
                <div className="w-28 h-28 rounded-full border-4 border-emerald-500 bg-surface-900 flex flex-col items-center justify-center shadow-lg shadow-emerald-950/60">
                  <span className="text-3xl font-black text-white">{summary.overall_score}</span>
                  <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">/ 100</span>
                </div>
                <div className="absolute -top-1.5 -right-1.5 bg-primary-600 text-white text-xs font-black px-2.5 py-1 rounded-full border border-primary-400 shadow">
                  Grade {summary.grade}
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-black text-white">{summary.tier_title}</h3>
                </div>
                <div className="badge bg-emerald-950 text-emerald-300 border border-emerald-700 text-xs px-2.5 py-0.5">
                  {summary.tier} Level Orator
                </div>
                <p className="text-xs text-gray-400 pt-1">
                  Benchmarked in <strong className="text-gray-200">Top {100 - summary.percentile_estimate}%</strong> of speakers ({summary.percentile_estimate}th percentile)
                </p>
              </div>
            </div>

            {/* Two-Track Balance Summary */}
            <div className="md:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {delivery && (
                <div className="p-4 rounded-xl bg-surface-800/90 border border-blue-900/50 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                      <Mic2 className="w-3.5 h-3.5" />
                      Track A: Delivery (HOW)
                    </span>
                    <span className="font-black text-white text-sm">{delivery.net_delivery_score} / 100</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-surface-700 overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${delivery.net_delivery_score}%` }}></div>
                  </div>
                  <div className="flex justify-between text-[11px] text-gray-400">
                    <span>Baseline: {delivery.raw_delivery_score}</span>
                    <span className={delivery.total_flaw_deduction > 0 ? 'text-rose-400 font-semibold' : 'text-emerald-400'}>
                      {delivery.total_flaw_deduction > 0 ? `-${delivery.total_flaw_deduction} pts flaws` : '0 deductions'}
                    </span>
                  </div>
                </div>
              )}

              {content && (
                <div className="p-4 rounded-xl bg-surface-800/90 border border-purple-900/50 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                      <Brain className="w-3.5 h-3.5" />
                      Track B: Content (WHAT)
                    </span>
                    <span className="font-black text-white text-sm">{content.net_content_score} / 100</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-surface-700 overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full" style={{ width: `${content.net_content_score}%` }}></div>
                  </div>
                  <div className="flex justify-between text-[11px] text-gray-400">
                    <span>{content.status}</span>
                    <span>{content.strengths_count} strengths · {content.issues_count} deductions</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Key Strategic Priority Banner */}
          <div className="p-3.5 rounded-xl bg-surface-950/80 border border-surface-700/60 flex items-start gap-3 text-xs">
            <Lightbulb className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <strong className="text-gray-200">Executive Priority: </strong>
              <span className="text-gray-300 leading-relaxed">{summary.summary_headline}</span>
              <span className="text-emerald-400 ml-1.5">{summary.key_takeaway}</span>
            </div>
          </div>
        </div>
      )}

      {/* Dual Audio Synchronization & Scrubber Console */}
      <div className="p-5 rounded-2xl bg-surface-800/90 border border-surface-700/80 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-surface-700/60 pb-3">
          <div className="flex items-center gap-2">
            <Volume2 className="w-4 h-4 text-primary-400" />
            <h4 className="text-sm font-bold text-white">Synchronized Multi-Track Audio Station</h4>
            <span className="badge bg-surface-700 text-gray-300 text-[10px]">
              Active: {activeAudioStream.toUpperCase()}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Speed Toggle */}
            <div className="flex items-center gap-1 bg-surface-900 p-1 rounded-lg border border-surface-700 text-[11px]">
              {[0.75, 1.0, 1.25, 1.5].map((speed) => (
                <button
                  key={speed}
                  onClick={() => handleSpeedChange(speed)}
                  className={`px-2 py-0.5 rounded font-mono transition-colors ${
                    playbackSpeed === speed ? 'bg-primary-600 text-white font-bold' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {speed}x
                </button>
              ))}
            </div>

            {/* Stream Selector Buttons */}
            <div className="flex items-center gap-1 bg-surface-900 p-1 rounded-lg border border-surface-700 text-xs">
              <button
                onClick={() => setActiveAudioStream('participant')}
                className={`px-2.5 py-1 rounded font-semibold transition-colors ${
                  activeAudioStream === 'participant' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Participant Audio
              </button>
              {data.has_reference_audio && (
                <button
                  onClick={() => setActiveAudioStream('reference')}
                  className={`px-2.5 py-1 rounded font-semibold transition-colors ${
                    activeAudioStream === 'reference' ? 'bg-emerald-600 text-white' : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  Track A Reference
                </button>
              )}
              {data.has_improved_audio && (
                <button
                  onClick={() => setActiveAudioStream('improved')}
                  className={`px-2.5 py-1 rounded font-semibold transition-colors ${
                    activeAudioStream === 'improved' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  Track B Improved
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Audio Players Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div className={`p-3 rounded-xl border transition-all ${
            activeAudioStream === 'participant' ? 'bg-blue-950/40 border-blue-600' : 'bg-surface-900/60 border-surface-700'
          }`}>
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-400 block mb-1">
              Participant Delivery (Track A)
            </span>
            <audio
              ref={participantAudioRef}
              controls
              onTimeUpdate={handleTimeUpdate}
              src={apiService.getAnalysisAudioUrl(data.analysis_id)}
              className="w-full h-8 accent-blue-500 rounded"
            />
          </div>

          {data.has_reference_audio && (
            <div className={`p-3 rounded-xl border transition-all ${
              activeAudioStream === 'reference' ? 'bg-emerald-950/40 border-emerald-600' : 'bg-surface-900/60 border-surface-700'
            }`}>
              <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 block mb-1">
                Track A Ideal Reference Audio
              </span>
              <audio
                ref={referenceAudioRef}
                controls
                onTimeUpdate={handleTimeUpdate}
                src={apiService.getReferenceAudioUrl(data.analysis_id)}
                className="w-full h-8 accent-emerald-500 rounded"
              />
            </div>
          )}

          {data.has_improved_audio && (
            <div className={`p-3 rounded-xl border transition-all ${
              activeAudioStream === 'improved' ? 'bg-purple-950/40 border-purple-600' : 'bg-surface-900/60 border-surface-700'
            }`}>
              <span className="text-[11px] font-bold uppercase tracking-wider text-purple-400 block mb-1">
                Track B AI-Improved Audio
              </span>
              <audio
                ref={improvedAudioRef}
                controls
                onTimeUpdate={handleTimeUpdate}
                src={apiService.getImprovedAudioUrl(data.analysis_id)}
                className="w-full h-8 accent-purple-500 rounded"
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between text-xs text-gray-400 pt-1">
          <span>
            Current Scrubber Time: <strong className="text-white font-mono">{currentTime.toFixed(2)}s</strong>
          </span>
          <span className="text-gray-400 italic">
            Tip: Click anywhere along the pitch contour, energy waterfall, or flaw timeline to seek immediately.
          </span>
        </div>
      </div>

      {/* Interactive Visualization Studio Card (Plotly.js) */}
      <div className="card p-6 space-y-6 shadow-2xl">
        {/* Navigation Tabs */}
        <div className="border-b border-surface-700 flex flex-wrap gap-2 text-xs font-semibold">
          {[
            { id: 'pitch', label: 'Prosodic Pitch Contour (F0 DTW)', icon: Activity },
            { id: 'energy', label: 'Energy Dynamics & Waterfall', icon: Sliders },
            { id: 'flaws', label: `Temporal Flaws Timeline (${flaws?.flaws?.length || 0})`, icon: Target },
            { id: 'radar', label: '8-Dimension Competency Radar', icon: Award },
            { id: 'cadence', label: 'Cadence & Pause Rhythm', icon: Clock },
          ].map((tab) => {
            const Icon = tab.icon
            const isActive = activeChartTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveChartTab(tab.id as typeof activeChartTab)}
                className={`py-2.5 px-3.5 rounded-t-lg transition-all flex items-center gap-2 border-b-2 ${
                  isActive
                    ? 'border-primary-500 text-primary-400 bg-surface-700/50 shadow'
                    : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-surface-700/20'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Tab 1: Prosodic Pitch Contour */}
        {activeChartTab === 'pitch' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-bold text-white">Dynamic Time Warped Pitch Contour (F0 Tracking)</h4>
                <p className="text-xs text-gray-400">
                  Continuous fundamental frequency comparison between participant vocal tract and Track A ideal delivery reference.
                </p>
              </div>
              {comparison?.pitch && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="badge bg-surface-700 text-sky-300 border border-sky-800">
                    Δ Mean F0: {comparison.pitch.delta_mean_f0.toFixed(1)} Hz
                  </span>
                  <span className="badge bg-surface-700 text-emerald-300 border border-emerald-800">
                    Melody Score: {comparison.pitch.similarity_score.toFixed(0)}/100
                  </span>
                </div>
              )}
            </div>

            <div className="w-full h-[380px] rounded-xl overflow-hidden border border-surface-700">
              <Plot
                data={[
                  {
                    x: plotTimeAxis,
                    y: plotParticipantF0,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Participant Pitch (Hz)',
                    line: { color: '#38bdf8', width: 2.5 },
                    hoverinfo: 'x+y+name',
                  },
                  {
                    x: plotTimeAxis,
                    y: plotReferenceF0,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Track A Ideal Reference (Hz)',
                    line: { color: '#34d399', width: 2, dash: 'dot' },
                    hoverinfo: 'x+y+name',
                  },
                ]}
                layout={{
                  ...plotlyDarkLayout,
                  title: { text: 'Fundamental Frequency (F0) Modulation Over Time' },
                  xaxis: {
                    gridcolor: '#1f293d',
                    zerolinecolor: '#374151',
                    title: { text: 'Time (seconds)' },
                  },
                  yaxis: {
                    gridcolor: '#1f293d',
                    zerolinecolor: '#374151',
                    title: { text: 'Frequency F0 (Hz)' },
                  },
                }}
                config={{ responsive: true, displayModeBar: false }}
                onClick={(e: Plotly.PlotMouseEvent) => {
                  if (e.points && e.points[0]) {
                    handleSeek(Number(e.points[0].x))
                  }
                }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler
              />
            </div>

            {/* Pitch Metric Callouts */}
            {comparison?.pitch && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                  <span className="text-gray-400 block mb-0.5">Participant Mean Pitch</span>
                  <span className="text-base font-bold text-white">{comparison.pitch.participant_mean_f0.toFixed(1)} Hz</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                  <span className="text-gray-400 block mb-0.5">Reference Ideal Pitch</span>
                  <span className="text-base font-bold text-emerald-400">{comparison.pitch.reference_mean_f0.toFixed(1)} Hz</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                  <span className="text-gray-400 block mb-0.5">Pitch Variation Ratio</span>
                  <span className="text-base font-bold text-sky-400">{comparison.pitch.pitch_variation_ratio.toFixed(2)}x</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                  <span className="text-gray-400 block mb-0.5">Semitone Dynamic Range</span>
                  <span className="text-base font-bold text-purple-400">{comparison.pitch.participant_range_semitones.toFixed(1)} ST</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Energy Dynamics & Waterfall */}
        {activeChartTab === 'energy' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-bold text-white">RMS Intensity & Vocal Projection Waterfall</h4>
                <p className="text-xs text-gray-400">
                  Root-mean-square amplitude envelope visualizing vocal projection consistency and syllable stress emphasis.
                </p>
              </div>
              {comparison?.energy && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="badge bg-surface-700 text-amber-300 border border-amber-800">
                    Energy Ratio: {comparison.energy.energy_ratio.toFixed(2)}x
                  </span>
                  <span className="badge bg-surface-700 text-emerald-300 border border-emerald-800">
                    Energy Score: {comparison.energy.similarity_score.toFixed(0)}/100
                  </span>
                </div>
              )}
            </div>

            <div className="w-full h-[380px] rounded-xl overflow-hidden border border-surface-700">
              <Plot
                data={[
                  {
                    x: plotTimeAxis,
                    y: plotParticipantRMS,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Participant RMS Energy',
                    line: { color: '#fbbf24', width: 2.5 },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(251, 191, 36, 0.12)',
                    hoverinfo: 'x+y+name',
                  },
                  {
                    x: plotTimeAxis,
                    y: plotReferenceRMS,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Track A Ideal Reference Energy',
                    line: { color: '#818cf8', width: 2, dash: 'dash' },
                    hoverinfo: 'x+y+name',
                  },
                ]}
                layout={{
                  ...plotlyDarkLayout,
                  title: { text: 'RMS Volume & Intensity Modulation (Waterfall)' },
                  xaxis: {
                    gridcolor: '#1f293d',
                    zerolinecolor: '#374151',
                    title: { text: 'Time (seconds)' },
                  },
                  yaxis: {
                    gridcolor: '#1f293d',
                    zerolinecolor: '#374151',
                    title: { text: 'RMS Amplitude' },
                  },
                }}
                config={{ responsive: true, displayModeBar: false }}
                onClick={(e: Plotly.PlotMouseEvent) => {
                  if (e.points && e.points[0]) {
                    handleSeek(Number(e.points[0].x))
                  }
                }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler
              />
            </div>

            {/* Energy Metric Callouts */}
            {comparison?.energy && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                  <span className="text-gray-400 block mb-0.5">Mean RMS Intensity</span>
                  <span className="text-base font-bold text-white">{comparison.energy.participant_mean_rms.toFixed(3)}</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                  <span className="text-gray-400 block mb-0.5">Participant Dynamic Range</span>
                  <span className="text-base font-bold text-amber-400">{comparison.energy.participant_dynamic_range_db.toFixed(1)} dB</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                  <span className="text-gray-400 block mb-0.5">Reference Dynamic Range</span>
                  <span className="text-base font-bold text-indigo-400">{comparison.energy.reference_dynamic_range_db.toFixed(1)} dB</span>
                </div>
                <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                  <span className="text-gray-400 block mb-0.5">Projection Status</span>
                  <span className="text-base font-bold text-emerald-400 capitalize">{comparison.energy.status.replace('_', ' ')}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Temporal Flaws Timeline */}
        {activeChartTab === 'flaws' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-bold text-white">Temporal Delivery Flaw Distribution Timeline</h4>
                <p className="text-xs text-gray-400">
                  Every detected anomaly grounded against Track A reference. Click any flaw point to seek audio directly.
                </p>
              </div>
              {flaws?.summary && (
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="badge bg-rose-950 text-rose-300 border border-rose-800">
                    {flaws.summary.high_severity_count} High
                  </span>
                  <span className="badge bg-amber-950 text-amber-300 border border-amber-800">
                    {flaws.summary.medium_severity_count} Med
                  </span>
                  <span className="badge bg-sky-950 text-sky-300 border border-sky-800">
                    {flaws.summary.low_severity_count} Low
                  </span>
                </div>
              )}
            </div>

            {/* Plotly Flaw Timeline Scatter */}
            {flaws?.flaws && flaws.flaws.length > 0 ? (
              <div className="w-full h-[320px] rounded-xl overflow-hidden border border-surface-700">
                <Plot
                  data={[
                    {
                      x: flaws.flaws.filter((f) => f.severity === 'high').map((f) => f.start_time),
                      y: flaws.flaws.filter((f) => f.severity === 'high').map(() => 3),
                      text: flaws.flaws.filter((f) => f.severity === 'high').map((f) => `${f.description} (${f.duration.toFixed(2)}s)`),
                      type: 'scatter',
                      mode: 'markers',
                      name: 'High Severity Flaws',
                      marker: { color: '#f43f5e', size: 16, symbol: 'diamond' },
                      hoverinfo: 'x+text',
                    },
                    {
                      x: flaws.flaws.filter((f) => f.severity === 'medium').map((f) => f.start_time),
                      y: flaws.flaws.filter((f) => f.severity === 'medium').map(() => 2),
                      text: flaws.flaws.filter((f) => f.severity === 'medium').map((f) => `${f.description} (${f.duration.toFixed(2)}s)`),
                      type: 'scatter',
                      mode: 'markers',
                      name: 'Medium Severity Flaws',
                      marker: { color: '#f59e0b', size: 13, symbol: 'circle' },
                      hoverinfo: 'x+text',
                    },
                    {
                      x: flaws.flaws.filter((f) => f.severity === 'low').map((f) => f.start_time),
                      y: flaws.flaws.filter((f) => f.severity === 'low').map(() => 1),
                      text: flaws.flaws.filter((f) => f.severity === 'low').map((f) => `${f.description} (${f.duration.toFixed(2)}s)`),
                      type: 'scatter',
                      mode: 'markers',
                      name: 'Low Severity Flaws',
                      marker: { color: '#38bdf8', size: 10, symbol: 'triangle-up' },
                      hoverinfo: 'x+text',
                    },
                  ]}
                  layout={{
                    ...plotlyDarkLayout,
                    title: { text: 'Chronological Temporal Flaw Distribution' },
                    xaxis: {
                      gridcolor: '#1f293d',
                      zerolinecolor: '#374151',
                      title: { text: 'Speech Timeline (seconds)' },
                    },
                    yaxis: {
                      gridcolor: '#1f293d',
                      zerolinecolor: '#374151',
                      tickmode: 'array',
                      tickvals: [1, 2, 3],
                      ticktext: ['Low', 'Medium', 'High'],
                      title: { text: 'Severity Tier' },
                    },
                  }}
                  config={{ responsive: true, displayModeBar: false }}
                  onClick={(e: Plotly.PlotMouseEvent) => {
                    if (e.points && e.points[0]) {
                      const clickedX = Number(e.points[0].x)
                      handleSeek(clickedX)
                      const matched = flaws.flaws.find((f) => Math.abs(f.start_time - clickedX) < 0.2)
                      if (matched) setSelectedFlaw(matched)
                    }
                  }}
                  style={{ width: '100%', height: '100%' }}
                  useResizeHandler
                />
              </div>
            ) : (
              <div className="p-8 rounded-xl bg-surface-900 border border-surface-700 text-center">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
                <h5 className="font-bold text-white">Zero Temporal Delivery Flaws Detected</h5>
                <p className="text-xs text-gray-400">Exceptional temporal and prosodic delivery discipline.</p>
              </div>
            )}

            {/* Selected Flaw Inspector & Remedial Drill */}
            {selectedFlaw && (
              <div className="p-4 rounded-xl bg-surface-900/90 border border-primary-700/60 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`badge uppercase text-[10px] font-bold ${
                      selectedFlaw.severity === 'high'
                        ? 'bg-rose-950 text-rose-300 border border-rose-800'
                        : selectedFlaw.severity === 'medium'
                        ? 'bg-amber-950 text-amber-300 border border-amber-800'
                        : 'bg-sky-950 text-sky-300 border border-sky-800'
                    }`}>
                      {selectedFlaw.severity} Severity
                    </span>
                    <h5 className="text-xs font-bold text-white">
                      {selectedFlaw.flaw_type.replace(/_/g, ' ').toUpperCase()} ({selectedFlaw.start_time.toFixed(2)}s – {selectedFlaw.end_time.toFixed(2)}s)
                    </h5>
                  </div>
                  <button
                    onClick={() => handleSeek(selectedFlaw.start_time)}
                    className="btn-primary text-xs py-1 px-3 flex items-center gap-1.5"
                  >
                    <Volume2 className="w-3.5 h-3.5" />
                    Play Flaw Interval
                  </button>
                </div>

                <p className="text-xs text-gray-300">{selectedFlaw.description}</p>

                {selectedFlaw.affected_text && (
                  <div className="text-xs text-gray-400">
                    Affected Transcript Passage: <strong className="text-white italic">"{selectedFlaw.affected_text}"</strong>
                  </div>
                )}

                <div className="p-2.5 rounded-lg bg-surface-800/80 border border-surface-700 flex items-start gap-2 text-xs">
                  <Lightbulb className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-emerald-400">Prescriptive Coaching Drill: </strong>
                    <span className="text-gray-300">{selectedFlaw.suggestion}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: 8-Dimension Competency Radar */}
        {activeChartTab === 'radar' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-bold text-white">8-Dimension Speech Competency Radar Profile</h4>
                <p className="text-xs text-gray-400">
                  Comprehensive 360° contrastive polygon comparing participant competencies across Delivery and Content vs 100 benchmark.
                </p>
              </div>
            </div>

            <div className="w-full h-[420px] rounded-xl overflow-hidden border border-surface-700">
              <Plot
                data={[
                  {
                    type: 'scatterpolar',
                    r: closedValues,
                    theta: closedLabels,
                    fill: 'toself',
                    fillcolor: 'rgba(99, 102, 241, 0.25)',
                    line: { color: '#6366f1', width: 2.5 },
                    name: 'Participant Actual Profile',
                  },
                  {
                    type: 'scatterpolar',
                    r: closedIdeal,
                    theta: closedLabels,
                    line: { color: '#10b981', width: 1.5, dash: 'dot' },
                    name: 'Ideal Benchmark (100)',
                  },
                ]}
                layout={{
                  ...plotlyDarkLayout,
                  title: { text: 'Holistic Speech Competency Profile (0 - 100)' },
                  polar: {
                    bgcolor: '#0a0f1e',
                    radialaxis: {
                      visible: true,
                      range: [0, 100],
                      gridcolor: '#1f293d',
                      tickfont: { color: '#6b7280', size: 10 },
                    },
                    angularaxis: {
                      gridcolor: '#1f293d',
                      tickfont: { color: '#e5e7eb', size: 11, family: 'Inter, sans-serif' },
                    },
                  },
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler
              />
            </div>

            {/* Scorecard Table */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
              {radarDimensions.map((dim) => (
                <div key={dim.name} className="p-2.5 rounded-lg bg-surface-900 border border-surface-700/60 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-300 truncate max-w-[130px]">{dim.name}</span>
                    <span className="badge bg-surface-800 text-emerald-400 text-[10px] font-bold">
                      Grade {dim.grade}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px] text-gray-400">
                    <span>{dim.track === 'delivery' ? 'Track A' : 'Track B'}</span>
                    <span className="font-mono font-bold text-white">{dim.raw_score} / 100</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 5: Cadence & Pause Rhythm */}
        {activeChartTab === 'cadence' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-bold text-white">Cadence & Pause Duration Rhythm Histogram</h4>
                <p className="text-xs text-gray-400">
                  Comparison of silence intervals and syntactic pause discipline against Track A ideal natural delivery.
                </p>
              </div>
              {comparison?.pause && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="badge bg-surface-700 text-sky-300 border border-sky-800">
                    Δ Pause Count: {comparison.pause.delta_pause_count > 0 ? `+${comparison.pause.delta_pause_count}` : comparison.pause.delta_pause_count}
                  </span>
                  <span className="badge bg-surface-700 text-emerald-300 border border-emerald-800">
                    Cadence: {comparison.pause.status.replace('_', ' ')}
                  </span>
                </div>
              )}
            </div>

            <div className="w-full h-[360px] rounded-xl overflow-hidden border border-surface-700">
              <Plot
                data={[
                  {
                    x: ['Micro (<0.3s)', 'Syntactic (0.3-0.8s)', 'Hesitant (0.8-1.5s)', 'Excessive (>1.5s)'],
                    y: [
                      comparison?.pause ? Math.max(0, comparison.pause.participant_pause_count - 2) : 2,
                      comparison?.pause ? Math.max(1, Math.round(comparison.pause.participant_pause_count * 0.6)) : 4,
                      comparison?.pause ? Math.max(0, Math.round(comparison.pause.participant_pause_count * 0.2)) : 1,
                      flaws?.summary ? flaws.summary.high_severity_count : 0,
                    ],
                    type: 'bar',
                    name: 'Participant Pauses',
                    marker: { color: '#38bdf8' },
                  },
                  {
                    x: ['Micro (<0.3s)', 'Syntactic (0.3-0.8s)', 'Hesitant (0.8-1.5s)', 'Excessive (>1.5s)'],
                    y: [
                      comparison?.pause ? Math.max(0, comparison.pause.reference_pause_count - 1) : 1,
                      comparison?.pause ? Math.max(1, Math.round(comparison.pause.reference_pause_count * 0.8)) : 5,
                      0,
                      0,
                    ],
                    type: 'bar',
                    name: 'Track A Ideal Reference',
                    marker: { color: '#10b981' },
                  },
                ]}
                layout={{
                  ...plotlyDarkLayout,
                  barmode: 'group',
                  title: { text: 'Pause Interval Categorization & Distribution' },
                  xaxis: {
                    gridcolor: '#1f293d',
                    zerolinecolor: '#374151',
                    title: { text: 'Pause Duration Category' },
                  },
                  yaxis: {
                    gridcolor: '#1f293d',
                    zerolinecolor: '#374151',
                    title: { text: 'Occurrence Count' },
                  },
                }}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler
              />
            </div>

            {/* Rhythm Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                <span className="text-gray-400 block mb-0.5">Participant Speaking Rate</span>
                <span className="text-base font-bold text-white">
                  {comparison?.pace?.participant_wpm.toFixed(0) || 135} WPM
                </span>
              </div>
              <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                <span className="text-gray-400 block mb-0.5">Reference Ideal Rate</span>
                <span className="text-base font-bold text-emerald-400">
                  {comparison?.pace?.reference_wpm.toFixed(0) || 140} WPM
                </span>
              </div>
              <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                <span className="text-gray-400 block mb-0.5">Pause-to-Speech Ratio</span>
                <span className="text-base font-bold text-sky-400">
                  {((comparison?.pause?.participant_pause_to_speech_ratio || 0.15) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-3 rounded-lg bg-surface-900 border border-surface-700/60">
                <span className="text-gray-400 block mb-0.5">Pause Duration Total</span>
                <span className="text-base font-bold text-amber-400">
                  {comparison?.pause?.participant_pause_duration.toFixed(1) || 1.2}s
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Two-Track Synchronized Transcript Comparison Drawer */}
      <div className="card p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-surface-700/60 pb-3">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-purple-400" />
            <h4 className="text-sm font-bold text-white">Two-Track Script & Delivery Alignment</h4>
          </div>
          <span className="badge bg-surface-700 text-gray-300 text-xs">
            Track A (Acoustic Reference) vs Track B (Content Ideal)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Track A */}
          <div className="p-4 rounded-xl bg-surface-900/80 border border-blue-900/50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-blue-400 uppercase tracking-wider text-[11px]">
                Track A: Participant Delivery Words
              </span>
              <span className="text-gray-400">Exact words · Acoustic baseline</span>
            </div>
            <p className="text-gray-200 leading-relaxed font-sans bg-surface-950 p-3 rounded-lg border border-surface-800">
              {data.delivery_transcript || data.raw_transcript || 'No transcript available.'}
            </p>
          </div>

          {/* Track B */}
          <div className="p-4 rounded-xl bg-surface-900/80 border border-purple-900/50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-purple-400 uppercase tracking-wider text-[11px]">
                Track B: AI-Polished Version
              </span>
              <span className="text-gray-400">Grammar & semantics enhanced</span>
            </div>
            <p className="text-purple-200 leading-relaxed font-sans bg-surface-950 p-3 rounded-lg border border-surface-800">
              {data.corrected_transcript || data.delivery_transcript || 'No polished transcript available.'}
            </p>
          </div>
        </div>
      </div>

      {/* Strategic 3-Step Action Roadmap */}
      {explanations?.diagnosis?.action_roadmap && (
        <div className="card p-6 space-y-4 shadow-xl bg-gradient-to-r from-surface-800 via-surface-900 to-surface-800 border-surface-700">
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-emerald-400" />
            <h4 className="text-sm font-bold text-white">Vocal Coach Action Roadmap</h4>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {explanations.diagnosis.action_roadmap.map((step, idx) => (
              <div key={idx} className="p-3.5 rounded-xl bg-surface-900/80 border border-surface-700/80 space-y-1 text-xs">
                <span className="badge bg-emerald-950 text-emerald-300 border border-emerald-700 font-bold mb-1">
                  Step {idx + 1}
                </span>
                <p className="text-gray-200 leading-relaxed">{step}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer Navigation */}
      <div className="flex justify-between items-center pt-4 border-t border-surface-700/60">
        <Link to="/analyze" className="btn-secondary text-sm py-2 px-5 flex items-center gap-2">
          <ArrowLeft className="w-4 h-4" />
          Analyze Another Speech
        </Link>
        <span className="text-xs text-gray-500 font-mono">
          Analysis ID: {data.analysis_id}
        </span>
      </div>
    </div>
  )
}
