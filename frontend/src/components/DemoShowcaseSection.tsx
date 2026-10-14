import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  ArrowRight,
  Clock,
  Award,
  Zap,
  Activity,
  AlertTriangle,
  Play,
  Loader2,
  CheckCircle2,
} from 'lucide-react'
import { apiService } from '../services/api'
import { DemoSampleSummary } from '../types'

export default function DemoShowcaseSection() {
  const [samples, setSamples] = useState<DemoSampleSummary[]>([])
  const [loadingSampleId, setLoadingSampleId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const fetchSamples = async () => {
      try {
        const resp = await apiService.getDemoSamples()
        setSamples(resp.samples)
      } catch (err: unknown) {
        console.error('Failed to load demo samples:', err)
      }
    }
    fetchSamples()
  }, [])

  const handleLoadDemo = async (sampleId: string) => {
    try {
      setError(null)
      setLoadingSampleId(sampleId)
      const res = await apiService.loadDemoSample(sampleId)
      navigate(`/results/${res.analysis_id}`)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load demo speech'
      setError(msg)
      setLoadingSampleId(null)
    }
  }

  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'master':
        return 'text-emerald-400 bg-emerald-950/80 border-emerald-700'
      case 'proficient':
        return 'text-blue-400 bg-blue-950/80 border-blue-700'
      case 'competent':
        return 'text-amber-400 bg-amber-950/80 border-amber-700'
      default:
        return 'text-rose-400 bg-rose-950/80 border-rose-700'
    }
  }

  if (samples.length === 0) return null

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-950/80 border border-primary-700 text-primary-300 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-primary-400 animate-pulse" />
          Zero-Upload One-Click Showcase
        </div>
        <h3 className="text-2xl font-black text-white">Contrastive Demo Dataset</h3>
        <p className="text-xs text-gray-400 max-w-xl mx-auto">
          Explore instant precomputed analyses demonstrating distinct public speaking delivery archetypes, DTW pitch warping, and temporal flaw attributions.
        </p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/80 border border-rose-700 text-rose-300 text-xs text-center">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {samples.map((sample) => {
          const isLoading = loadingSampleId === sample.sample_id
          return (
            <div
              key={sample.sample_id}
              className="card bg-surface-800/90 border border-surface-700 hover:border-primary-500/60 transition-all flex flex-col justify-between p-5 space-y-4 hover:shadow-xl hover:shadow-primary-950/30 group"
            >
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-primary-400">
                      {sample.archetype}
                    </span>
                    <h4 className="font-bold text-white text-sm group-hover:text-primary-300 transition-colors">
                      {sample.title}
                    </h4>
                  </div>
                  <div className={`badge border text-[10px] font-bold ${getTierColor(sample.tier)}`}>
                    Grade {sample.grade}
                  </div>
                </div>

                {/* Score & Duration */}
                <div className="flex items-center justify-between text-xs p-2 rounded-lg bg-surface-900 border border-surface-700/60">
                  <div className="flex items-center gap-1.5">
                    <Award className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-gray-300 font-mono font-bold">{sample.overall_score}</span>
                    <span className="text-[10px] text-gray-500">/ 100</span>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-gray-400">
                    <Clock className="w-3 h-3 text-gray-500" />
                    <span>{sample.duration}s</span>
                  </div>
                </div>

                {/* Transcript Excerpt */}
                <p className="text-[11px] text-gray-300 italic bg-surface-950/60 p-2.5 rounded-lg border border-surface-800 line-clamp-3">
                  "{sample.transcript_preview}"
                </p>

                {/* Key Flaws Showcase */}
                <div className="space-y-1">
                  <span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider block">
                    Target Acoustic Dynamics:
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {sample.key_flaws.map((flaw, idx) => (
                      <span
                        key={idx}
                        className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${
                          flaw.startsWith('None')
                            ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                            : 'bg-rose-950/60 text-rose-300 border-rose-800'
                        }`}
                      >
                        {flaw}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={() => handleLoadDemo(sample.sample_id)}
                disabled={isLoading || loadingSampleId !== null}
                className="w-full btn-primary text-xs py-2 px-3 flex items-center justify-center gap-1.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Opening Dashboard...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 fill-white" />
                    <span>Load Demo Analysis</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                  </>
                )}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
