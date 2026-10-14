import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2,
  Loader2,
  AlertCircle,
  ArrowRight,
  Sparkles,
  Volume2,
  FileText,
  Brain,
  Music,
  GitCompare,
  Activity,
  Layers,
  ShieldAlert,
  Award,
} from 'lucide-react'
import { apiService } from '../services/api'
import { PipelineProgressResponse, PipelineStageInfo } from '../types'

interface PipelineProgressTrackerProps {
  analysisId: string
  onComplete?: (resultsUrl: string) => void
  onCancel?: () => void
}

const STAGE_ICONS: Record<string, React.ElementType> = {
  ingestion: Volume2,
  transcription: FileText,
  content_evaluation: Brain,
  reference_generation: Music,
  alignment: Layers,
  feature_extraction: Activity,
  comparison: GitCompare,
  flaw_detection: ShieldAlert,
  explanations: Sparkles,
  scoring: Award,
}

export default function PipelineProgressTracker({
  analysisId,
  onComplete,
  onCancel,
}: PipelineProgressTrackerProps) {
  const [progress, setProgress] = useState<PipelineProgressResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    let intervalId: any = null
    let isCancelled = false

    const poll = async () => {
      try {
        const data = await apiService.getPipelineProgress(analysisId)
        if (isCancelled) return
        setProgress(data)

        if (data.status === 'completed') {
          clearInterval(intervalId)
          if (onComplete) {
            onComplete(`/results/${analysisId}`)
          }
        } else if (data.status === 'failed') {
          clearInterval(intervalId)
          setError(data.error_message || 'Pipeline execution encountered a failure.')
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          const msg = err instanceof Error ? err.message : 'Failed to query progress'
          console.warn('Progress polling error:', msg)
        }
      }
    }

    // Immediate first poll
    poll()
    // Poll every 1200ms
    intervalId = setInterval(poll, 1200)

    return () => {
      isCancelled = true
      clearInterval(intervalId)
    }
  }, [analysisId, onComplete])

  const percent = progress?.progress_percent || 10
  const isCompleted = progress?.status === 'completed'
  const isFailed = progress?.status === 'failed'

  return (
    <div className="card bg-surface-800/95 border border-primary-500/40 shadow-2xl p-6 sm:p-8 space-y-6 animate-fade-in relative overflow-hidden">
      {/* Background glow effect */}
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-primary-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-surface-700 pb-5">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-primary-950 border border-primary-700/60 text-primary-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-primary-400 animate-pulse" />
            Autonomous 10-Stage Speech Pipeline
          </div>
          <h3 className="text-xl font-black text-white flex items-center gap-2">
            {isCompleted ? 'Analysis Complete!' : isFailed ? 'Pipeline Interrupted' : 'Analyzing Speech Recording...'}
          </h3>
          <p className="text-xs text-gray-400">
            {isCompleted
              ? 'All 10 stages synthesized. Your multidimensional delivery & content report is ready.'
              : isFailed
              ? 'An error occurred during stage processing. See diagnostic details below.'
              : 'Executing autonomous pipeline: Faster-Whisper ASR, Gemini Content AI, Librosa DTW & Rubric Scoring.'}
          </p>
        </div>

        {isCompleted && (
          <button
            onClick={() => navigate(`/results/${analysisId}`)}
            className="btn-primary flex items-center gap-2 text-sm py-2.5 px-6 shadow-lg shadow-primary-600/30"
          >
            <span>View Full Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Progress Bar & Percentage */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold">
          <span className="text-gray-300">
            Stage {progress?.current_step || 1} of 10:{' '}
            <span className="text-primary-300 font-bold uppercase tracking-wider">
              {progress?.current_stage.replace(/_/g, ' ') || 'Ingestion'}
            </span>
          </span>
          <span className="text-primary-400 font-mono text-sm">{percent}%</span>
        </div>
        <div className="w-full bg-surface-900 rounded-full h-3 p-0.5 border border-surface-700 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${
              isFailed
                ? 'bg-rose-500'
                : isCompleted
                ? 'bg-gradient-to-r from-primary-500 to-emerald-400'
                : 'bg-gradient-to-r from-primary-600 to-accent-500'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      {/* Error Message if Failed */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-700 text-rose-200 text-xs flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold">Pipeline Error</p>
            <p className="opacity-90">{error}</p>
          </div>
        </div>
      )}

      {/* 10 Stages Sequential Checklist */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-2">
        {progress?.stages.map((stage: PipelineStageInfo, idx: number) => {
          const Icon = STAGE_ICONS[stage.stage_id] || Activity
          const isDone = stage.status === 'completed'
          const isRunning = stage.status === 'running'
          const isFail = stage.status === 'failed'

          return (
            <div
              key={stage.stage_id}
              className={`p-3 rounded-xl border transition-all flex items-start gap-3 ${
                isDone
                  ? 'bg-surface-700/40 border-emerald-900/60 text-gray-200'
                  : isRunning
                  ? 'bg-primary-950/40 border-primary-500/80 shadow-md shadow-primary-950/50'
                  : isFail
                  ? 'bg-rose-950/40 border-rose-800 text-rose-300'
                  : 'bg-surface-900/40 border-surface-700/60 text-gray-500 opacity-60'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                  isDone
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-700'
                    : isRunning
                    ? 'bg-primary-600 text-white animate-pulse'
                    : isFail
                    ? 'bg-rose-900 text-rose-300 border border-rose-700'
                    : 'bg-surface-800 text-gray-500 border border-surface-700'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isRunning ? (
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                ) : (
                  <span>{idx + 1}</span>
                )}
              </div>

              <div className="space-y-0.5 min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1">
                  <h4
                    className={`text-xs font-bold truncate ${
                      isDone ? 'text-gray-200' : isRunning ? 'text-primary-300 font-black' : isFail ? 'text-rose-300' : 'text-gray-400'
                    }`}
                  >
                    {stage.name}
                  </h4>
                  {isDone && (
                    <span className="text-[10px] text-emerald-400 font-semibold flex-shrink-0">Ready</span>
                  )}
                  {isRunning && (
                    <span className="text-[10px] text-primary-400 font-semibold animate-pulse flex-shrink-0">
                      Processing...
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-gray-400 line-clamp-1">{stage.description}</p>
              </div>
            </div>
          )
        })}
      </div>

      {/* Footer Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-surface-700/80 text-xs text-gray-400">
        <span className="font-mono text-[11px]">Analysis ID: {analysisId}</span>
        {isCompleted ? (
          <button
            onClick={() => navigate(`/results/${analysisId}`)}
            className="btn-primary text-xs py-2 px-5 flex items-center gap-1.5"
          >
            <span>Proceed to Dashboard</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        ) : onCancel && !isCompleted ? (
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-white transition-colors text-xs underline underline-offset-2"
          >
            Back to Upload
          </button>
        ) : null}
      </div>
    </div>
  )
}
