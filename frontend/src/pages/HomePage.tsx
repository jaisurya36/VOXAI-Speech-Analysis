import { Link } from 'react-router-dom'
import { Mic2, Brain, BarChart3, Zap, ChevronRight, Sparkles } from 'lucide-react'
import DemoShowcaseSection from '../components/DemoShowcaseSection'

const features = [
  {
    icon: Mic2,
    title: 'HOW You Say It',
    description: 'Pitch, tone, pace, pauses, energy, fluency, cadence, emphasis — all measured against an AI-generated ideal reference.',
    color: 'text-blue-400',
    bg: 'bg-blue-950/50',
    border: 'border-blue-800/50',
  },
  {
    icon: Brain,
    title: 'WHAT You Say It',
    description: 'Grammar, semantics, relevance, logical flow, coherence, vocabulary — evaluated by Gemini AI with structured evidence.',
    color: 'text-purple-400',
    bg: 'bg-purple-950/50',
    border: 'border-purple-800/50',
  },
  {
    icon: BarChart3,
    title: 'Temporal Flaw Detection',
    description: 'Every flaw is timestamped and backed by mathematical evidence — pitch deviation, pace comparison, energy analysis.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-950/50',
    border: 'border-emerald-800/50',
  },
  {
    icon: Zap,
    title: 'Zero Manual Reference',
    description: 'No need to upload a reference speech. The AI automatically generates an ideal delivery baseline from your words.',
    color: 'text-amber-400',
    bg: 'bg-amber-950/50',
    border: 'border-amber-800/50',
  },
]

export default function HomePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      {/* Hero */}
      <div className="text-center mb-20">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-950 border border-primary-700 text-primary-400 text-sm font-medium mb-8">
          <span className="w-2 h-2 rounded-full bg-primary-400 animate-pulse"></span>
          AI-Powered Objective Speech Evaluation
        </div>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-white mb-6 leading-tight">
          Counterpointing
          <span className="block text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-accent-400">
            Speech Analytics
          </span>
        </h1>

        <p className="text-xl text-gray-400 max-w-3xl mx-auto mb-10 leading-relaxed">
          Upload your speech. The system automatically transcribes, generates an ideal delivery reference,
          compares acoustically, detects temporal flaws, evaluates content — and explains everything with
          mathematical precision.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/analyze" className="btn-primary flex items-center gap-2 justify-center text-lg py-3.5 px-8">
            <Mic2 className="w-5 h-5" />
            Upload Speech
            <ChevronRight className="w-5 h-5" />
          </Link>
        </div>
      </div>

      {/* Contrastive Demo Dataset Showcase */}
      <div className="mb-20">
        <DemoShowcaseSection />
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-20">
        {features.map((feature) => (
          <div key={feature.title} className={`card border ${feature.border} ${feature.bg} hover:scale-[1.02] transition-transform duration-200`}>
            <div className="w-10 h-10 rounded-lg bg-surface-700 flex items-center justify-center mb-4">
              <feature.icon className={`w-5 h-5 ${feature.color}`} />
            </div>
            <h3 className="font-bold text-white mb-2">{feature.title}</h3>
            <p className="text-sm text-gray-400 leading-relaxed">{feature.description}</p>
          </div>
        ))}
      </div>

      {/* Architecture */}
      <div className="card">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">How It Works</h2>
        <div className="flex flex-wrap items-center justify-center gap-3 text-sm">
          {[
            'Audio / Video Upload',
            'Audio Extraction',
            'Faster-Whisper Transcription',
            'Gemini Content Evaluation',
            'AI Reference Generation',
            'Forced Alignment',
            'Acoustic Feature Extraction',
            'DTW Comparison',
            'Temporal Flaw Detection',
            'Rubric Scoring',
            'Interactive Dashboard',
          ].map((step, i) => (
            <div key={step} className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-primary-700 text-primary-200 text-xs flex items-center justify-center font-bold">{i + 1}</span>
                <span className="text-gray-300">{step}</span>
              </div>
              {i < 10 && <ChevronRight className="w-4 h-4 text-gray-600" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
