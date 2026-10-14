import React, { useState, useRef, DragEvent, ChangeEvent } from 'react'
import {
  UploadCloud,
  FileAudio,
  FileVideo,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Music,
  Clock,
  Layers,
  Volume2,
  FileText,
  AlignLeft,
  Activity,
  ListOrdered,
  Brain,
  Check,
  X,
  HelpCircle,
  Lightbulb,
  ThumbsUp,
  AlertTriangle,
  Radio,
  Sliders,
  Share2,
  GitCompare,
  TrendingUp,
  Cpu,
  Gauge,
  Scale,
  Timer,
  FastForward,
  Target,
  ShieldAlert,
  Compass,
  BookOpen,
  Award,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { apiService } from '../services/api'
import DemoShowcaseSection from '../components/DemoShowcaseSection'
import PipelineProgressTracker from '../components/PipelineProgressTracker'
import {
  MediaUploadResponse,
  TranscriptionResponse,
  ContentEvaluationResponse,
  ReferenceGenerationResponse,
  AlignmentResponse,
  AlignedWordItem,
  AlignedPhraseItem,
  FeaturesResponse,
  ComparisonResponse,
  FlawsResponse,
  TemporalFlawItem,
  ExplanationsResponse,
  CausalFlawExplanation,
  ScoringResponse,
  ScoringDimensionItem,
  RubricTierLevel,
} from '../types'

const ACCEPTED_EXTENSIONS = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.mp4', '.mov', '.webm']
const MAX_FILE_SIZE_MB = 500

export default function AnalyzePage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [isProcessingMedia, setIsProcessingMedia] = useState(false)
  const [isOneClickRunning, setIsOneClickRunning] = useState(false)
  const [activeProcessingId, setActiveProcessingId] = useState<string | null>(null)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isEvaluatingContent, setIsEvaluatingContent] = useState(false)
  const [isGeneratingReference, setIsGeneratingReference] = useState(false)
  const [isAligning, setIsAligning] = useState(false)
  const [isExtractingFeatures, setIsExtractingFeatures] = useState(false)
  const [isComparing, setIsComparing] = useState(false)
  const [isDetectingFlaws, setIsDetectingFlaws] = useState(false)
  const [isExplaining, setIsExplaining] = useState(false)
  const [isScoring, setIsScoring] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [uploadResult, setUploadResult] = useState<MediaUploadResponse | null>(null)
  const [transcriptResult, setTranscriptResult] = useState<TranscriptionResponse | null>(null)
  const [contentResult, setContentResult] = useState<ContentEvaluationResponse | null>(null)
  const [referenceResult, setReferenceResult] = useState<ReferenceGenerationResponse | null>(null)
  const [alignmentResult, setAlignmentResult] = useState<AlignmentResponse | null>(null)
  const [alignmentViewMode, setAlignmentViewMode] = useState<'words' | 'phrases'>('words')
  const [highlightedWordIndex, setHighlightedWordIndex] = useState<number | null>(null)
  const [featuresResult, setFeaturesResult] = useState<FeaturesResponse | null>(null)
  const [featuresTab, setFeaturesTab] = useState<'pitch' | 'energy' | 'rhythm' | 'spectral' | 'words'>('pitch')
  const [comparisonResult, setComparisonResult] = useState<ComparisonResponse | null>(null)
  const [comparisonTab, setComparisonTab] = useState<'overview' | 'dtw' | 'words' | 'prosody'>('overview')
  const [flawsResult, setFlawsResult] = useState<FlawsResponse | null>(null)
  const [flawsCategoryFilter, setFlawsCategoryFilter] = useState<string>('all')
  const [selectedFlawId, setSelectedFlawId] = useState<string | null>(null)
  const [explanationsResult, setExplanationsResult] = useState<ExplanationsResponse | null>(null)
  const [activeExplanationsTab, setActiveExplanationsTab] = useState<'diagnosis' | 'causes' | 'flaws' | 'roadmap'>('diagnosis')
  const [scoringResult, setScoringResult] = useState<ScoringResponse | null>(null)
  const [scoringTab, setScoringTab] = useState<'composite' | 'dimensions' | 'matrix'>('composite')
  const [deliveryWeight, setDeliveryWeight] = useState<number>(0.50)
  const [contentWeight, setContentWeight] = useState<number>(0.50)

  const [showRawTranscript, setShowRawTranscript] = useState(false)
  const [activeTab, setActiveTab] = useState<'delivery' | 'improved' | 'grammar' | 'semantics' | 'content'>('delivery')

  const fileInputRef = useRef<HTMLInputElement>(null)
  const participantAudioRef = useRef<HTMLAudioElement>(null)
  const referenceAudioRef = useRef<HTMLAudioElement>(null)
  const improvedAudioRef = useRef<HTMLAudioElement>(null)

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400 bg-emerald-950/60 border-emerald-700'
    if (score >= 60) return 'text-amber-400 bg-amber-950/60 border-amber-700'
    return 'text-red-400 bg-red-950/60 border-red-700'
  }

  const validateAndSelectFile = (selectedFile: File) => {
    setError(null)
    const ext = '.' + selectedFile.name.split('.').pop()?.toLowerCase()

    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported file format "${ext}". Please upload an audio (${ACCEPTED_EXTENSIONS.slice(0, 6).join(', ')}) or video (${ACCEPTED_EXTENSIONS.slice(6).join(', ')}) file.`)
      return
    }

    if (selectedFile.size === 0) {
      setError('The selected file is empty (0 bytes).')
      return
    }

    if (selectedFile.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(`File size exceeds maximum allowed limit of ${MAX_FILE_SIZE_MB} MB.`)
      return
    }

    setFile(selectedFile)
    setUploadResult(null)
    setTranscriptResult(null)
    setContentResult(null)
    setReferenceResult(null)
    setAlignmentResult(null)
    setHighlightedWordIndex(null)
    setFeaturesResult(null)
    setUploadProgress(null)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelectFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelectFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return

    try {
      setError(null)
      setIsProcessingMedia(true)
      setUploadProgress(0)

      const result = await apiService.uploadMedia(file, (percent) => {
        setUploadProgress(percent)
      })

      setUploadResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setError(message)
    } finally {
      setIsProcessingMedia(false)
    }
  }

  const handleUploadAndProcessAll = async () => {
    if (!file) return

    try {
      setError(null)
      setIsProcessingMedia(true)
      setIsOneClickRunning(true)

      const response = await apiService.uploadAndProcess(
        file,
        deliveryWeight,
        contentWeight,
        (percent) => {
          setUploadProgress(percent)
        }
      )

      setActiveProcessingId(response.analysis_id)
      navigate(response.results_url || `/results/${response.analysis_id}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '1-Click analysis failed'
      setError(message)
      setActiveProcessingId(null)
    } finally {
      setIsProcessingMedia(false)
      setIsOneClickRunning(false)
    }
  }

  const handleProcessAll = async () => {
    if (!uploadResult) return

    try {
      setError(null)
      setIsOneClickRunning(true)
      setActiveProcessingId(uploadResult.analysis_id)

      const response = await apiService.processAll(uploadResult.analysis_id, {
        delivery_weight: deliveryWeight,
        content_weight: contentWeight,
      })

      navigate(response.results_url || `/results/${uploadResult.analysis_id}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Pipeline execution failed'
      setError(message)
    } finally {
      setIsOneClickRunning(false)
    }
  }

  const handleTranscribe = async () => {
    if (!uploadResult) return

    try {
      setError(null)
      setIsTranscribing(true)
      const result = await apiService.transcribe(uploadResult.analysis_id)
      setTranscriptResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Transcription failed'
      setError(message)
    } finally {
      setIsTranscribing(false)
    }
  }

  const handleEvaluateContent = async () => {
    if (!uploadResult) return

    try {
      setError(null)
      setIsEvaluatingContent(true)
      const result = await apiService.evaluateContent(uploadResult.analysis_id)
      setContentResult(result)
      setActiveTab('improved')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Content evaluation failed'
      setError(message)
    } finally {
      setIsEvaluatingContent(false)
    }
  }

  const handleGenerateReference = async () => {
    if (!uploadResult) return

    try {
      setError(null)
      setIsGeneratingReference(true)
      const result = await apiService.generateReference(uploadResult.analysis_id)
      setReferenceResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Reference generation failed'
      setError(message)
    } finally {
      setIsGeneratingReference(false)
    }
  }

  const handleAlign = async () => {
    if (!uploadResult) return

    try {
      setError(null)
      setIsAligning(true)
      const result = await apiService.align(uploadResult.analysis_id)
      setAlignmentResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Forced alignment failed'
      setError(message)
    } finally {
      setIsAligning(false)
    }
  }

  const handlePlayAlignedWord = (wordItem: AlignedWordItem, index?: number) => {
    if (index !== undefined) {
      setHighlightedWordIndex(index)
    }
    if (participantAudioRef.current) {
      participantAudioRef.current.currentTime = wordItem.participant_start
      participantAudioRef.current.play()
    }
  }

  const handlePlayReferenceWord = (wordItem: AlignedWordItem) => {
    if (referenceAudioRef.current) {
      referenceAudioRef.current.currentTime = wordItem.reference_start
      referenceAudioRef.current.play()
    }
  }

  const handlePlayAlignedPhrase = (phraseItem: AlignedPhraseItem) => {
    if (participantAudioRef.current) {
      participantAudioRef.current.currentTime = phraseItem.participant_start
      participantAudioRef.current.play()
    }
  }

  const handlePlaySegment = (start: number) => {
    if (participantAudioRef.current) {
      participantAudioRef.current.currentTime = start
      participantAudioRef.current.play()
    }
  }

  const handleExtractFeatures = async () => {
    if (!uploadResult) return
    try {
      setError(null)
      setIsExtractingFeatures(true)
      const result = await apiService.extractFeatures(uploadResult.analysis_id)
      setFeaturesResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Feature extraction failed'
      setError(message)
    } finally {
      setIsExtractingFeatures(false)
    }
  }

  const handleCompare = async () => {
    if (!uploadResult) return
    try {
      setError(null)
      setIsComparing(true)
      const result = await apiService.compare(uploadResult.analysis_id)
      setComparisonResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Comparison failed'
      setError(message)
    } finally {
      setIsComparing(false)
    }
  }

  const handleDetectFlaws = async () => {
    if (!uploadResult) return
    try {
      setError(null)
      setIsDetectingFlaws(true)
      const result = await apiService.detectFlaws(uploadResult.analysis_id)
      setFlawsResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Flaw detection failed'
      setError(message)
    } finally {
      setIsDetectingFlaws(false)
    }
  }

  const handleExplain = async () => {
    if (!uploadResult) return
    try {
      setError(null)
      setIsExplaining(true)
      const result = await apiService.explain(uploadResult.analysis_id)
      setExplanationsResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Causal explanation failed'
      setError(message)
    } finally {
      setIsExplaining(false)
    }
  }

  const handleScore = async (overrideDeliveryW?: number, overrideContentW?: number) => {
    if (!uploadResult) return
    try {
      setError(null)
      setIsScoring(true)
      const dw = overrideDeliveryW !== undefined ? overrideDeliveryW : deliveryWeight
      const cw = overrideContentW !== undefined ? overrideContentW : contentWeight
      const result = await apiService.score(uploadResult.analysis_id, dw, cw)
      setScoringResult(result)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Rubric evaluation failed'
      setError(message)
    } finally {
      setIsScoring(false)
    }
  }

  const handlePlayFlaw = (flaw: TemporalFlawItem) => {
    setSelectedFlawId(flaw.id)
    if (participantAudioRef.current) {
      participantAudioRef.current.currentTime = Math.max(0, flaw.start_time - 0.15)
      participantAudioRef.current.play()
    }
  }

  const handleReset = () => {
    setFile(null)
    setUploadResult(null)
    setTranscriptResult(null)
    setContentResult(null)
    setReferenceResult(null)
    setAlignmentResult(null)
    setHighlightedWordIndex(null)
    setIsAligning(false)
    setFeaturesResult(null)
    setIsExtractingFeatures(false)
    setComparisonResult(null)
    setIsComparing(false)
    setFlawsResult(null)
    setIsDetectingFlaws(false)
    setSelectedFlawId(null)
    setFlawsCategoryFilter('all')
    setExplanationsResult(null)
    setIsExplaining(false)
    setActiveExplanationsTab('diagnosis')
    setScoringResult(null)
    setIsScoring(false)
    setScoringTab('composite')
    setUploadProgress(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const isVideo = file?.name.match(/\.(mp4|mov|webm)$/i) || uploadResult?.input_type === 'video'

  const wpm = transcriptResult && transcriptResult.duration > 0
    ? Math.round((transcriptResult.words.length / transcriptResult.duration) * 60)
    : 0

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-950/80 border border-primary-700/50 text-primary-400 text-xs font-semibold mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          Autonomous Contrastive Speech Pipeline
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-3">
          Speech Analytics Studio
        </h1>
        <p className="text-gray-400 max-w-2xl mx-auto text-sm sm:text-base">
          Autonomous evaluation without requiring manual reference speech:
          standardization, Faster-Whisper ASR, Gemini linguistic evaluation, and automatic ideal TTS baseline.
        </p>
      </div>

      {/* 5-Stage Pipeline Progress Tracker */}
      <div className="mb-8 grid grid-cols-2 sm:grid-cols-5 gap-2 sm:gap-3">
        <div className={`p-3 rounded-xl border flex items-center gap-2 transition-all ${
          uploadResult
            ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-300'
            : isProcessingMedia
            ? 'bg-primary-950/40 border-primary-500 text-primary-300 animate-pulse'
            : 'bg-surface-800 border-surface-600 text-gray-400'
        }`}>
          <div className="w-5 h-5 rounded-full flex items-center justify-center font-bold text-xs bg-surface-700 flex-shrink-0">
            {uploadResult ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : '1'}
          </div>
          <div className="text-xs truncate">
            <p className="font-semibold truncate">1. Ingestion</p>
            <p className="text-[10px] opacity-75">{uploadResult ? '16 kHz WAV' : 'Pending'}</p>
          </div>
        </div>

        <div className={`p-3 rounded-xl border flex items-center gap-2 transition-all ${
          transcriptResult
            ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-300'
            : isTranscribing
            ? 'bg-primary-950/40 border-primary-500 text-primary-300 animate-pulse'
            : 'bg-surface-800 border-surface-600 text-gray-400'
        }`}>
          <div className="w-5 h-5 rounded-full flex items-center justify-center font-bold text-xs bg-surface-700 flex-shrink-0">
            {transcriptResult ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : '2'}
          </div>
          <div className="text-xs truncate">
            <p className="font-semibold truncate">2. ASR Track A</p>
            <p className="text-[10px] opacity-75">{transcriptResult ? 'Timestamps' : 'Whisper'}</p>
          </div>
        </div>

        <div className={`p-3 rounded-xl border flex items-center gap-2 transition-all ${
          contentResult
            ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-300'
            : isEvaluatingContent
            ? 'bg-primary-950/40 border-primary-500 text-primary-300 animate-pulse'
            : 'bg-surface-800 border-surface-600 text-gray-400'
        }`}>
          <div className="w-5 h-5 rounded-full flex items-center justify-center font-bold text-xs bg-surface-700 flex-shrink-0">
            {contentResult ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : '3'}
          </div>
          <div className="text-xs truncate">
            <p className="font-semibold truncate">3. Content Track B</p>
            <p className="text-[10px] opacity-75">{contentResult ? 'Evaluated' : 'Gemini AI'}</p>
          </div>
        </div>

        <div className={`p-3 rounded-xl border flex items-center gap-2 transition-all ${
          referenceResult
            ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-300'
            : isGeneratingReference
            ? 'bg-primary-950/40 border-primary-500 text-primary-300 animate-pulse'
            : 'bg-surface-800 border-surface-600 text-gray-400'
        }`}>
          <div className="w-5 h-5 rounded-full flex items-center justify-center font-bold text-xs bg-surface-700 flex-shrink-0">
            {referenceResult ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : '4'}
          </div>
          <div className="text-xs truncate">
            <p className="font-semibold truncate">4. Ideal Reference</p>
            <p className="text-[10px] opacity-75">{referenceResult ? 'Generated' : 'Gemini TTS'}</p>
          </div>
        </div>

        <div className={`p-3 rounded-xl border flex items-center gap-2 transition-all col-span-2 sm:col-span-1 ${
          alignmentResult
            ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-300'
            : isAligning
            ? 'bg-primary-950/40 border-primary-500 text-primary-300 animate-pulse'
            : referenceResult
            ? 'bg-primary-950/20 border-primary-800/60 text-primary-300'
            : 'bg-surface-800 border-surface-600 text-gray-500'
        }`}>
          <div className="w-5 h-5 rounded-full flex items-center justify-center font-bold text-xs bg-surface-700 flex-shrink-0">
            {alignmentResult ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : '5'}
          </div>
          <div className="text-xs truncate">
            <p className="font-semibold truncate">5. Forced Alignment</p>
            <p className="text-[10px] opacity-75">
              {alignmentResult ? `${alignmentResult.alignment_coverage.toFixed(0)}% Coverage` : isAligning ? 'Aligning...' : 'Track A Mapping'}
            </p>
          </div>
        </div>
      </div>

      {/* Real-time Pipeline Progress Tracker (Phase 14) */}
      {activeProcessingId && (
        <div className="mb-8">
          <PipelineProgressTracker
            analysisId={activeProcessingId}
            onCancel={() => {
              setActiveProcessingId(null)
              setIsOneClickRunning(false)
            }}
          />
        </div>
      )}

      {/* Main Card */}
      <div className="card shadow-2xl relative overflow-hidden border border-surface-600 bg-surface-800/90 mb-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-950/60 border border-red-700 text-red-200 flex items-start gap-3 animate-fade-in">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-semibold text-red-300">Pipeline Error</p>
              <p className="mt-0.5 text-red-200/90">{error}</p>
            </div>
          </div>
        )}

        {/* State 1: Dropzone & Showcase */}
        {!file && !uploadResult && (
          <div className="space-y-8">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200 ${
                isDragging
                  ? 'border-primary-400 bg-primary-950/30 scale-[1.01]'
                  : 'border-surface-500 hover:border-primary-500 hover:bg-surface-700/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept={ACCEPTED_EXTENSIONS.join(',')}
                onChange={handleFileChange}
              />

              <div className="w-16 h-16 rounded-2xl bg-primary-600/20 text-primary-400 mx-auto flex items-center justify-center mb-5 ring-1 ring-primary-500/30">
                <UploadCloud className="w-8 h-8" />
              </div>

              <h3 className="text-lg font-bold text-white mb-2">
                Drop your speech recording here, or <span className="text-primary-400 underline decoration-primary-500/50 underline-offset-4">browse</span>
              </h3>
              <p className="text-sm text-gray-400 mb-6 max-w-md mx-auto">
                Audio (WAV, MP3, M4A, FLAC) or Video (MP4, MOV, WebM) up to 500 MB. Zero manual reference needed.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-2">
                <span className="badge bg-surface-700 text-gray-300 border border-surface-600">
                  <FileAudio className="w-3.5 h-3.5 text-blue-400" />
                  Audio
                </span>
                <span className="badge bg-surface-700 text-gray-300 border border-surface-600">
                  <FileVideo className="w-3.5 h-3.5 text-purple-400" />
                  Video
                </span>
                <span className="badge bg-surface-700 text-gray-300 border border-surface-600">
                  <Music className="w-3.5 h-3.5 text-emerald-400" />
                  Auto-TTS Baseline
                </span>
              </div>
            </div>

            {/* Contrastive Showcase Section */}
            <div className="pt-6 border-t border-surface-700/80">
              <DemoShowcaseSection />
            </div>
          </div>
        )}

        {/* State 2: File Selected */}
        {file && !uploadResult && (
          <div className="space-y-6 animate-fade-in">
            <div className="p-5 rounded-xl bg-surface-700/60 border border-surface-500 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-primary-600/20 flex items-center justify-center flex-shrink-0 text-primary-400">
                  {isVideo ? <FileVideo className="w-6 h-6" /> : <FileAudio className="w-6 h-6" />}
                </div>
                <div>
                  <h4 className="font-semibold text-white truncate max-w-sm sm:max-w-md">{file.name}</h4>
                  <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
                    <span>{formatFileSize(file.size)}</span>
                    <span>•</span>
                    <span className="capitalize">{isVideo ? 'Video' : 'Audio'}</span>
                  </div>
                </div>
              </div>

              {!isProcessingMedia && (
                <button
                  onClick={handleReset}
                  className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-surface-600 transition-colors"
                  title="Choose different file"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
            </div>

            {isProcessingMedia && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium text-gray-300">
                  <span>Standardizing audio via FFmpeg to 16 kHz mono WAV...</span>
                  <span>{uploadProgress !== null ? `${uploadProgress}%` : ''}</span>
                </div>
                <div className="w-full bg-surface-700 h-2.5 rounded-full overflow-hidden">
                  <div
                    className="bg-primary-500 h-full rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${uploadProgress || 100}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
              <button
                onClick={handleReset}
                disabled={isProcessingMedia || isOneClickRunning}
                className="btn-secondary text-sm py-2 px-4"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={isProcessingMedia || isOneClickRunning}
                className="btn-secondary text-sm py-2 px-4 flex items-center gap-2"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Standardize Only</span>
              </button>
              <button
                onClick={handleUploadAndProcessAll}
                disabled={isProcessingMedia || isOneClickRunning}
                className="btn-primary flex items-center gap-2 text-sm py-2 px-5 bg-gradient-to-r from-primary-600 via-primary-500 to-accent-600 hover:from-primary-500 hover:to-accent-500 shadow-lg shadow-primary-950/40 text-white font-bold"
              >
                {isOneClickRunning ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Analyzing 10 Stages...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-accent-300 animate-pulse" />
                    <span>⚡ 1-Click Full Speech Analysis</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* State 3: Upload Complete */}
        {uploadResult && (
          <div className="space-y-6 animate-fade-in">
            {/* Top Bar with Media Summary */}
            <div className="p-4 rounded-xl bg-surface-700/60 border border-surface-600 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-950 border border-emerald-700 text-emerald-400 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-sm font-bold text-white flex items-center gap-2">
                    <span>{uploadResult.original_filename}</span>
                    <span className="badge bg-emerald-900/60 text-emerald-300 border border-emerald-700 text-[10px]">
                      16 kHz Mono WAV
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 flex items-center gap-3 mt-0.5">
                    <span>Duration: {formatDuration(uploadResult.duration)} ({uploadResult.duration.toFixed(2)}s)</span>
                    <span>•</span>
                    <span className="font-mono text-[11px] text-gray-500">ID: {uploadResult.analysis_id.slice(0, 8)}...</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons across pipeline */}
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={handleProcessAll}
                  disabled={isOneClickRunning}
                  className="btn-primary text-sm py-2 px-4 flex items-center gap-2 bg-gradient-to-r from-primary-600 via-primary-500 to-accent-600 hover:from-primary-500 hover:to-accent-500 shadow-lg shadow-primary-950/40 text-white font-bold"
                >
                  {isOneClickRunning ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Running Pipeline...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-accent-300 animate-pulse" />
                      <span>⚡ 1-Click Full Pipeline</span>
                    </>
                  )}
                </button>

                {!transcriptResult && (
                  <button
                    onClick={handleTranscribe}
                    disabled={isTranscribing}
                    className="btn-primary text-sm py-2 px-5 flex items-center gap-2 shadow-lg shadow-primary-900/30"
                  >
                    {isTranscribing ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Transcribing...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        <span>Transcribe Speech</span>
                      </>
                    )}
                  </button>
                )}

                {transcriptResult && !contentResult && (
                  <button
                    onClick={handleEvaluateContent}
                    disabled={isEvaluatingContent}
                    className="btn-primary text-sm py-2 px-4 flex items-center gap-2 bg-purple-600 hover:bg-purple-500 shadow-lg shadow-purple-900/30"
                  >
                    {isEvaluatingContent ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Evaluating...</span>
                      </>
                    ) : (
                      <>
                        <Brain className="w-4 h-4" />
                        <span>Evaluate Content</span>
                      </>
                    )}
                  </button>
                )}

                {transcriptResult && !referenceResult && (
                  <button
                    onClick={handleGenerateReference}
                    disabled={isGeneratingReference}
                    className="btn-primary text-sm py-2 px-4 flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-900/30"
                  >
                    {isGeneratingReference ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Synthesizing Reference...</span>
                      </>
                    ) : (
                      <>
                        <Radio className="w-4 h-4" />
                        <span>Generate Ideal Reference</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Spinners */}
            {isGeneratingReference && (
              <div className="py-10 px-6 rounded-xl bg-emerald-950/30 border border-emerald-700/40 text-center animate-fade-in">
                <div className="w-10 h-10 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin mx-auto mb-3" />
                <h4 className="text-sm font-bold text-white mb-1">Synthesizing Ideal Delivery Baseline...</h4>
                <p className="text-xs text-emerald-200/80 max-w-md mx-auto">
                  Automatically generating public-speaking reference from Track A wording and standardizing to 16 kHz mono WAV.
                </p>
              </div>
            )}

            {/* Phase 5: Multi-Track Audio Playback Studio */}
            {referenceResult && (
              <div className="space-y-4 animate-fade-in">
                {/* Reference Generated Banner */}
                <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-700 text-emerald-200 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    <div>
                      <h4 className="font-bold text-emerald-300 text-sm">AI Reference Generated</h4>
                      <p className="text-xs text-emerald-200/80">
                        Synthesized baseline ({referenceResult.duration.toFixed(1)}s) using {referenceResult.model_name} ({referenceResult.voice_name}).
                      </p>
                    </div>
                  </div>
                  <span className="badge bg-emerald-900/80 text-emerald-300 border border-emerald-700 text-[11px]">
                    Track A Grounding Ready
                  </span>
                </div>

                {/* Multi-Track Audio Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Track 1: Participant Audio */}
                  <div className="p-4 rounded-xl bg-surface-700/60 border border-surface-600 space-y-2">
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span className="text-gray-300 flex items-center gap-1.5">
                        <Volume2 className="w-4 h-4 text-primary-400" />
                        Participant Speech (Original)
                      </span>
                      <span className="text-gray-500 font-mono">16 kHz WAV</span>
                    </div>
                    <audio
                      ref={participantAudioRef}
                      controls
                      src={apiService.getAnalysisAudioUrl(uploadResult.analysis_id)}
                      className="w-full h-8 accent-primary-500 rounded"
                    />
                  </div>

                  {/* Track 2: Ideal Delivery Reference (Track A) */}
                  <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-700/50 space-y-2">
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span className="text-emerald-300 flex items-center gap-1.5">
                        <Radio className="w-4 h-4 text-emerald-400" />
                        Ideal Delivery Reference (Track A)
                      </span>
                      <span className="badge bg-emerald-900/80 text-emerald-300 border border-emerald-700 text-[10px]">
                        Acoustic Baseline
                      </span>
                    </div>
                    <audio
                      ref={referenceAudioRef}
                      controls
                      src={apiService.getReferenceAudioUrl(uploadResult.analysis_id)}
                      className="w-full h-8 accent-emerald-500 rounded"
                    />
                  </div>
                </div>

                {/* Optional Track 3: Improved Content Version Preview */}
                {referenceResult.has_improved_audio && (
                  <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-800/50 space-y-2">
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span className="text-purple-300 flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 text-purple-400" />
                        Improved Speech Preview (Track B — Learning Only)
                      </span>
                      <span className="badge bg-purple-900/60 text-purple-300 border border-purple-700 text-[10px]">
                        Content Preview
                      </span>
                    </div>
                    <audio
                      ref={improvedAudioRef}
                      controls
                      src={apiService.getImprovedAudioUrl(uploadResult.analysis_id)}
                      className="w-full h-8 accent-purple-500 rounded"
                    />
                    <p className="text-[10px] text-gray-500">
                      Synthesized from Gemini AI's improved script. Used solely for speaker learning, NOT as the forced alignment baseline.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Forced Alignment Studio (Phase 6) */}
            {alignmentResult && (
              <div className="p-5 rounded-2xl bg-surface-900/80 border border-primary-800/40 space-y-5 animate-fade-in shadow-xl">
                {/* Header & Badges */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-primary-600/20 border border-primary-500/30 flex items-center justify-center text-primary-400">
                      <GitCompare className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        Forced Alignment Studio (Phase 6)
                        <span className="badge bg-primary-900/60 text-primary-300 border border-primary-700 text-[10px]">
                          Acoustic Ground Truth
                        </span>
                      </h4>
                      <p className="text-xs text-gray-400">
                        Bidirectional time-mapping between participant speech and Track A reference audio
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`badge border text-xs font-semibold ${
                      alignmentResult.alignment_coverage >= 90
                        ? 'bg-emerald-950/80 border-emerald-700 text-emerald-300'
                        : alignmentResult.alignment_coverage >= 70
                        ? 'bg-amber-950/80 border-amber-700 text-amber-300'
                        : 'bg-red-950/80 border-red-700 text-red-300'
                    }`}>
                      Coverage: {alignmentResult.alignment_coverage.toFixed(1)}%
                    </span>
                    <span className="badge bg-surface-700 border-surface-500 text-gray-300 text-xs">
                      {alignmentResult.matched_word_count} / {alignmentResult.total_participant_words} Words Matched
                    </span>
                  </div>
                </div>

                {/* Metric Highlights */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                    <span className="text-gray-400 block mb-1">Participant Words</span>
                    <span className="text-base font-bold text-white font-mono">{alignmentResult.total_participant_words}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                    <span className="text-gray-400 block mb-1">Reference Words</span>
                    <span className="text-base font-bold text-white font-mono">{alignmentResult.total_reference_words}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                    <span className="text-gray-400 block mb-1">Aligned Pairs</span>
                    <span className="text-base font-bold text-emerald-400 font-mono">{alignmentResult.aligned_words.length}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                    <span className="text-gray-400 block mb-1">Aligned Phrases</span>
                    <span className="text-base font-bold text-primary-400 font-mono">{alignmentResult.aligned_phrases.length}</span>
                  </div>
                </div>

                {/* View Switcher Tabs */}
                <div className="flex items-center justify-between border-b border-surface-700 pb-2">
                  <div className="flex gap-2">
                    <button
                      onClick={() => setAlignmentViewMode('words')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        alignmentViewMode === 'words'
                          ? 'bg-primary-600 text-white'
                          : 'bg-surface-800 text-gray-400 hover:text-white'
                      }`}
                    >
                      Aligned Words ({alignmentResult.aligned_words.length})
                    </button>
                    <button
                      onClick={() => setAlignmentViewMode('phrases')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        alignmentViewMode === 'phrases'
                          ? 'bg-primary-600 text-white'
                          : 'bg-surface-800 text-gray-400 hover:text-white'
                      }`}
                    >
                      Aligned Phrases ({alignmentResult.aligned_phrases.length})
                    </button>
                  </div>

                  <span className="text-[11px] text-gray-400 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-primary-400" />
                    Click row to seek audio
                  </span>
                </div>

                {/* View 1: Aligned Words Table */}
                {alignmentViewMode === 'words' && (
                  <div className="overflow-x-auto max-h-72 overflow-y-auto rounded-xl border border-surface-700 bg-surface-900/50">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-surface-800/90 text-gray-400 sticky top-0 border-b border-surface-700">
                        <tr>
                          <th className="py-2.5 px-3 font-semibold">Word</th>
                          <th className="py-2.5 px-3 font-semibold">Participant Interval</th>
                          <th className="py-2.5 px-3 font-semibold">Ideal Ref Interval</th>
                          <th className="py-2.5 px-3 font-semibold">Temporal &Delta;</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Listen</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-700/60 font-mono text-[11px]">
                        {alignmentResult.aligned_words.map((item, idx) => {
                          const partDur = item.participant_end - item.participant_start
                          const refDur = item.reference_end - item.reference_start
                          const delta = partDur - refDur
                          const isSelected = highlightedWordIndex === idx

                          return (
                            <tr
                              key={idx}
                              onClick={() => handlePlayAlignedWord(item, idx)}
                              className={`cursor-pointer transition-colors ${
                                isSelected
                                  ? 'bg-primary-950/60 border-l-2 border-primary-500'
                                  : 'hover:bg-surface-800/60'
                              }`}
                            >
                              <td className="py-2 px-3 font-semibold font-sans text-gray-200">
                                <span className="text-white font-medium">{item.word}</span>
                              </td>
                              <td className="py-2 px-3 text-primary-300">
                                {item.participant_start.toFixed(2)}s – {item.participant_end.toFixed(2)}s
                                <span className="text-[10px] text-gray-400 ml-1.5 font-sans">({partDur.toFixed(2)}s)</span>
                              </td>
                              <td className="py-2 px-3 text-emerald-300">
                                {item.reference_start.toFixed(2)}s – {item.reference_end.toFixed(2)}s
                                <span className="text-[10px] text-gray-400 ml-1.5 font-sans">({refDur.toFixed(2)}s)</span>
                              </td>
                              <td className="py-2 px-3">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                  Math.abs(delta) < 0.1
                                    ? 'bg-emerald-950/80 text-emerald-400'
                                    : delta > 0
                                    ? 'bg-amber-950/80 text-amber-400'
                                    : 'bg-sky-950/80 text-sky-400'
                                }`}>
                                  {delta >= 0 ? `+${delta.toFixed(2)}s` : `${delta.toFixed(2)}s`}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-right">
                                <div className="inline-flex items-center gap-1.5">
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handlePlayAlignedWord(item, idx)
                                    }}
                                    className="p-1 rounded bg-surface-700 hover:bg-primary-600 text-gray-300 hover:text-white transition-colors"
                                    title="Play participant audio"
                                  >
                                    <Play className="w-3 h-3 fill-current" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handlePlayReferenceWord(item)
                                    }}
                                    className="p-1 rounded bg-surface-700 hover:bg-emerald-600 text-gray-300 hover:text-white transition-colors"
                                    title="Play reference audio"
                                  >
                                    <Radio className="w-3 h-3" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* View 2: Aligned Phrases Table */}
                {alignmentViewMode === 'phrases' && (
                  <div className="overflow-x-auto max-h-72 overflow-y-auto rounded-xl border border-surface-700 bg-surface-900/50">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-surface-800/90 text-gray-400 sticky top-0 border-b border-surface-700">
                        <tr>
                          <th className="py-2.5 px-3 font-semibold">#</th>
                          <th className="py-2.5 px-3 font-semibold">Phrase Text</th>
                          <th className="py-2.5 px-3 font-semibold">Participant</th>
                          <th className="py-2.5 px-3 font-semibold">Reference</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-700/60 font-mono text-[11px]">
                        {alignmentResult.aligned_phrases.map((phrase) => {
                          const partDur = phrase.participant_end - phrase.participant_start
                          const refDur = phrase.reference_end - phrase.reference_start

                          return (
                            <tr
                              key={phrase.phrase_id}
                              onClick={() => handlePlayAlignedPhrase(phrase)}
                              className="cursor-pointer hover:bg-surface-800/60 transition-colors"
                            >
                              <td className="py-2 px-3 text-gray-500">{phrase.phrase_id}</td>
                              <td className="py-2 px-3 font-sans font-medium text-gray-200">
                                "{phrase.text}"
                                <span className="text-[10px] text-gray-400 ml-1.5 font-sans">({phrase.word_count} words)</span>
                              </td>
                              <td className="py-2 px-3 text-primary-300">
                                {phrase.participant_start.toFixed(2)}s – {phrase.participant_end.toFixed(2)}s ({partDur.toFixed(2)}s)
                              </td>
                              <td className="py-2 px-3 text-emerald-300">
                                {phrase.reference_start.toFixed(2)}s – {phrase.reference_end.toFixed(2)}s ({refDur.toFixed(2)}s)
                              </td>
                              <td className="py-2 px-3 text-right">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handlePlayAlignedPhrase(phrase)
                                  }}
                                  className="p-1 rounded bg-surface-700 hover:bg-primary-600 text-gray-300 hover:text-white transition-colors"
                                  title="Play phrase audio"
                                >
                                  <Play className="w-3 h-3 fill-current" />
                                </button>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Discrepancies notification */}
                {(alignmentResult.unmatched_participant_words.length > 0 || alignmentResult.unmatched_reference_words.length > 0) && (
                  <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-800/50 text-xs text-amber-300 space-y-1">
                    <p className="font-semibold flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Alignment Discrepancies Noted
                    </p>
                    {alignmentResult.unmatched_participant_words.length > 0 && (
                      <p className="text-[11px] text-gray-400">
                        Unmatched participant words: {alignmentResult.unmatched_participant_words.join(', ')}
                      </p>
                    )}
                    {alignmentResult.unmatched_reference_words.length > 0 && (
                      <p className="text-[11px] text-gray-400">
                        Unmatched reference words: {alignmentResult.unmatched_reference_words.join(', ')}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Acoustic Feature Profiler (Phase 7) */}
            {featuresResult && (
              <div className="p-5 rounded-2xl bg-surface-900/80 border border-sky-800/40 space-y-5 animate-fade-in shadow-xl">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-sky-600/20 border border-sky-500/30 flex items-center justify-center text-sky-400">
                      <TrendingUp className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        Acoustic Feature Profiler (Phase 7)
                        <span className="badge bg-sky-900/60 text-sky-300 border border-sky-700 text-[10px]">Bitrack Analysis</span>
                      </h4>
                      <p className="text-xs text-gray-400">Participant vs Ideal Reference — Pitch · Energy · Rhythm · Spectral · MFCC</p>
                    </div>
                  </div>
                  <div className="flex gap-1.5 flex-wrap text-[10px] font-semibold">
                    <span className="badge bg-sky-950/70 border-sky-700 text-sky-300">
                      WPM: {featuresResult.participant_features.rhythm.words_per_minute}
                    </span>
                    <span className="badge bg-surface-700 border-surface-500 text-gray-300">
                      Pauses: {featuresResult.participant_features.rhythm.pause_count}
                    </span>
                  </div>
                </div>

                {/* Comparison stat grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  {[
                    { label: 'Mean Pitch', p: `${featuresResult.participant_features.pitch.mean_f0} Hz`, r: `${featuresResult.reference_features.pitch.mean_f0} Hz`, color: 'sky' },
                    { label: 'Pitch Std Dev', p: `${featuresResult.participant_features.pitch.std_f0} Hz`, r: `${featuresResult.reference_features.pitch.std_f0} Hz`, color: 'sky' },
                    { label: 'Pitch Range', p: `${featuresResult.participant_features.pitch.pitch_range_semitones} st`, r: `${featuresResult.reference_features.pitch.pitch_range_semitones} st`, color: 'sky' },
                    { label: 'WPM', p: `${featuresResult.participant_features.rhythm.words_per_minute}`, r: `${featuresResult.reference_features.rhythm.words_per_minute}`, color: 'emerald' },
                    { label: 'Pause Count', p: `${featuresResult.participant_features.rhythm.pause_count}`, r: `${featuresResult.reference_features.rhythm.pause_count}`, color: 'amber' },
                    { label: 'Voiced Ratio', p: `${(featuresResult.participant_features.pitch.voiced_fraction * 100).toFixed(0)}%`, r: `${(featuresResult.reference_features.pitch.voiced_fraction * 100).toFixed(0)}%`, color: 'sky' },
                    { label: 'Mean Energy', p: featuresResult.participant_features.energy.mean_rms.toFixed(3), r: featuresResult.reference_features.energy.mean_rms.toFixed(3), color: 'orange' },
                    { label: 'Dynamic Range', p: `${featuresResult.participant_features.energy.dynamic_range_db} dB`, r: `${featuresResult.reference_features.energy.dynamic_range_db} dB`, color: 'orange' },
                  ].map(item => (
                    <div key={item.label} className="p-2.5 rounded-xl bg-surface-800 border border-surface-600 space-y-1.5">
                      <p className="text-[10px] text-gray-400 font-semibold uppercase tracking-wide">{item.label}</p>
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-bold text-sky-300`}>{item.p}</span>
                        <span className="text-[10px] text-gray-500">vs</span>
                        <span className="text-xs font-bold text-emerald-300">{item.r}</span>
                      </div>
                      <div className="flex items-center gap-1 text-[9px] text-gray-500">
                        <span className="w-2 h-2 rounded-full bg-sky-400 inline-block" />You
                        <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block ml-1" />Ref
                      </div>
                    </div>
                  ))}
                </div>

                {/* Tab switcher */}
                <div className="flex gap-1.5 border-b border-surface-700 pb-2 overflow-x-auto">
                  {(['pitch', 'energy', 'rhythm', 'spectral', 'words'] as const).map(tab => (
                    <button
                      key={tab}
                      onClick={() => setFeaturesTab(tab)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                        featuresTab === tab ? 'bg-sky-600 text-white' : 'bg-surface-800 text-gray-400 hover:text-white'
                      }`}
                    >
                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                  ))}
                </div>

                {/* Pitch Panel */}
                {featuresTab === 'pitch' && (
                  <div className="space-y-3 text-xs">
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        ['Min F0', featuresResult.participant_features.pitch.min_f0, featuresResult.reference_features.pitch.min_f0, 'Hz'],
                        ['Median F0', featuresResult.participant_features.pitch.median_f0, featuresResult.reference_features.pitch.median_f0, 'Hz'],
                        ['Max F0', featuresResult.participant_features.pitch.max_f0, featuresResult.reference_features.pitch.max_f0, 'Hz'],
                      ].map(([label, p, r, unit]) => (
                        <div key={label as string} className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                          <p className="text-gray-400 text-[10px] font-semibold uppercase mb-1">{label as string}</p>
                          <p className="text-sky-300 font-bold">{p as number} <span className="text-gray-500 font-normal">{unit as string}</span></p>
                          <p className="text-emerald-300 text-[11px]">Ref: {r as number} {unit as string}</p>
                        </div>
                      ))}
                    </div>
                    <div className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                      <p className="text-gray-400 text-[10px] font-semibold uppercase mb-2">Pitch Contour (100 frames)</p>
                      <div className="flex items-end gap-0.5 h-16">
                        {featuresResult.participant_features.pitch.contour.map((v, i) => {
                          const maxV = Math.max(...featuresResult.participant_features.pitch.contour.filter(x => x > 0))
                          const height = maxV > 0 ? Math.max(2, (v / maxV) * 100) : 2
                          return <div key={i} style={{ height: `${height}%` }} className="flex-1 bg-sky-500/60 rounded-sm" />
                        })}
                      </div>
                      <div className="flex items-end gap-0.5 h-12 mt-1.5">
                        {featuresResult.reference_features.pitch.contour.map((v, i) => {
                          const maxV = Math.max(...featuresResult.reference_features.pitch.contour.filter(x => x > 0))
                          const height = maxV > 0 ? Math.max(2, (v / maxV) * 100) : 2
                          return <div key={i} style={{ height: `${height}%` }} className="flex-1 bg-emerald-500/60 rounded-sm" />
                        })}
                      </div>
                      <div className="flex items-center gap-4 mt-1.5 text-[10px] text-gray-400">
                        <span><span className="inline-block w-2 h-2 rounded-sm bg-sky-500/60 mr-1" />Participant</span>
                        <span><span className="inline-block w-2 h-2 rounded-sm bg-emerald-500/60 mr-1" />Reference</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Energy Panel */}
                {featuresTab === 'energy' && (
                  <div className="space-y-3 text-xs">
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        ['Std RMS', featuresResult.participant_features.energy.std_rms.toFixed(4), featuresResult.reference_features.energy.std_rms.toFixed(4)],
                        ['Peak RMS', featuresResult.participant_features.energy.max_rms.toFixed(4), featuresResult.reference_features.energy.max_rms.toFixed(4)],
                      ].map(([label, p, r]) => (
                        <div key={label} className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                          <p className="text-gray-400 text-[10px] font-semibold uppercase mb-1">{label}</p>
                          <p className="text-sky-300 font-bold font-mono">{p}</p>
                          <p className="text-emerald-300 text-[11px] font-mono">Ref: {r}</p>
                        </div>
                      ))}
                    </div>
                    <div className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                      <p className="text-gray-400 text-[10px] font-semibold uppercase mb-2">Energy Contour (RMS per Frame)</p>
                      <div className="flex items-end gap-0.5 h-16">
                        {featuresResult.participant_features.energy.contour.map((v, i) => {
                          const maxV = Math.max(...featuresResult.participant_features.energy.contour)
                          const height = maxV > 0 ? Math.max(2, (v / maxV) * 100) : 2
                          return <div key={i} style={{ height: `${height}%` }} className="flex-1 bg-orange-500/60 rounded-sm" />
                        })}
                      </div>
                      <div className="flex items-end gap-0.5 h-12 mt-1.5">
                        {featuresResult.reference_features.energy.contour.map((v, i) => {
                          const maxV = Math.max(...featuresResult.reference_features.energy.contour)
                          const height = maxV > 0 ? Math.max(2, (v / maxV) * 100) : 2
                          return <div key={i} style={{ height: `${height}%` }} className="flex-1 bg-emerald-500/60 rounded-sm" />
                        })}
                      </div>
                      <div className="flex items-center gap-4 mt-1.5 text-[10px] text-gray-400">
                        <span><span className="inline-block w-2 h-2 rounded-sm bg-orange-500/60 mr-1" />Participant</span>
                        <span><span className="inline-block w-2 h-2 rounded-sm bg-emerald-500/60 mr-1" />Reference</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Rhythm Panel */}
                {featuresTab === 'rhythm' && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                    {[
                      { label: 'Total Duration', p: `${featuresResult.participant_features.rhythm.total_duration}s`, r: `${featuresResult.reference_features.rhythm.total_duration}s` },
                      { label: 'Speaking Duration', p: `${featuresResult.participant_features.rhythm.speaking_duration}s`, r: `${featuresResult.reference_features.rhythm.speaking_duration}s` },
                      { label: 'Pause Duration', p: `${featuresResult.participant_features.rhythm.pause_duration}s`, r: `${featuresResult.reference_features.rhythm.pause_duration}s` },
                      { label: 'Pause Count', p: `${featuresResult.participant_features.rhythm.pause_count}`, r: `${featuresResult.reference_features.rhythm.pause_count}` },
                      { label: 'Mean Pause', p: `${featuresResult.participant_features.rhythm.mean_pause_duration}s`, r: `${featuresResult.reference_features.rhythm.mean_pause_duration}s` },
                      { label: 'Pause/Speech Ratio', p: `${featuresResult.participant_features.rhythm.pause_to_speech_ratio}`, r: `${featuresResult.reference_features.rhythm.pause_to_speech_ratio}` },
                      { label: 'Words/Min (WPM)', p: `${featuresResult.participant_features.rhythm.words_per_minute}`, r: `${featuresResult.reference_features.rhythm.words_per_minute}` },
                      { label: 'Articulation Rate', p: `${featuresResult.participant_features.rhythm.articulation_rate}`, r: `${featuresResult.reference_features.rhythm.articulation_rate}` },
                    ].map(item => (
                      <div key={item.label} className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                        <p className="text-gray-400 text-[10px] font-semibold uppercase tracking-wide mb-1">{item.label}</p>
                        <p className="text-sky-300 font-bold">{item.p}</p>
                        <p className="text-emerald-300 text-[11px]">Ref: {item.r}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Spectral Panel */}
                {featuresTab === 'spectral' && (
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    {[
                      { label: 'Spectral Centroid (Brightness)', p: `${featuresResult.participant_features.spectral.mean_spectral_centroid} Hz`, r: `${featuresResult.reference_features.spectral.mean_spectral_centroid} Hz` },
                      { label: 'Spectral Bandwidth', p: `${featuresResult.participant_features.spectral.mean_spectral_bandwidth} Hz`, r: `${featuresResult.reference_features.spectral.mean_spectral_bandwidth} Hz` },
                      { label: 'Spectral Roll-off (85%)', p: `${featuresResult.participant_features.spectral.mean_spectral_rolloff} Hz`, r: `${featuresResult.reference_features.spectral.mean_spectral_rolloff} Hz` },
                      { label: 'Zero Crossing Rate', p: featuresResult.participant_features.spectral.mean_zero_crossing_rate.toFixed(4), r: featuresResult.reference_features.spectral.mean_zero_crossing_rate.toFixed(4) },
                    ].map(item => (
                      <div key={item.label} className="p-3 rounded-xl bg-surface-800 border border-surface-600">
                        <p className="text-gray-400 text-[10px] font-semibold uppercase tracking-wide mb-1">{item.label}</p>
                        <p className="text-sky-300 font-bold">{item.p}</p>
                        <p className="text-emerald-300 text-[11px]">Ref: {item.r}</p>
                      </div>
                    ))}
                    <div className="col-span-2 p-3 rounded-xl bg-surface-800 border border-surface-600">
                      <p className="text-gray-400 text-[10px] font-semibold uppercase mb-2">MFCC Coefficients (13)</p>
                      <div className="flex items-end gap-1 h-14">
                        {featuresResult.participant_features.mfcc.mean_mfcc.map((v, i) => {
                          const allVals = [...featuresResult.participant_features.mfcc.mean_mfcc, ...featuresResult.reference_features.mfcc.mean_mfcc]
                          const maxAbs = Math.max(1, ...allVals.map(Math.abs))
                          const height = Math.max(4, (Math.abs(v) / maxAbs) * 100)
                          return <div key={i} style={{ height: `${height}%` }} className={`flex-1 rounded-sm ${v >= 0 ? 'bg-sky-500/60' : 'bg-sky-800/60'}`} title={`MFCC ${i + 1}: ${v.toFixed(1)}`} />
                        })}
                      </div>
                      <div className="flex items-end gap-1 h-10 mt-1">
                        {featuresResult.reference_features.mfcc.mean_mfcc.map((v, i) => {
                          const allVals = [...featuresResult.participant_features.mfcc.mean_mfcc, ...featuresResult.reference_features.mfcc.mean_mfcc]
                          const maxAbs = Math.max(1, ...allVals.map(Math.abs))
                          const height = Math.max(4, (Math.abs(v) / maxAbs) * 100)
                          return <div key={i} style={{ height: `${height}%` }} className={`flex-1 rounded-sm ${v >= 0 ? 'bg-emerald-500/60' : 'bg-emerald-800/60'}`} title={`MFCC ${i + 1}: ${v.toFixed(1)}`} />
                        })}
                      </div>
                      <div className="flex items-center gap-4 mt-1.5 text-[10px] text-gray-400">
                        <span><span className="inline-block w-2 h-2 rounded-sm bg-sky-500/60 mr-1" />Participant</span>
                        <span><span className="inline-block w-2 h-2 rounded-sm bg-emerald-500/60 mr-1" />Reference</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Word-level Panel */}
                {featuresTab === 'words' && featuresResult.participant_features.word_features.length > 0 && (
                  <div className="overflow-x-auto max-h-72 overflow-y-auto rounded-xl border border-surface-700 bg-surface-900/50">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-surface-800/90 text-gray-400 sticky top-0 border-b border-surface-700">
                        <tr>
                          <th className="py-2 px-3 font-semibold">Word</th>
                          <th className="py-2 px-3 font-semibold">Interval</th>
                          <th className="py-2 px-3 font-semibold">Duration</th>
                          <th className="py-2 px-3 font-semibold">Mean F0</th>
                          <th className="py-2 px-3 font-semibold">Energy</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-700/60 font-mono text-[11px]">
                        {featuresResult.participant_features.word_features.map((wf, idx) => (
                          <tr
                            key={idx}
                            onClick={() => {
                              if (participantAudioRef.current) {
                                participantAudioRef.current.currentTime = wf.start
                                participantAudioRef.current.play()
                              }
                            }}
                            className="cursor-pointer hover:bg-surface-800/60 transition-colors"
                          >
                            <td className="py-1.5 px-3 font-sans font-semibold text-white">{wf.word}</td>
                            <td className="py-1.5 px-3 text-sky-300">{wf.start.toFixed(2)}–{wf.end.toFixed(2)}s</td>
                            <td className="py-1.5 px-3 text-gray-300">{wf.duration.toFixed(2)}s</td>
                            <td className="py-1.5 px-3 text-amber-300">{wf.mean_f0 != null ? `${wf.mean_f0} Hz` : '—'}</td>
                            <td className="py-1.5 px-3 text-orange-300">{wf.mean_energy.toFixed(4)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {featuresTab === 'words' && featuresResult.participant_features.word_features.length === 0 && (
                  <p className="text-xs text-gray-400 text-center py-4">No word-level features available. Run forced alignment first for word-by-word acoustics.</p>
                )}
              </div>
            )}

            {/* Contrastive Acoustic Comparison Studio (Phase 8) */}
            {comparisonResult && (
              <div className="p-5 rounded-2xl bg-surface-900/80 border border-indigo-800/50 space-y-5 animate-fade-in shadow-xl">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                      <Scale className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        Contrastive Delivery Comparison (Phase 8)
                        <span className="badge bg-indigo-900/60 text-indigo-300 border border-indigo-700 text-[10px]">DTW & Deviations</span>
                      </h4>
                      <p className="text-xs text-gray-400">
                        Mathematical divergence vs Track A Ideal Reference across 5 acoustic dimensions
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="text-right">
                      <div className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Overall Delivery Match</div>
                      <div className="text-lg font-black text-indigo-400">
                        {comparisonResult.summary.overall_similarity_score.toFixed(1)}%
                      </div>
                    </div>
                    <span className={`badge border text-xs px-2.5 py-1 ${getScoreColor(comparisonResult.summary.overall_similarity_score)}`}>
                      {comparisonResult.summary.overall_similarity_score >= 80 ? 'High Fidelity' : comparisonResult.summary.overall_similarity_score >= 60 ? 'Moderate Match' : 'High Deviation'}
                    </span>
                  </div>
                </div>

                {/* 5-Dimension Score Gauges */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {/* Pace */}
                  <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-600/60 flex flex-col justify-between">
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                      <span className="flex items-center gap-1"><Timer className="w-3.5 h-3.5 text-blue-400" /> Pace</span>
                      <span className="font-bold text-white text-xs">{comparisonResult.pace.similarity_score.toFixed(0)}%</span>
                    </div>
                    <div className="text-sm font-bold text-white mb-0.5">
                      {comparisonResult.pace.delta_wpm > 0 ? `+${comparisonResult.pace.delta_wpm}` : comparisonResult.pace.delta_wpm} WPM
                    </div>
                    <div className="text-[10px] text-gray-400 flex items-center justify-between">
                      <span>{comparisonResult.pace.participant_wpm} vs {comparisonResult.pace.reference_wpm}</span>
                      <span className={`badge px-1.5 py-0 text-[9px] ${comparisonResult.pace.status === 'optimal_tempo' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-amber-950 text-amber-400 border-amber-800'}`}>
                        {comparisonResult.pace.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  {/* Pitch / Melody */}
                  <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-600/60 flex flex-col justify-between">
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                      <span className="flex items-center gap-1"><Activity className="w-3.5 h-3.5 text-violet-400" /> Pitch</span>
                      <span className="font-bold text-white text-xs">{comparisonResult.pitch.similarity_score.toFixed(0)}%</span>
                    </div>
                    <div className="text-sm font-bold text-white mb-0.5">
                      {comparisonResult.pitch.pitch_variation_ratio.toFixed(2)}× Var
                    </div>
                    <div className="text-[10px] text-gray-400 flex items-center justify-between">
                      <span>DTW: {comparisonResult.pitch.dtw.normalized_distance.toFixed(1)}</span>
                      <span className={`badge px-1.5 py-0 text-[9px] ${comparisonResult.pitch.status === 'expressive_prosody' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-amber-950 text-amber-400 border-amber-800'}`}>
                        {comparisonResult.pitch.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  {/* Pauses / Rhythm */}
                  <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-600/60 flex flex-col justify-between">
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                      <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5 text-emerald-400" /> Cadence</span>
                      <span className="font-bold text-white text-xs">{comparisonResult.pause.similarity_score.toFixed(0)}%</span>
                    </div>
                    <div className="text-sm font-bold text-white mb-0.5">
                      {comparisonResult.pause.delta_pause_count > 0 ? `+${comparisonResult.pause.delta_pause_count}` : comparisonResult.pause.delta_pause_count} Pauses
                    </div>
                    <div className="text-[10px] text-gray-400 flex items-center justify-between">
                      <span>{comparisonResult.pause.participant_pause_count} vs {comparisonResult.pause.reference_pause_count}</span>
                      <span className={`badge px-1.5 py-0 text-[9px] ${comparisonResult.pause.status === 'balanced_cadence' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-amber-950 text-amber-400 border-amber-800'}`}>
                        {comparisonResult.pause.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  {/* Energy Dynamics */}
                  <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-600/60 flex flex-col justify-between">
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                      <span className="flex items-center gap-1"><Volume2 className="w-3.5 h-3.5 text-amber-400" /> Dynamics</span>
                      <span className="font-bold text-white text-xs">{comparisonResult.energy.similarity_score.toFixed(0)}%</span>
                    </div>
                    <div className="text-sm font-bold text-white mb-0.5">
                      {comparisonResult.energy.energy_ratio.toFixed(2)}× Energy
                    </div>
                    <div className="text-[10px] text-gray-400 flex items-center justify-between">
                      <span>{comparisonResult.energy.delta_dynamic_range_db > 0 ? `+${comparisonResult.energy.delta_dynamic_range_db}` : comparisonResult.energy.delta_dynamic_range_db} dB</span>
                      <span className={`badge px-1.5 py-0 text-[9px] ${comparisonResult.energy.status === 'balanced_projection' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-amber-950 text-amber-400 border-amber-800'}`}>
                        {comparisonResult.energy.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  {/* Timbre & Articulation */}
                  <div className="p-3 rounded-xl bg-surface-800/80 border border-surface-600/60 flex flex-col justify-between col-span-2 sm:col-span-1">
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                      <span className="flex items-center gap-1"><Music className="w-3.5 h-3.5 text-cyan-400" /> Timbre</span>
                      <span className="font-bold text-white text-xs">{comparisonResult.timbre.similarity_score.toFixed(0)}%</span>
                    </div>
                    <div className="text-sm font-bold text-white mb-0.5">
                      {comparisonResult.timbre.mfcc_cosine_distance.toFixed(3)} Dist
                    </div>
                    <div className="text-[10px] text-gray-400 flex items-center justify-between">
                      <span>Centroid: {comparisonResult.timbre.delta_spectral_centroid > 0 ? `+${comparisonResult.timbre.delta_spectral_centroid}` : comparisonResult.timbre.delta_spectral_centroid} Hz</span>
                      <span className={`badge px-1.5 py-0 text-[9px] ${comparisonResult.timbre.status === 'clear_articulation' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-amber-950 text-amber-400 border-amber-800'}`}>
                        {comparisonResult.timbre.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex items-center gap-1.5 border-b border-surface-700 pb-2 text-xs">
                  <button
                    onClick={() => setComparisonTab('overview')}
                    className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${comparisonTab === 'overview' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white hover:bg-surface-800'}`}
                  >
                    Overview & Deviations
                  </button>
                  <button
                    onClick={() => setComparisonTab('dtw')}
                    className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${comparisonTab === 'dtw' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white hover:bg-surface-800'}`}
                  >
                    DTW Warping Path
                  </button>
                  <button
                    onClick={() => setComparisonTab('words')}
                    className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${comparisonTab === 'words' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white hover:bg-surface-800'}`}
                  >
                    Word-by-Word Contrast ({comparisonResult.aligned_words_comparison.length})
                  </button>
                  <button
                    onClick={() => setComparisonTab('prosody')}
                    className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${comparisonTab === 'prosody' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white hover:bg-surface-800'}`}
                  >
                    Contrastive Matrices
                  </button>
                </div>

                {/* Tab 1: Overview & Primary Deviations */}
                {comparisonTab === 'overview' && (
                  <div className="space-y-4">
                    {/* Primary flaws callout */}
                    {comparisonResult.summary.primary_delivery_flaws.length > 0 ? (
                      <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/40 space-y-2">
                        <div className="flex items-center gap-2 text-xs font-bold text-amber-400">
                          <AlertTriangle className="w-4 h-4" />
                          <span>Mathematically Detected Delivery Discrepancies</span>
                        </div>
                        <ul className="space-y-1.5 text-xs text-gray-300">
                          {comparisonResult.summary.primary_delivery_flaws.map((flaw, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-amber-400 font-bold">•</span>
                              <span>{flaw}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-xs text-emerald-300 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Acoustic and temporal alignment closely follows the ideal delivery baseline!</span>
                      </div>
                    )}

                    {/* Detailed Metric Delta Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-3.5 rounded-xl bg-surface-800/60 border border-surface-700/60 space-y-2">
                        <div className="font-semibold text-gray-300 flex items-center justify-between">
                          <span>Pace & Articulation Rates</span>
                          <span className="text-gray-500 font-mono text-[10px]">Δ (Participant - Ideal)</span>
                        </div>
                        <div className="space-y-1.5 font-mono text-[11px]">
                          <div className="flex justify-between py-1 border-b border-surface-700/40">
                            <span className="text-gray-400 font-sans">Words Per Minute</span>
                            <span className="text-white">{comparisonResult.pace.participant_wpm} vs {comparisonResult.pace.reference_wpm} <strong className={comparisonResult.pace.delta_wpm > 0 ? 'text-amber-400' : 'text-blue-400'}>({comparisonResult.pace.delta_wpm > 0 ? `+${comparisonResult.pace.delta_wpm}` : comparisonResult.pace.delta_wpm})</strong></span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-surface-700/40">
                            <span className="text-gray-400 font-sans">Speaking Time Ratio</span>
                            <span className="text-white">{comparisonResult.pace.participant_speaking_duration}s vs {comparisonResult.pace.reference_speaking_duration}s <strong className="text-sky-300">({comparisonResult.pace.duration_ratio}×)</strong></span>
                          </div>
                          <div className="flex justify-between py-1">
                            <span className="text-gray-400 font-sans">Articulation Rate</span>
                            <span className="text-white">{comparisonResult.timbre.participant_articulation_rate} vs {comparisonResult.timbre.reference_articulation_rate} <strong className="text-cyan-300">({comparisonResult.timbre.delta_articulation_rate > 0 ? `+${comparisonResult.timbre.delta_articulation_rate}` : comparisonResult.timbre.delta_articulation_rate} WPM)</strong></span>
                          </div>
                        </div>
                      </div>

                      <div className="p-3.5 rounded-xl bg-surface-800/60 border border-surface-700/60 space-y-2">
                        <div className="font-semibold text-gray-300 flex items-center justify-between">
                          <span>Pitch & Vocal Range</span>
                          <span className="text-gray-500 font-mono text-[10px]">Δ (Participant - Ideal)</span>
                        </div>
                        <div className="space-y-1.5 font-mono text-[11px]">
                          <div className="flex justify-between py-1 border-b border-surface-700/40">
                            <span className="text-gray-400 font-sans">Mean Pitch (F0)</span>
                            <span className="text-white">{comparisonResult.pitch.participant_mean_f0} Hz vs {comparisonResult.pitch.reference_mean_f0} Hz <strong className="text-violet-300">({comparisonResult.pitch.delta_mean_f0 > 0 ? `+${comparisonResult.pitch.delta_mean_f0}` : comparisonResult.pitch.delta_mean_f0} Hz)</strong></span>
                          </div>
                          <div className="flex justify-between py-1 border-b border-surface-700/40">
                            <span className="text-gray-400 font-sans">Pitch Variation Ratio</span>
                            <span className="text-white">{comparisonResult.pitch.participant_std_f0} Hz vs {comparisonResult.pitch.reference_std_f0} Hz <strong className={comparisonResult.pitch.pitch_variation_ratio < 0.65 ? 'text-amber-400' : 'text-emerald-400'}>({comparisonResult.pitch.pitch_variation_ratio}×)</strong></span>
                          </div>
                          <div className="flex justify-between py-1">
                            <span className="text-gray-400 font-sans">Dynamic Range</span>
                            <span className="text-white">{comparisonResult.pitch.participant_range_semitones} st vs {comparisonResult.pitch.reference_range_semitones} st <strong className="text-indigo-300">({comparisonResult.pitch.delta_semitones > 0 ? `+${comparisonResult.pitch.delta_semitones}` : comparisonResult.pitch.delta_semitones} st)</strong></span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab 2: DTW Warping Path */}
                {comparisonTab === 'dtw' && (
                  <div className="space-y-4">
                    <div className="p-3 rounded-xl bg-surface-800/60 border border-surface-700/60 text-xs text-gray-300 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <span className="font-bold text-white block">Dynamic Time Warping (DTW) Non-Linear Alignment</span>
                        <span className="text-gray-400 text-[11px]">Finds optimal monotonic mapping between asynchronous speech streams to score prosodic trajectory.</span>
                      </div>
                      <div className="flex items-center gap-3 font-mono text-[11px] text-right">
                        <div>
                          <div className="text-gray-500 text-[9px] uppercase">Pitch DTW Cost</div>
                          <div className="font-bold text-violet-300">{comparisonResult.pitch.dtw.accumulated_cost} ({comparisonResult.pitch.dtw.normalized_distance} /step)</div>
                        </div>
                        <div>
                          <div className="text-gray-500 text-[9px] uppercase">Energy DTW Cost</div>
                          <div className="font-bold text-amber-300">{comparisonResult.energy.dtw.accumulated_cost} ({comparisonResult.energy.dtw.normalized_distance} /step)</div>
                        </div>
                      </div>
                    </div>

                    {/* DTW Sample Warping Path Table */}
                    <div className="overflow-x-auto rounded-xl border border-surface-700/60 bg-surface-900/60">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-surface-800/80 text-gray-400 text-[10px] uppercase">
                          <tr>
                            <th className="py-2 px-3">Node #</th>
                            <th className="py-2 px-3">Participant Index</th>
                            <th className="py-2 px-3">Reference Index</th>
                            <th className="py-2 px-3">Participant Norm Time</th>
                            <th className="py-2 px-3">Reference Norm Time</th>
                            <th className="py-2 px-3">Temporal Shift</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-surface-800/60 text-gray-300 text-[11px]">
                          {comparisonResult.pitch.dtw.sample_path.map((node, idx) => {
                            const shift = Math.round((node.normalized_participant_time - node.normalized_reference_time) * 1000) / 10
                            return (
                              <tr key={idx} className="hover:bg-surface-800/40">
                                <td className="py-1.5 px-3 text-gray-500">{idx + 1}</td>
                                <td className="py-1.5 px-3 text-sky-300">frame {node.participant_index}</td>
                                <td className="py-1.5 px-3 text-emerald-300">frame {node.reference_index}</td>
                                <td className="py-1.5 px-3">{node.normalized_participant_time.toFixed(2)}</td>
                                <td className="py-1.5 px-3">{node.normalized_reference_time.toFixed(2)}</td>
                                <td className="py-1.5 px-3">
                                  <span className={`badge px-1.5 py-0 text-[9px] ${Math.abs(shift) < 5 ? 'bg-surface-700 text-gray-300' : shift > 0 ? 'bg-amber-950 text-amber-300 border-amber-800' : 'bg-blue-950 text-blue-300 border-blue-800'}`}>
                                    {shift > 0 ? `+${shift}% lag` : shift < 0 ? `${shift}% lead` : 'aligned'}
                                  </span>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Tab 3: Word-by-Word Contrast */}
                {comparisonTab === 'words' && (
                  <div className="space-y-3">
                    <div className="overflow-x-auto rounded-xl border border-surface-700/60 bg-surface-900/60">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-surface-800/80 text-gray-400 text-[10px] uppercase">
                          <tr>
                            <th className="py-2 px-3 font-sans">Word</th>
                            <th className="py-2 px-3">Participant Time</th>
                            <th className="py-2 px-3">Reference Time</th>
                            <th className="py-2 px-3">Dur Ratio (P/R)</th>
                            <th className="py-2 px-3">Tempo Flag</th>
                            <th className="py-2 px-3">Pitch Δ (Hz)</th>
                            <th className="py-2 px-3">Emphasis</th>
                            <th className="py-2 px-3 text-right">Seek</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-surface-800/60 text-gray-300 text-[11px]">
                          {comparisonResult.aligned_words_comparison.map((item, idx) => (
                            <tr
                              key={idx}
                              onClick={() => {
                                if (participantAudioRef.current) {
                                  participantAudioRef.current.currentTime = item.participant_start
                                  participantAudioRef.current.play()
                                }
                              }}
                              className="cursor-pointer hover:bg-surface-800/60 transition-colors"
                            >
                              <td className="py-2 px-3 font-sans font-bold text-white">{item.word}</td>
                              <td className="py-2 px-3 text-sky-300">{item.participant_start.toFixed(2)}–{item.participant_end.toFixed(2)}s ({item.participant_duration.toFixed(2)}s)</td>
                              <td className="py-2 px-3 text-emerald-300">{item.reference_start.toFixed(2)}–{item.reference_end.toFixed(2)}s ({item.reference_duration.toFixed(2)}s)</td>
                              <td className="py-2 px-3 text-white font-bold">{item.duration_ratio.toFixed(2)}×</td>
                              <td className="py-2 px-3">
                                <span className={`badge px-1.5 py-0 text-[9px] ${item.tempo_flag === 'stretched' ? 'bg-amber-950 text-amber-300 border-amber-800' : item.tempo_flag === 'compressed' ? 'bg-purple-950 text-purple-300 border-purple-800' : 'bg-surface-700 text-gray-300'}`}>
                                  {item.tempo_flag}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-violet-300">
                                {item.pitch_delta_hz != null ? `${item.pitch_delta_hz > 0 ? `+${item.pitch_delta_hz}` : item.pitch_delta_hz} Hz` : '—'}
                              </td>
                              <td className="py-2 px-3">
                                <span className={`badge px-1.5 py-0 text-[9px] ${item.emphasis_flag === 'accented' ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : item.emphasis_flag === 'reduced' ? 'bg-red-950 text-red-300 border-red-800' : 'bg-surface-700 text-gray-300'}`}>
                                  {item.emphasis_flag}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-right">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    if (participantAudioRef.current) {
                                      participantAudioRef.current.currentTime = item.participant_start
                                      participantAudioRef.current.play()
                                    }
                                  }}
                                  className="p-1 rounded bg-surface-700 hover:bg-primary-600 text-gray-300 hover:text-white transition-colors"
                                  title="Play word audio"
                                >
                                  <Play className="w-3 h-3 fill-current" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Tab 4: Contrastive Matrices */}
                {comparisonTab === 'prosody' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-4 rounded-xl bg-surface-800/60 border border-surface-700/60 space-y-3">
                      <div className="flex items-center gap-2 font-bold text-white">
                        <Activity className="w-4 h-4 text-violet-400" />
                        <span>Melodic & Intonation Contrast</span>
                      </div>
                      <p className="text-gray-400 text-[11px]">
                        Measures expressive dynamic pitch movements between participant speech and the synthetically synthesized Track A ideal delivery.
                      </p>
                      <div className="space-y-2 font-mono text-[11px]">
                        <div className="flex justify-between py-1 border-b border-surface-700/40">
                          <span className="text-gray-400 font-sans">Pitch Variation Index</span>
                          <span className="text-white font-bold">{comparisonResult.pitch.pitch_variation_ratio}× of baseline</span>
                        </div>
                        <div className="flex justify-between py-1 border-b border-surface-700/40">
                          <span className="text-gray-400 font-sans">Semitone Modulation Range</span>
                          <span className="text-white font-bold">{comparisonResult.pitch.delta_semitones > 0 ? `+${comparisonResult.pitch.delta_semitones}` : comparisonResult.pitch.delta_semitones} st</span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-gray-400 font-sans">Prosodic Classification</span>
                          <span className="badge bg-violet-950 text-violet-300 border-violet-800 text-[10px] uppercase font-bold">{comparisonResult.pitch.status}</span>
                        </div>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-surface-800/60 border border-surface-700/60 space-y-3">
                      <div className="flex items-center gap-2 font-bold text-white">
                        <Volume2 className="w-4 h-4 text-amber-400" />
                        <span>Dynamics & Vocal Energy Contrast</span>
                      </div>
                      <p className="text-gray-400 text-[11px]">
                        Analyzes vocal projection, breath control, and root-mean-square energy contrast across speech segments.
                      </p>
                      <div className="space-y-2 font-mono text-[11px]">
                        <div className="flex justify-between py-1 border-b border-surface-700/40">
                          <span className="text-gray-400 font-sans">Energy Ratio (RMS)</span>
                          <span className="text-white font-bold">{comparisonResult.energy.energy_ratio}× of baseline</span>
                        </div>
                        <div className="flex justify-between py-1 border-b border-surface-700/40">
                          <span className="text-gray-400 font-sans">Dynamic Range Delta</span>
                          <span className="text-white font-bold">{comparisonResult.energy.delta_dynamic_range_db > 0 ? `+${comparisonResult.energy.delta_dynamic_range_db}` : comparisonResult.energy.delta_dynamic_range_db} dB</span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-gray-400 font-sans">Projection Classification</span>
                          <span className="badge bg-amber-950 text-amber-300 border-amber-800 text-[10px] uppercase font-bold">{comparisonResult.energy.status}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Temporal Flaw Finding Studio (Phase 9) */}
            {flawsResult && (
              <div className="p-5 rounded-2xl bg-surface-900/80 border border-rose-800/50 space-y-5 animate-fade-in shadow-xl">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-rose-600/20 border border-rose-500/30 flex items-center justify-center text-rose-400">
                      <Target className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        Temporal Flaw Finding Studio (Phase 9)
                        <span className="badge bg-rose-900/60 text-rose-300 border border-rose-700 text-[10px]">Timestamped Grounding</span>
                      </h4>
                      <p className="text-xs text-gray-400">
                        Concrete delivery anomalies mathematically detected and grounded against Track A reference
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 font-mono text-xs">
                      {flawsResult.summary.high_severity_count > 0 && (
                        <span className="badge bg-rose-950/80 text-rose-400 border border-rose-700 font-bold">
                          {flawsResult.summary.high_severity_count} High
                        </span>
                      )}
                      {flawsResult.summary.medium_severity_count > 0 && (
                        <span className="badge bg-amber-950/80 text-amber-400 border border-amber-700 font-bold">
                          {flawsResult.summary.medium_severity_count} Medium
                        </span>
                      )}
                      {flawsResult.summary.low_severity_count > 0 && (
                        <span className="badge bg-blue-950/80 text-blue-400 border border-blue-700 font-bold">
                          {flawsResult.summary.low_severity_count} Low
                        </span>
                      )}
                    </div>
                    <span className="badge bg-surface-800 text-gray-300 border border-surface-600 text-xs px-2.5 py-1">
                      {flawsResult.summary.flaw_density_per_minute} flaws/min
                    </span>
                  </div>
                </div>

                {/* Primary Concern Callout Banner */}
                <div className="p-3.5 rounded-xl bg-surface-800/80 border border-rose-900/40 flex items-start gap-3">
                  <ShieldAlert className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <span className="font-semibold text-rose-300 block">Primary Delivery Bottleneck</span>
                    <span className="text-gray-300">{flawsResult.summary.primary_concern}</span>
                  </div>
                </div>

                {/* Filter Pills */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-surface-800 text-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="text-gray-400 text-[11px] mr-1">Filter Dimension:</span>
                    {['all', 'pace', 'pause', 'pitch', 'energy'].map((cat) => {
                      const count = cat === 'all'
                        ? flawsResult.summary.total_flaws
                        : (flawsResult.summary.flaws_by_category[cat] || 0)
                      return (
                        <button
                          key={cat}
                          onClick={() => setFlawsCategoryFilter(cat)}
                          className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${flawsCategoryFilter === cat ? 'bg-rose-600 text-white' : 'text-gray-400 hover:text-white bg-surface-800/80 border border-surface-700/60'}`}
                        >
                          {cat.charAt(0).toUpperCase() + cat.slice(1)} ({count})
                        </button>
                      )
                    })}
                  </div>
                  <span className="text-gray-500 font-mono text-[11px]">
                    Showing {flawsResult.flaws.filter(f => flawsCategoryFilter === 'all' || f.category === flawsCategoryFilter).length} of {flawsResult.summary.total_flaws}
                  </span>
                </div>

                {/* Chronological Flaw Timeline */}
                <div className="space-y-3">
                  {flawsResult.flaws.filter(f => flawsCategoryFilter === 'all' || f.category === flawsCategoryFilter).length === 0 ? (
                    <div className="p-8 text-center text-gray-400 bg-surface-800/40 rounded-xl border border-surface-700/60">
                      <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                      <p className="font-semibold text-white">No delivery flaws detected in this category!</p>
                      <p className="text-xs text-gray-500 mt-1">Speech in this dimension matches ideal delivery benchmarks closely.</p>
                    </div>
                  ) : (
                    flawsResult.flaws
                      .filter(f => flawsCategoryFilter === 'all' || f.category === flawsCategoryFilter)
                      .map((flaw) => {
                        const isSelected = selectedFlawId === flaw.id
                        const severityBorder = flaw.severity === 'high' ? 'border-rose-700/60' : flaw.severity === 'medium' ? 'border-amber-700/60' : 'border-blue-700/60'
                        const severityBg = flaw.severity === 'high' ? 'bg-rose-950/20' : flaw.severity === 'medium' ? 'bg-amber-950/20' : 'bg-blue-950/20'

                        return (
                          <div
                            key={flaw.id}
                            className={`p-4 rounded-xl border ${severityBorder} ${severityBg} hover:border-surface-400 transition-all space-y-2.5 ${isSelected ? 'ring-2 ring-rose-500/50' : ''}`}
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className={`badge uppercase text-[10px] font-bold px-2 py-0.5 ${flaw.severity === 'high' ? 'bg-rose-950 text-rose-300 border-rose-800' : flaw.severity === 'medium' ? 'bg-amber-950 text-amber-300 border-amber-800' : 'bg-blue-950 text-blue-300 border-blue-800'}`}>
                                  {flaw.severity}
                                </span>
                                <span className="badge bg-surface-800 text-gray-300 border-surface-600 text-[10px] uppercase font-semibold">
                                  {flaw.category}
                                </span>
                                <span className="font-mono text-xs font-bold text-white flex items-center gap-1">
                                  <Clock className="w-3 h-3 text-gray-400" />
                                  {flaw.start_time.toFixed(2)}s – {flaw.end_time.toFixed(2)}s
                                  <span className="text-gray-400 font-normal">({flaw.duration.toFixed(2)}s)</span>
                                </span>
                              </div>

                              <button
                                type="button"
                                onClick={() => handlePlayFlaw(flaw)}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-surface-800 hover:bg-rose-600 text-gray-200 hover:text-white transition-colors border border-surface-700/60 w-fit"
                                title="Play audio from flaw start timestamp"
                              >
                                <Play className="w-3 h-3 fill-current text-rose-400 group-hover:text-white" />
                                <span>Listen from {flaw.start_time.toFixed(2)}s</span>
                              </button>
                            </div>

                            {/* Affected text and explanation */}
                            <div className="text-xs space-y-1">
                              {flaw.affected_text && (
                                <p className="text-gray-300 font-medium">
                                  <strong className="text-gray-400 font-sans mr-1">Spoken Content:</strong>
                                  <span className="font-mono bg-surface-800/80 px-1.5 py-0.5 rounded text-rose-200">"{flaw.affected_text}"</span>
                                </p>
                              )}
                              <p className="text-gray-300 leading-relaxed">
                                {flaw.description}
                              </p>
                            </div>

                            {/* Quantitative Mathematical Evidence */}
                            {Object.keys(flaw.metric_evidence).length > 0 && (
                              <div className="p-2.5 rounded-lg bg-surface-900/60 border border-surface-700/60 text-[11px] font-mono flex flex-wrap items-center gap-x-4 gap-y-1 text-gray-400">
                                <span className="text-gray-500 font-sans font-semibold uppercase text-[10px]">Evidence:</span>
                                {Object.entries(flaw.metric_evidence).map(([key, val]) => (
                                  <span key={key} className="text-gray-300">
                                    <span className="text-gray-500">{key.replace(/_/g, ' ')}:</span> <strong className="text-white">{typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(2)) : String(val)}</strong>
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Actionable coaching suggestion */}
                            <div className="text-xs flex items-start gap-1.5 text-emerald-300 bg-emerald-950/30 p-2 rounded-lg border border-emerald-900/40">
                              <Lightbulb className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                              <span><strong className="text-emerald-400">Coaching Note: </strong>{flaw.suggestion}</span>
                            </div>
                          </div>
                        )
                      })
                  )}
                </div>
              </div>
            )}

            {/* Causal Explanations & Delivery Diagnosis Studio (Phase 10) */}
            {explanationsResult && (
              <div className="p-5 rounded-2xl bg-surface-900/80 border border-purple-800/50 space-y-5 animate-fade-in shadow-xl">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
                      <Compass className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        Causal Explanations & Delivery Diagnosis (Phase 10)
                        <span className="badge bg-purple-900/60 text-purple-300 border border-purple-700 text-[10px]">
                          {explanationsResult.is_gemini_generated ? 'Gemini 2.0 Flash Verified' : 'Deterministic Causal Engine'}
                        </span>
                      </h4>
                      <p className="text-xs text-gray-400">
                        Physiological root causes, perceptual listener impact, and prescriptive remedial drills
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="badge bg-purple-950 text-purple-300 border border-purple-700 text-xs px-2.5 py-1 font-semibold">
                      {explanationsResult.flaw_explanations.length} Causal Attributions
                    </span>
                  </div>
                </div>

                {/* Delivery Archetype Hero Card */}
                <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/40 via-surface-800/70 to-indigo-950/40 border border-purple-700/50 space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">Identified Archetype:</span>
                      <h3 className="text-base font-extrabold text-white">
                        {explanationsResult.diagnosis.archetype.name}
                      </h3>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {explanationsResult.diagnosis.archetype.key_traits.map((trait, idx) => (
                        <span key={idx} className="badge bg-surface-800/80 text-purple-200 border border-purple-800/60 text-[10px]">
                          {trait}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed">
                    {explanationsResult.diagnosis.archetype.summary}
                  </p>
                </div>

                {/* 3 Diagnostic Callout Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {/* Panel 1: Top Root Causes */}
                  <div className="p-3.5 rounded-xl bg-surface-800/70 border border-surface-700/60 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Physiological Root Causes</span>
                    </div>
                    <ul className="space-y-1.5 text-xs text-gray-300">
                      {explanationsResult.diagnosis.top_root_causes.map((rc, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-amber-400 font-bold text-xs">{idx + 1}.</span>
                          <span className="text-[11px] leading-snug">{rc}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Panel 2: Acoustic Strengths */}
                  <div className="p-3.5 rounded-xl bg-surface-800/70 border border-surface-700/60 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                      <ThumbsUp className="w-3.5 h-3.5" />
                      <span>Verified Acoustic Strengths</span>
                    </div>
                    <ul className="space-y-1.5 text-xs text-gray-300">
                      {explanationsResult.diagnosis.acoustic_strengths.map((str, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <Check className="w-3 h-3 text-emerald-400 flex-shrink-0 mt-0.5" />
                          <span className="text-[11px] leading-snug">{str}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Panel 3: Action Roadmap */}
                  <div className="p-3.5 rounded-xl bg-surface-800/70 border border-surface-700/60 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-sky-400">
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>Actionable Roadmap</span>
                    </div>
                    <ul className="space-y-1.5 text-xs text-gray-300">
                      {explanationsResult.diagnosis.action_roadmap.map((step, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-sky-400 font-bold text-xs">→</span>
                          <span className="text-[11px] leading-snug">{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Flaw-by-Flaw Causal Explanations Accordion/List */}
                {explanationsResult.flaw_explanations.length > 0 && (
                  <div className="space-y-3 pt-2 border-t border-surface-800">
                    <div className="text-xs font-bold text-gray-300 flex items-center justify-between">
                      <span>Causal Breakdowns per Grounded Speech Flaw</span>
                      <span className="text-gray-500 font-mono text-[11px]">
                        {explanationsResult.flaw_explanations.length} anomalies explained
                      </span>
                    </div>

                    <div className="space-y-2.5">
                      {explanationsResult.flaw_explanations.map((expl, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-xl bg-surface-800/50 border border-purple-900/30 hover:border-purple-700/50 transition-all space-y-2 text-xs"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                            <div className="flex items-center gap-2">
                              <span className="badge bg-purple-950 text-purple-300 border border-purple-800 text-[10px] uppercase font-bold">
                                {expl.flaw_type.replace(/_/g, ' ')}
                              </span>
                              <span className="font-mono text-gray-300 text-[11px] font-semibold">
                                {expl.start_time.toFixed(2)}s – {expl.end_time.toFixed(2)}s
                              </span>
                              {expl.affected_text && (
                                <span className="font-sans text-gray-400 text-[11px] truncate max-w-xs">
                                  "{expl.affected_text}"
                                </span>
                              )}
                            </div>

                            <button
                              type="button"
                              onClick={() => {
                                if (participantAudioRef.current) {
                                  participantAudioRef.current.currentTime = Math.max(0, expl.start_time - 0.15)
                                  participantAudioRef.current.play()
                                }
                              }}
                              className="text-[11px] text-purple-400 hover:text-purple-300 flex items-center gap-1 font-medium w-fit"
                            >
                              <Play className="w-3 h-3 fill-current" />
                              Seek ({expl.start_time.toFixed(1)}s)
                            </button>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 font-sans text-[11px]">
                            {/* Math & Physiological Driver */}
                            <div className="p-2.5 rounded-lg bg-surface-900/60 border border-surface-700/50 space-y-1">
                              <p className="text-gray-300">
                                <strong className="text-purple-400 font-semibold">Signal Evidence: </strong>
                                {expl.mathematical_cause}
                              </p>
                              <p className="text-gray-300">
                                <strong className="text-amber-400 font-semibold">Physiological Driver: </strong>
                                {expl.physiological_factor}
                              </p>
                            </div>

                            {/* Listener Impact & Remedial Drill */}
                            <div className="p-2.5 rounded-lg bg-surface-900/60 border border-surface-700/50 space-y-1">
                              <p className="text-gray-300">
                                <strong className="text-sky-400 font-semibold">Perceptual Impact: </strong>
                                {expl.perceptual_impact}
                              </p>
                              <p className="text-emerald-300">
                                <strong className="text-emerald-400 font-semibold">Remedial Drill: </strong>
                                {expl.remedial_drill}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Rubric Scoring & Composite Evaluation Studio (Phase 11) */}
            {scoringResult && (
              <div className="p-5 rounded-2xl bg-surface-900/80 border border-emerald-800/50 space-y-5 animate-fade-in shadow-xl">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                      <Award className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        Rubric Scoring & Composite Evaluation Studio (Phase 11)
                        <span className="badge bg-emerald-900/60 text-emerald-300 border border-emerald-700 text-[10px]">
                          Two-Track Calibrated
                        </span>
                      </h4>
                      <p className="text-xs text-gray-400">
                        Multi-tiered weighted synthesis across Track A (Delivery 'HOW') and Track B (Content 'WHAT')
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <span className="badge bg-emerald-950 text-emerald-300 border border-emerald-700 text-xs px-2.5 py-1 font-semibold">
                      {scoringResult.summary.tier_title}
                    </span>
                    <span className="badge bg-primary-950 text-primary-300 border border-primary-700 text-xs px-2.5 py-1 font-semibold">
                      Grade {scoringResult.summary.grade}
                    </span>
                    <span className="badge bg-surface-800 text-gray-300 border border-surface-600 text-xs px-2.5 py-1 font-semibold">
                      {scoringResult.summary.percentile_estimate}th Percentile
                    </span>
                  </div>
                </div>

                {/* Sub-Navigation Tabs */}
                <div className="border-b border-surface-700/80 flex gap-2 text-xs font-semibold">
                  <button
                    onClick={() => setScoringTab('composite')}
                    className={`py-2 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                      scoringTab === 'composite'
                        ? 'border-emerald-500 text-emerald-400 bg-emerald-950/20 rounded-t'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    <Award className="w-3.5 h-3.5" />
                    Composite Overview
                  </button>
                  <button
                    onClick={() => setScoringTab('dimensions')}
                    className={`py-2 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                      scoringTab === 'dimensions'
                        ? 'border-emerald-500 text-emerald-400 bg-emerald-950/20 rounded-t'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    <Activity className="w-3.5 h-3.5" />
                    8-Dimension Scorecard ({scoringResult.dimensions.length})
                  </button>
                  <button
                    onClick={() => setScoringTab('matrix')}
                    className={`py-2 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                      scoringTab === 'matrix'
                        ? 'border-emerald-500 text-emerald-400 bg-emerald-950/20 rounded-t'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    Mastery Rubric Levels
                  </button>
                </div>

                {/* Tab: Composite Overview */}
                {scoringTab === 'composite' && (
                  <div className="space-y-4">
                    {/* Hero Overall Score Banner */}
                    <div className="p-5 rounded-xl bg-gradient-to-r from-emerald-950/60 via-surface-800 to-primary-950/50 border border-emerald-700/50 flex flex-col md:flex-row items-center justify-between gap-6">
                      <div className="flex items-center gap-5">
                        <div className="relative flex items-center justify-center">
                          <div className="w-24 h-24 rounded-full border-4 border-emerald-500/80 bg-surface-900/90 flex flex-col items-center justify-center shadow-lg shadow-emerald-950/50">
                            <span className="text-2xl font-black text-white">{scoringResult.summary.overall_score}</span>
                            <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">/ 100</span>
                          </div>
                          <div className="absolute -top-1 -right-1 bg-primary-600 text-white text-[11px] font-black px-2 py-0.5 rounded-full border border-primary-400 shadow">
                            {scoringResult.summary.grade}
                          </div>
                        </div>

                        <div className="space-y-1 text-center md:text-left">
                          <div className="flex flex-wrap items-center gap-2 justify-center md:justify-start">
                            <h5 className="text-lg font-black text-white">{scoringResult.summary.tier_title}</h5>
                            <span className="badge bg-emerald-900/70 text-emerald-300 border border-emerald-600 text-[10px]">
                              {scoringResult.summary.tier} Tier
                            </span>
                          </div>
                          <p className="text-xs text-emerald-200/90 max-w-md">
                            {scoringResult.summary.summary_headline}
                          </p>
                          <div className="text-[11px] text-gray-400 pt-0.5">
                            Estimated Benchmark: <strong className="text-gray-200">Top {100 - scoringResult.summary.percentile_estimate}%</strong> of evaluated speakers ({scoringResult.summary.percentile_estimate}th percentile)
                          </div>
                        </div>
                      </div>

                      {/* Coaching Takeaway Box */}
                      <div className="w-full md:w-80 p-3.5 rounded-lg bg-surface-900/80 border border-surface-700/70 space-y-1.5">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
                          <Lightbulb className="w-3.5 h-3.5" />
                          <span>Primary Strategic Priority</span>
                        </div>
                        <p className="text-xs text-gray-300 leading-relaxed">
                          {scoringResult.summary.key_takeaway}
                        </p>
                      </div>
                    </div>

                    {/* Two-Track Contrast Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Track A: Delivery Card */}
                      <div className="p-4 rounded-xl bg-surface-800/80 border border-blue-900/50 space-y-3.5">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
                              <Activity className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <h6 className="text-xs font-bold text-white uppercase tracking-wider">Track A: Delivery (HOW)</h6>
                              <div className="text-[11px] text-gray-400">{Math.round(scoringResult.summary.delivery_weight * 100)}% Weight Contribution</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="text-xl font-black text-blue-400">{scoringResult.delivery.net_delivery_score}</span>
                            <span className="text-xs text-gray-500"> / 100</span>
                            <span className="ml-1.5 badge bg-blue-950 text-blue-300 border border-blue-700 text-[10px] font-bold">
                              Grade {scoringResult.delivery.grade}
                            </span>
                          </div>
                        </div>

                        {/* Baseline & Deduction tag */}
                        <div className="flex items-center justify-between text-xs p-2 rounded-lg bg-surface-900/60 border border-surface-700/50">
                          <span className="text-gray-400">
                            Acoustic Baseline: <strong className="text-gray-200">{scoringResult.delivery.raw_delivery_score}</strong>
                          </span>
                          {scoringResult.delivery.total_flaw_deduction > 0 ? (
                            <span className="text-rose-400 font-semibold flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" />
                              -{scoringResult.delivery.total_flaw_deduction} pts flaw penalty
                            </span>
                          ) : (
                            <span className="text-emerald-400 font-medium">0 flaw deductions</span>
                          )}
                        </div>

                        {/* Delivery Sub-Dimensions */}
                        <div className="space-y-2 pt-1 text-xs">
                          <div>
                            <div className="flex justify-between text-[11px] mb-0.5">
                              <span className="text-gray-400">Pace (20%)</span>
                              <span className="font-semibold text-gray-200">{scoringResult.delivery.pace_score}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${scoringResult.delivery.pace_score}%` }}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[11px] mb-0.5">
                              <span className="text-gray-400">Pitch Prosody & Intonation (25%)</span>
                              <span className="font-semibold text-gray-200">{scoringResult.delivery.pitch_score}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                              <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${scoringResult.delivery.pitch_score}%` }}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[11px] mb-0.5">
                              <span className="text-gray-400">Cadence & Pause Discipline (20%)</span>
                              <span className="font-semibold text-gray-200">{scoringResult.delivery.rhythm_score}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                              <div className="h-full bg-sky-500 rounded-full" style={{ width: `${scoringResult.delivery.rhythm_score}%` }}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[11px] mb-0.5">
                              <span className="text-gray-400">Dynamic Energy & Projection (20%)</span>
                              <span className="font-semibold text-gray-200">{scoringResult.delivery.energy_score}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                              <div className="h-full bg-amber-500 rounded-full" style={{ width: `${scoringResult.delivery.energy_score}%` }}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[11px] mb-0.5">
                              <span className="text-gray-400">Timbre & Articulation (15%)</span>
                              <span className="font-semibold text-gray-200">{scoringResult.delivery.timbre_score}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                              <div className="h-full bg-teal-500 rounded-full" style={{ width: `${scoringResult.delivery.timbre_score}%` }}></div>
                            </div>
                          </div>
                        </div>

                        {scoringResult.delivery.archetype && (
                          <div className="text-[11px] text-gray-400 pt-1 border-t border-surface-700/50 flex items-center justify-between">
                            <span>Vocal Archetype:</span>
                            <span className="font-bold text-purple-300">{scoringResult.delivery.archetype}</span>
                          </div>
                        )}
                      </div>

                      {/* Track B: Content Card */}
                      <div className="p-4 rounded-xl bg-surface-800/80 border border-purple-900/50 space-y-3.5">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-lg bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
                              <Brain className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <h6 className="text-xs font-bold text-white uppercase tracking-wider">Track B: Content (WHAT)</h6>
                              <div className="text-[11px] text-gray-400">{Math.round(scoringResult.summary.content_weight * 100)}% Weight Contribution</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="text-xl font-black text-purple-400">{scoringResult.content.net_content_score}</span>
                            <span className="text-xs text-gray-500"> / 100</span>
                            <span className="ml-1.5 badge bg-purple-950 text-purple-300 border border-purple-700 text-[10px] font-bold">
                              Grade {scoringResult.content.grade}
                            </span>
                          </div>
                        </div>

                        {/* Status tag */}
                        <div className="flex items-center justify-between text-xs p-2 rounded-lg bg-surface-900/60 border border-surface-700/50">
                          <span className="text-gray-400">
                            Assessment: <strong className="text-purple-300">{scoringResult.content.status}</strong>
                          </span>
                          <span className="text-gray-300 text-[11px]">
                            {scoringResult.content.strengths_count} strengths · {scoringResult.content.issues_count} deductions
                          </span>
                        </div>

                        {/* Content Sub-Dimensions */}
                        <div className="space-y-3 pt-2 text-xs">
                          <div>
                            <div className="flex justify-between text-[11px] mb-0.5">
                              <span className="text-gray-400">Grammar & Syntactic Precision (30%)</span>
                              <span className="font-semibold text-gray-200">{scoringResult.content.grammar_score}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                              <div className="h-full bg-purple-500 rounded-full" style={{ width: `${scoringResult.content.grammar_score}%` }}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[11px] mb-0.5">
                              <span className="text-gray-400">Semantic Clarity & Vocabulary (35%)</span>
                              <span className="font-semibold text-gray-200">{scoringResult.content.semantics_score}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                              <div className="h-full bg-violet-500 rounded-full" style={{ width: `${scoringResult.content.semantics_score}%` }}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[11px] mb-0.5">
                              <span className="text-gray-400">Structure & Rhetorical Impact (35%)</span>
                              <span className="font-semibold text-gray-200">{scoringResult.content.structure_score}</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                              <div className="h-full bg-fuchsia-500 rounded-full" style={{ width: `${scoringResult.content.structure_score}%` }}></div>
                            </div>
                          </div>
                        </div>

                        <div className="text-[11px] text-gray-400 pt-3 border-t border-surface-700/50">
                          Evaluated against Track B polished transcript without modifying Track A delivery baseline.
                        </div>
                      </div>
                    </div>

                    {/* Interactive Weight Allocation Bar */}
                    <div className="p-3.5 rounded-xl bg-surface-800/60 border border-surface-700/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-2">
                        <Scale className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        <div>
                          <span className="font-semibold text-gray-200">Rubric Calibration Presets:</span>
                          <span className="text-gray-400 ml-1.5">Adjust delivery vs content weight distribution</span>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5">
                        {[
                          { label: '50/50 Balanced', dw: 0.50, cw: 0.50 },
                          { label: '60/40 Delivery Focus', dw: 0.60, cw: 0.40 },
                          { label: '40/60 Content Focus', dw: 0.40, cw: 0.60 },
                          { label: '70/30 Orator Pitch', dw: 0.70, cw: 0.30 },
                        ].map((preset) => (
                          <button
                            key={preset.label}
                            onClick={() => {
                              setDeliveryWeight(preset.dw)
                              setContentWeight(preset.cw)
                              handleScore(preset.dw, preset.cw)
                            }}
                            disabled={isScoring}
                            className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
                              deliveryWeight === preset.dw && contentWeight === preset.cw
                                ? 'bg-emerald-600 text-white border-emerald-500'
                                : 'bg-surface-700 text-gray-300 border-surface-600 hover:bg-surface-600'
                            }`}
                          >
                            {preset.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab: 8-Dimension Scorecard */}
                {scoringTab === 'dimensions' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {scoringResult.dimensions.map((dim: ScoringDimensionItem) => (
                        <div
                          key={dim.name}
                          className="p-3.5 rounded-xl bg-surface-800/70 border border-surface-700/60 space-y-2.5"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="flex items-center gap-1.5">
                                <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                                  dim.track === 'delivery'
                                    ? 'bg-blue-950 text-blue-300 border border-blue-800'
                                    : 'bg-purple-950 text-purple-300 border border-purple-800'
                                }`}>
                                  {dim.track === 'delivery' ? 'Track A Delivery' : 'Track B Content'}
                                </span>
                                <span className="text-[11px] text-gray-400 font-mono">
                                  Weight: {Math.round(dim.weight_within_track * 100)}%
                                </span>
                              </div>
                              <h6 className="text-xs font-bold text-white mt-1">{dim.name}</h6>
                            </div>

                            <div className="text-right flex-shrink-0">
                              <span className="text-base font-black text-white">{dim.raw_score}</span>
                              <span className="text-[11px] text-gray-400"> / 100</span>
                              <div className="mt-0.5">
                                <span className="badge bg-surface-700 text-emerald-300 text-[10px] font-bold">
                                  Grade {dim.grade}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="w-full h-1.5 rounded-full bg-surface-700 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                dim.raw_score >= 80 ? 'bg-emerald-500' : dim.raw_score >= 65 ? 'bg-amber-500' : 'bg-rose-500'
                              }`}
                              style={{ width: `${dim.raw_score}%` }}
                            ></div>
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-gray-400 pt-0.5">
                            <span className="text-gray-300 italic">{dim.status}</span>
                            <span>{dim.feedback}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tab: Mastery Rubric Levels */}
                {scoringTab === 'matrix' && (
                  <div className="space-y-3">
                    <p className="text-xs text-gray-400">
                      Standard objective evaluation tiers used to benchmark speech delivery and linguistic content:
                    </p>
                    <div className="space-y-2.5">
                      {scoringResult.rubric_tiers.map((tier: RubricTierLevel) => {
                        const isCurrentTier = scoringResult.summary.tier.toLowerCase() === tier.tier_name.toLowerCase()
                        return (
                          <div
                            key={tier.tier_name}
                            className={`p-3.5 rounded-xl border transition-all ${
                              isCurrentTier
                                ? 'bg-emerald-950/40 border-emerald-500 shadow-md shadow-emerald-950/50'
                                : 'bg-surface-800/60 border-surface-700/50'
                            }`}
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-bold text-white">{tier.title}</span>
                                <span className="badge bg-surface-700 text-gray-300 text-[10px] font-mono">
                                  {tier.min_score} – {tier.max_score} pts
                                </span>
                              </div>
                              {isCurrentTier && (
                                <span className="badge bg-emerald-600 text-white text-[10px] font-bold flex items-center gap-1 w-fit">
                                  <Check className="w-3 h-3" />
                                  Your Current Tier
                                </span>
                              )}
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                              <div className="p-2 rounded bg-surface-900/60 border border-surface-700/40">
                                <span className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider block mb-0.5">
                                  Delivery Standard (HOW):
                                </span>
                                <p className="text-gray-300 text-[11px] leading-relaxed">{tier.delivery_standard}</p>
                              </div>
                              <div className="p-2 rounded bg-surface-900/60 border border-surface-700/40">
                                <span className="text-[11px] font-semibold text-purple-400 uppercase tracking-wider block mb-0.5">
                                  Content Standard (WHAT):
                                </span>
                                <p className="text-gray-300 text-[11px] leading-relaxed">{tier.content_standard}</p>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Single Audio Player before reference generation */}
            {!referenceResult && (
              <div className="p-4 rounded-xl bg-surface-700/40 border border-surface-600 flex items-center gap-4">
                <Volume2 className="w-5 h-5 text-primary-400 flex-shrink-0" />
                <audio
                  ref={participantAudioRef}
                  controls
                  src={apiService.getAnalysisAudioUrl(uploadResult.analysis_id)}
                  className="w-full h-9 accent-primary-500 rounded"
                />
              </div>
            )}

            {/* Content Evaluation Cards (Phase 4) */}
            {contentResult && (
              <div className="space-y-6 animate-fade-in">
                {/* Score Badges Bar */}
                <div className="grid grid-cols-3 gap-3">
                  <div className={`p-4 rounded-xl border flex flex-col items-center text-center ${getScoreColor(contentResult.grammar.score)}`}>
                    <span className="text-xs font-semibold uppercase tracking-wider opacity-90 mb-1">Grammar Score</span>
                    <span className="text-3xl font-black">{contentResult.grammar.score}</span>
                    <span className="text-[11px] opacity-75 mt-1">
                      {contentResult.grammar.errors.length} deduction(s)
                    </span>
                  </div>

                  <div className={`p-4 rounded-xl border flex flex-col items-center text-center ${getScoreColor(contentResult.semantics.score)}`}>
                    <span className="text-xs font-semibold uppercase tracking-wider opacity-90 mb-1">Semantics Score</span>
                    <span className="text-3xl font-black">{contentResult.semantics.score}</span>
                    <span className="text-[11px] opacity-75 mt-1">
                      {contentResult.semantics.issues.length} issue(s) identified
                    </span>
                  </div>

                  <div className={`p-4 rounded-xl border flex flex-col items-center text-center ${getScoreColor(contentResult.content.score)}`}>
                    <span className="text-xs font-semibold uppercase tracking-wider opacity-90 mb-1">Content Score</span>
                    <span className="text-3xl font-black">{contentResult.content.score}</span>
                    <span className="text-[11px] opacity-75 mt-1">
                      {contentResult.content.strengths.length} key strength(s)
                    </span>
                  </div>
                </div>

                {/* Tabs */}
                <div className="border-b border-surface-600 flex gap-2 overflow-x-auto text-xs font-semibold">
                  <button
                    onClick={() => setActiveTab('delivery')}
                    className={`py-2 px-3 border-b-2 transition-colors ${
                      activeTab === 'delivery'
                        ? 'border-primary-500 text-primary-400'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    Track A: Delivery Reference
                  </button>
                  <button
                    onClick={() => setActiveTab('improved')}
                    className={`py-2 px-3 border-b-2 transition-colors ${
                      activeTab === 'improved'
                        ? 'border-purple-500 text-purple-400'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    Track B: AI-Improved Version
                  </button>
                  <button
                    onClick={() => setActiveTab('grammar')}
                    className={`py-2 px-3 border-b-2 transition-colors ${
                      activeTab === 'grammar'
                        ? 'border-amber-500 text-amber-400'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    Grammar ({contentResult.grammar.errors.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('semantics')}
                    className={`py-2 px-3 border-b-2 transition-colors ${
                      activeTab === 'semantics'
                        ? 'border-accent-500 text-accent-400'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    Semantics ({contentResult.semantics.issues.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('content')}
                    className={`py-2 px-3 border-b-2 transition-colors ${
                      activeTab === 'content'
                        ? 'border-emerald-500 text-emerald-400'
                        : 'border-transparent text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    Recommendations ({contentResult.content.recommendations.length})
                  </button>
                </div>

                {/* Tab 1: Track A Delivery Reference */}
                {activeTab === 'delivery' && transcriptResult && (
                  <div className="p-4 rounded-xl bg-surface-900/60 border border-surface-600 space-y-3">
                    <div className="flex items-center justify-between text-xs text-gray-400">
                      <span className="font-semibold text-primary-400">Track A — Delivery Reference (Original Wording)</span>
                      <button
                        onClick={() => setShowRawTranscript(!showRawTranscript)}
                        className="text-primary-400 hover:underline"
                      >
                        {showRawTranscript ? 'Show Normalized' : 'Show Raw ASR'}
                      </button>
                    </div>
                    <p className="text-sm text-gray-200 leading-relaxed font-sans bg-surface-800 p-4 rounded border border-surface-600 select-text">
                      {showRawTranscript ? transcriptResult.raw_transcript : transcriptResult.delivery_transcript}
                    </p>
                  </div>
                )}

                {/* Tab 2: Track B AI-Improved Transcript */}
                {activeTab === 'improved' && (
                  <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-800/50 space-y-3">
                    <div className="flex items-center justify-between text-xs text-purple-300">
                      <span className="font-semibold flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" />
                        Track B — AI-Improved Content Transcript
                      </span>
                    </div>
                    <p className="text-sm text-gray-100 leading-relaxed font-sans bg-surface-800 p-4 rounded border border-purple-700/40 select-text">
                      {contentResult.corrected_transcript}
                    </p>
                  </div>
                )}

                {/* Tab 3: Grammar */}
                {activeTab === 'grammar' && (
                  <div className="space-y-3">
                    {contentResult.grammar.errors.length === 0 ? (
                      <div className="p-6 text-center text-gray-400 bg-surface-900/40 rounded-xl border border-surface-600">
                        <Check className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                        <p className="font-semibold text-white">No grammatical errors detected!</p>
                      </div>
                    ) : (
                      contentResult.grammar.errors.map((err, idx) => (
                        <div key={idx} className="p-3.5 rounded-xl bg-surface-900/60 border border-surface-600 space-y-1.5 text-xs">
                          <div className="flex items-center gap-2 text-red-400 font-medium">
                            <X className="w-3.5 h-3.5" />
                            <span>Original: </span>
                            <span className="line-through text-gray-400 font-mono">"{err.original}"</span>
                          </div>
                          <div className="flex items-center gap-2 text-emerald-400 font-medium">
                            <Check className="w-3.5 h-3.5" />
                            <span>Corrected: </span>
                            <span className="text-emerald-300 font-mono">"{err.corrected}"</span>
                          </div>
                          <p className="text-gray-400 pl-5 text-[11px]">{err.explanation}</p>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Tab 4: Semantics */}
                {activeTab === 'semantics' && (
                  <div className="space-y-3">
                    {contentResult.semantics.issues.length === 0 ? (
                      <div className="p-6 text-center text-gray-400 bg-surface-900/40 rounded-xl border border-surface-600">
                        <Check className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                        <p className="font-semibold text-white">High semantic clarity!</p>
                      </div>
                    ) : (
                      contentResult.semantics.issues.map((iss, idx) => (
                        <div key={idx} className="p-3.5 rounded-xl bg-surface-900/60 border border-surface-600 space-y-1.5 text-xs">
                          <div className="flex items-center gap-2 text-amber-400 font-semibold">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            <span>Excerpt: "{iss.text}"</span>
                          </div>
                          <p className="text-gray-300 pl-5"><strong className="text-gray-400">Issue: </strong>{iss.issue}</p>
                          <p className="text-emerald-300 pl-5"><strong className="text-gray-400">Suggestion: </strong>{iss.suggestion}</p>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Tab 5: Recommendations */}
                {activeTab === 'content' && (
                  <div className="space-y-4">
                    <div className="p-4 rounded-xl bg-primary-950/20 border border-primary-800/40">
                      <h5 className="text-xs font-bold text-primary-300 flex items-center gap-1.5 mb-2.5">
                        <Lightbulb className="w-3.5 h-3.5" />
                        Recommendations to Elevate Content
                      </h5>
                      <ul className="space-y-1.5 text-xs text-gray-300">
                        {contentResult.content.recommendations.map((rec, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-primary-400 font-bold">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Bottom Navigation */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-surface-600">
              <button
                onClick={handleReset}
                className="btn-secondary text-sm py-2.5 px-4 w-full sm:w-auto flex items-center justify-center gap-2"
              >
                <RotateCcw className="w-4 h-4" />
                Upload Different Recording
              </button>

              {scoringResult ? (
                <Link
                  to={`/results/${uploadResult?.analysis_id}`}
                  className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-900/30"
                >
                  <Award className="w-4 h-4" />
                  <span>Rubric Scoring Complete — View Full Dashboard (Phase 12)</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              ) : explanationsResult ? (
                <button
                  onClick={() => handleScore()}
                  disabled={isScoring}
                  className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-900/30"
                >
                  <Award className="w-4 h-4" />
                  <span>{isScoring ? 'Computing Rubric Scoring...' : 'Compute Rubric Scoring (Phase 11)'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : flawsResult ? (
                <button
                  onClick={handleExplain}
                  disabled={isExplaining}
                  className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-500 shadow-lg shadow-purple-900/30"
                >
                  <Compass className="w-4 h-4" />
                  <span>{isExplaining ? 'Synthesizing Causal Explanations...' : 'Generate Causal Explanations (Phase 10)'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : comparisonResult ? (
                <button
                  onClick={handleDetectFlaws}
                  disabled={isDetectingFlaws}
                  className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-500 shadow-lg shadow-rose-900/30"
                >
                  <Target className="w-4 h-4" />
                  <span>{isDetectingFlaws ? 'Scanning Temporal Delivery Flaws...' : 'Detect Temporal Flaws (Phase 9)'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : featuresResult ? (
                <button
                  onClick={handleCompare}
                  disabled={isComparing}
                  className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-900/30"
                >
                  <GitCompare className="w-4 h-4" />
                  <span>{isComparing ? 'Running DTW Acoustic Comparison...' : 'Run Acoustic Comparison (Phase 8)'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : alignmentResult ? (
                <button
                  onClick={handleExtractFeatures}
                  disabled={isExtractingFeatures}
                  className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto flex items-center justify-center gap-2 shadow-lg shadow-sky-900/30 bg-sky-600 hover:bg-sky-500"
                >
                  <Cpu className="w-4 h-4" />
                  <span>{isExtractingFeatures ? 'Extracting Acoustic Features...' : 'Extract Acoustic Features (Phase 7)'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : referenceResult ? (
                <button
                  onClick={handleAlign}
                  disabled={isAligning}
                  className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto flex items-center justify-center gap-2 shadow-lg shadow-primary-900/30"
                >
                  <GitCompare className="w-4 h-4" />
                  <span>{isAligning ? 'Aligning Speech Streams...' : 'Run Forced Alignment (Phase 6)'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : transcriptResult ? (
                <button
                  onClick={handleGenerateReference}
                  disabled={isGeneratingReference}
                  className="btn-primary text-sm py-2.5 px-6 w-full sm:w-auto flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-900/30"
                >
                  <Radio className="w-4 h-4" />
                  <span>Generate Ideal Delivery Reference</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
