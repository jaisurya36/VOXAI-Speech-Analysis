export interface HealthResponse {
  status: string
  application: string
  version: string
}

export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Analysis {
  id: string
  status: AnalysisStatus
  stage: string | null
  original_filename: string
  input_type: 'audio' | 'video'
  duration: number | null
  sample_rate: number | null
  raw_transcript?: string | null
  delivery_transcript?: string | null
  corrected_transcript?: string | null
  created_at?: string
  updated_at?: string
}

export interface MediaUploadResponse {
  analysis_id: string
  original_filename: string
  input_type: 'audio' | 'video'
  duration: number
  sample_rate: number
  status: string
  message: string
}

export interface WordTimestamp {
  word: string
  start: number
  end: number
  probability?: number
}

export interface SegmentTimestamp {
  id: number
  start: number
  end: number
  text: string
}

export interface TranscriptionResponse {
  analysis_id: string
  status: string
  language: string
  duration: number
  raw_transcript: string
  delivery_transcript: string
  segments: SegmentTimestamp[]
  words: WordTimestamp[]
}

export interface GrammarErrorItem {
  original: string
  corrected: string
  explanation: string
}

export interface GrammarEvaluation {
  score: number
  errors: GrammarErrorItem[]
}

export interface SemanticIssueItem {
  text: string
  issue: string
  suggestion: string
}

export interface SemanticEvaluation {
  score: number
  issues: SemanticIssueItem[]
}

export interface ContentEvaluation {
  score: number
  strengths: string[]
  weaknesses: string[]
  recommendations: string[]
}

export interface ContentEvaluationResponse {
  analysis_id: string
  corrected_transcript: string
  grammar: GrammarEvaluation
  semantics: SemanticEvaluation
  content: ContentEvaluation
  is_fallback: boolean
  status_message: string
}

export interface ReferenceGenerationResponse {
  analysis_id: string
  status: string
  reference_script: string
  duration: number
  model_name: string
  voice_name: string
  is_fallback: boolean
  has_improved_audio: boolean
  message: string
}

export interface AlignedWordItem {
  word: string
  participant_start: number
  participant_end: number
  reference_start: number
  reference_end: number
  confidence: number
}

export interface AlignedPhraseItem {
  phrase_id: number
  text: string
  participant_start: number
  participant_end: number
  reference_start: number
  reference_end: number
  word_count: number
}

export interface AlignmentResponse {
  analysis_id: string
  status: string
  alignment_coverage: number
  matched_word_count: number
  total_participant_words: number
  total_reference_words: number
  aligned_words: AlignedWordItem[]
  aligned_phrases: AlignedPhraseItem[]
  unmatched_participant_words: string[]
  unmatched_reference_words: string[]
  message: string
}

export interface PitchFeatures {
  mean_f0: number
  median_f0: number
  std_f0: number
  min_f0: number
  max_f0: number
  pitch_range_semitones: number
  voiced_fraction: number
  contour: number[]
}

export interface EnergyFeatures {
  mean_rms: number
  std_rms: number
  max_rms: number
  dynamic_range_db: number
  contour: number[]
}

export interface SpectralFeatures {
  mean_spectral_centroid: number
  mean_spectral_bandwidth: number
  mean_spectral_rolloff: number
  mean_zero_crossing_rate: number
}

export interface MFCCFeatures {
  mean_mfcc: number[]
  std_mfcc: number[]
}

export interface RhythmFeatures {
  total_duration: number
  speaking_duration: number
  pause_duration: number
  pause_count: number
  mean_pause_duration: number
  pause_to_speech_ratio: number
  words_per_minute: number
  articulation_rate: number
}

export interface WordAcousticFeature {
  word: string
  start: number
  end: number
  duration: number
  mean_f0?: number | null
  max_f0?: number | null
  mean_energy: number
}

export interface TrackFeatures {
  pitch: PitchFeatures
  energy: EnergyFeatures
  spectral: SpectralFeatures
  mfcc: MFCCFeatures
  rhythm: RhythmFeatures
  word_features: WordAcousticFeature[]
}

export interface FeaturesResponse {
  analysis_id: string
  status: string
  participant_features: TrackFeatures
  reference_features: TrackFeatures
  time_axis: number[]
  message: string
}

export interface DTWAlignmentPoint {
  participant_index: number
  reference_index: number
  normalized_participant_time: number
  normalized_reference_time: number
}

export interface DTWMetricResult {
  accumulated_cost: number
  normalized_distance: number
  path_length: number
  sample_path: DTWAlignmentPoint[]
}

export interface PaceComparison {
  participant_wpm: number
  reference_wpm: number
  delta_wpm: number
  wpm_ratio: number
  participant_speaking_duration: number
  reference_speaking_duration: number
  duration_ratio: number
  status: string
  similarity_score: number
}

export interface PauseComparison {
  participant_pause_count: number
  reference_pause_count: number
  delta_pause_count: number
  participant_pause_duration: number
  reference_pause_duration: number
  delta_pause_duration: number
  pause_duration_ratio: number
  participant_pause_to_speech_ratio: number
  reference_pause_to_speech_ratio: number
  delta_pause_to_speech: number
  status: string
  similarity_score: number
}

export interface PitchComparison {
  participant_mean_f0: number
  reference_mean_f0: number
  delta_mean_f0: number
  participant_std_f0: number
  reference_std_f0: number
  pitch_variation_ratio: number
  participant_range_semitones: number
  reference_range_semitones: number
  delta_semitones: number
  dtw: DTWMetricResult
  status: string
  similarity_score: number
}

export interface EnergyComparison {
  participant_mean_rms: number
  reference_mean_rms: number
  energy_ratio: number
  participant_dynamic_range_db: number
  reference_dynamic_range_db: number
  delta_dynamic_range_db: number
  dtw: DTWMetricResult
  status: string
  similarity_score: number
}

export interface TimbreComparison {
  mfcc_cosine_distance: number
  participant_spectral_centroid: number
  reference_spectral_centroid: number
  delta_spectral_centroid: number
  participant_articulation_rate: number
  reference_articulation_rate: number
  delta_articulation_rate: number
  status: string
  similarity_score: number
}

export interface WordComparisonItem {
  word: string
  participant_start: number
  participant_end: number
  participant_duration: number
  reference_start: number
  reference_end: number
  reference_duration: number
  duration_ratio: number
  duration_delta: number
  pitch_delta_hz?: number | null
  energy_ratio?: number | null
  tempo_flag: 'compressed' | 'stretched' | 'normal'
  emphasis_flag: 'accented' | 'reduced' | 'normal'
}

export interface ComparisonSummary {
  overall_similarity_score: number
  pace_score: number
  pitch_score: number
  rhythm_score: number
  energy_score: number
  timbre_score: number
  primary_delivery_flaws: string[]
}

export interface ComparisonResponse {
  analysis_id: string
  status: string
  summary: ComparisonSummary
  pace: PaceComparison
  pause: PauseComparison
  pitch: PitchComparison
  energy: EnergyComparison
  timbre: TimbreComparison
  aligned_words_comparison: WordComparisonItem[]
  message: string
}

export interface TemporalFlawItem {
  id: string
  flaw_type: string
  category: 'pace' | 'pause' | 'pitch' | 'energy' | 'articulation' | string
  severity: 'low' | 'medium' | 'high' | string
  start_time: number
  end_time: number
  duration: number
  description: string
  affected_text: string
  metric_evidence: Record<string, any>
  suggestion: string
}

export interface FlawsSummary {
  total_flaws: number
  high_severity_count: number
  medium_severity_count: number
  low_severity_count: number
  flaw_density_per_minute: number
  flaws_by_category: Record<string, number>
  primary_concern: string
}

export interface FlawsResponse {
  analysis_id: string
  status: string
  summary: FlawsSummary
  flaws: TemporalFlawItem[]
  message: string
}

export interface CausalFlawExplanation {
  flaw_id: string
  flaw_type: string
  start_time: number
  end_time: number
  affected_text: string
  mathematical_cause: string
  physiological_factor: string
  perceptual_impact: string
  remedial_drill: string
  confidence: number
}

export interface DeliveryArchetype {
  name: string
  summary: string
  key_traits: string[]
}

export interface CausalDiagnosis {
  archetype: DeliveryArchetype
  top_root_causes: string[]
  acoustic_strengths: string[]
  action_roadmap: string[]
}

export interface ExplanationsResponse {
  analysis_id: string
  status: string
  diagnosis: CausalDiagnosis
  flaw_explanations: CausalFlawExplanation[]
  is_gemini_generated: boolean
  message: string
}

export interface ScoringDimensionItem {
  name: string
  track: 'delivery' | 'content'
  raw_score: number
  weight_within_track: number
  overall_weight: number
  weighted_score: number
  grade: string
  status: string
  feedback: string
}

export interface FlawDeductionItem {
  severity: string
  count: number
  penalty_per_unit: number
  total_penalty: number
}

export interface DeliveryRubricBreakdown {
  pace_score: number
  pitch_score: number
  rhythm_score: number
  energy_score: number
  timbre_score: number
  raw_delivery_score: number
  flaw_penalties: FlawDeductionItem[]
  total_flaw_deduction: number
  net_delivery_score: number
  grade: string
  tier: string
  status: string
  archetype?: string | null
}

export interface ContentRubricBreakdown {
  grammar_score: number
  semantics_score: number
  structure_score: number
  net_content_score: number
  grade: string
  tier: string
  status: string
  strengths_count: number
  issues_count: number
}

export interface RubricTierLevel {
  tier_name: string
  title: string
  min_score: number
  max_score: number
  delivery_standard: string
  content_standard: string
}

export interface CompositeScoreSummary {
  overall_score: number
  grade: string
  tier: string
  tier_title: string
  delivery_weight: number
  content_weight: number
  weighted_delivery_score: number
  weighted_content_score: number
  percentile_estimate: number
  summary_headline: string
  key_takeaway: string
}

export interface ScoringResponse {
  analysis_id: string
  status: string
  summary: CompositeScoreSummary
  delivery: DeliveryRubricBreakdown
  content: ContentRubricBreakdown
  dimensions: ScoringDimensionItem[]
  rubric_tiers: RubricTierLevel[]
  message: string
}

export interface DashboardDataResponse {
  analysis_id: string
  status: string
  stage?: string | null
  original_filename: string
  input_type: string
  duration?: number | null
  sample_rate?: number | null
  created_at?: string | null
  raw_transcript?: string | null
  delivery_transcript?: string | null
  corrected_transcript?: string | null
  features?: FeaturesResponse | null
  comparison?: ComparisonResponse | null
  flaws?: FlawsResponse | null
  explanations?: ExplanationsResponse | null
  scores?: ScoringResponse | null
  has_audio: boolean
  has_reference_audio: boolean
  has_improved_audio: boolean
  message: string
}

export interface DemoSampleSummary {
  sample_id: string
  title: string
  archetype: string
  duration: number
  overall_score: number
  grade: string
  tier: string
  description: string
  transcript_preview: string
  key_flaws: string[]
  tags: string[]
}

export interface DemoListResponse {
  samples: DemoSampleSummary[]
  count: number
}

export interface DemoLoadResponse {
  sample_id: string
  analysis_id: string
  status: string
  title: string
  message: string
}

export interface PipelineStageInfo {
  stage_id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  description: string
  detail?: string | null
}

export interface PipelineProgressResponse {
  analysis_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  current_stage: string
  current_step: number
  total_steps: number
  progress_percent: number
  stages: PipelineStageInfo[]
  error_message?: string | null
}

export interface ProcessAllRequest {
  delivery_weight?: number
  content_weight?: number
}

export interface ProcessAllResponse {
  analysis_id: string
  status: 'completed' | 'failed'
  original_filename: string
  duration?: number | null
  total_words: number
  total_flaws: number
  overall_score?: number | null
  letter_grade?: string | null
  tier?: string | null
  tier_title?: string | null
  archetype?: string | null
  stages_completed: number
  total_stages: number
  results_url: string
  message: string
}



