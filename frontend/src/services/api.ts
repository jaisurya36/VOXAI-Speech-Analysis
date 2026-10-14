import axios, { AxiosProgressEvent } from 'axios'
import {
  HealthResponse,
  MediaUploadResponse,
  Analysis,
  TranscriptionResponse,
  ContentEvaluationResponse,
  ReferenceGenerationResponse,
  AlignmentResponse,
  FeaturesResponse,
  ComparisonResponse,
  FlawsResponse,
  ExplanationsResponse,
  ScoringResponse,
  DashboardDataResponse,
  DemoListResponse,
  DemoLoadResponse,
  PipelineProgressResponse,
  ProcessAllRequest,
  ProcessAllResponse,
} from '../types'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const httpClient = axios.create({
  baseURL: BASE_URL,
  timeout: 300000, // 5 minutes for long operations
})

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Unknown server error'
    return Promise.reject(new Error(message))
  }
)

export const apiService = {
  async health(): Promise<HealthResponse> {
    const response = await httpClient.get<HealthResponse>('/api/health')
    return response.data
  },

  async uploadMedia(
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<MediaUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await httpClient.post<MediaUploadResponse>('/api/media/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (progressEvent.total && onProgress) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentCompleted)
        }
      },
    })
    return response.data
  },

  async getMediaStatus(analysisId: string): Promise<Analysis> {
    const response = await httpClient.get<Analysis>(`/api/media/${analysisId}/status`)
    return response.data
  },

  getAnalysisAudioUrl(analysisId: string): string {
    return `${BASE_URL}/api/media/${analysisId}/audio`
  },

  getOriginalMediaUrl(analysisId: string): string {
    return `${BASE_URL}/api/media/${analysisId}/original`
  },

  async transcribe(analysisId: string): Promise<TranscriptionResponse> {
    const response = await httpClient.post<TranscriptionResponse>(`/api/analysis/${analysisId}/transcribe`)
    return response.data
  },

  async getTranscript(analysisId: string): Promise<TranscriptionResponse> {
    const response = await httpClient.get<TranscriptionResponse>(`/api/analysis/${analysisId}/transcript`)
    return response.data
  },

  async evaluateContent(analysisId: string): Promise<ContentEvaluationResponse> {
    const response = await httpClient.post<ContentEvaluationResponse>(`/api/analysis/${analysisId}/evaluate-content`)
    return response.data
  },

  async getContentEvaluation(analysisId: string): Promise<ContentEvaluationResponse> {
    const response = await httpClient.get<ContentEvaluationResponse>(`/api/analysis/${analysisId}/content-evaluation`)
    return response.data
  },

  async generateReference(analysisId: string): Promise<ReferenceGenerationResponse> {
    const response = await httpClient.post<ReferenceGenerationResponse>(`/api/analysis/${analysisId}/generate-reference`)
    return response.data
  },

  getReferenceAudioUrl(analysisId: string): string {
    return `${BASE_URL}/api/analysis/${analysisId}/reference-audio`
  },

  getImprovedAudioUrl(analysisId: string): string {
    return `${BASE_URL}/api/analysis/${analysisId}/improved-audio`
  },

  async align(analysisId: string): Promise<AlignmentResponse> {
    const response = await httpClient.post<AlignmentResponse>(`/api/analysis/${analysisId}/align`)
    return response.data
  },

  async getAlignment(analysisId: string): Promise<AlignmentResponse> {
    const response = await httpClient.get<AlignmentResponse>(`/api/analysis/${analysisId}/alignment`)
    return response.data
  },

  async extractFeatures(analysisId: string): Promise<FeaturesResponse> {
    const response = await httpClient.post<FeaturesResponse>(`/api/analysis/${analysisId}/extract-features`)
    return response.data
  },

  async getFeatures(analysisId: string): Promise<FeaturesResponse> {
    const response = await httpClient.get<FeaturesResponse>(`/api/analysis/${analysisId}/features`)
    return response.data
  },

  async compare(analysisId: string): Promise<ComparisonResponse> {
    const response = await httpClient.post<ComparisonResponse>(`/api/analysis/${analysisId}/compare`)
    return response.data
  },

  async getComparison(analysisId: string): Promise<ComparisonResponse> {
    const response = await httpClient.get<ComparisonResponse>(`/api/analysis/${analysisId}/comparison`)
    return response.data
  },

  async detectFlaws(analysisId: string): Promise<FlawsResponse> {
    const response = await httpClient.post<FlawsResponse>(`/api/analysis/${analysisId}/detect-flaws`)
    return response.data
  },

  async getFlaws(analysisId: string): Promise<FlawsResponse> {
    const response = await httpClient.get<FlawsResponse>(`/api/analysis/${analysisId}/flaws`)
    return response.data
  },

  async explain(analysisId: string): Promise<ExplanationsResponse> {
    const response = await httpClient.post<ExplanationsResponse>(`/api/analysis/${analysisId}/explain`)
    return response.data
  },

  async getExplanations(analysisId: string): Promise<ExplanationsResponse> {
    const response = await httpClient.get<ExplanationsResponse>(`/api/analysis/${analysisId}/explanations`)
    return response.data
  },

  async score(
    analysisId: string,
    deliveryWeight: number = 0.50,
    contentWeight: number = 0.50
  ): Promise<ScoringResponse> {
    const response = await httpClient.post<ScoringResponse>(
      `/api/analysis/${analysisId}/score?delivery_weight=${deliveryWeight}&content_weight=${contentWeight}`
    )
    return response.data
  },

  async getScore(analysisId: string): Promise<ScoringResponse> {
    const response = await httpClient.get<ScoringResponse>(`/api/analysis/${analysisId}/score`)
    return response.data
  },

  async getDashboardData(analysisId: string, autoComplete: boolean = true): Promise<DashboardDataResponse> {
    const response = await httpClient.get<DashboardDataResponse>(
      `/api/analysis/${analysisId}/dashboard?auto_complete=${autoComplete}`
    )
    return response.data
  },

  async getDemoSamples(): Promise<DemoListResponse> {
    const response = await httpClient.get<DemoListResponse>('/api/demo/samples')
    return response.data
  },

  async loadDemoSample(sampleId: string): Promise<DemoLoadResponse> {
    const response = await httpClient.post<DemoLoadResponse>(`/api/demo/load/${sampleId}`)
    return response.data
  },

  async processAll(analysisId: string, req?: ProcessAllRequest): Promise<ProcessAllResponse> {
    const response = await httpClient.post<ProcessAllResponse>(
      `/api/analysis/${analysisId}/process-all`,
      req || { delivery_weight: 0.50, content_weight: 0.50 }
    )
    return response.data
  },

  async uploadAndProcess(
    file: File,
    deliveryWeight: number = 0.50,
    contentWeight: number = 0.50,
    onProgress?: (percent: number) => void
  ): Promise<ProcessAllResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('delivery_weight', deliveryWeight.toString())
    formData.append('content_weight', contentWeight.toString())

    const response = await httpClient.post<ProcessAllResponse>('/api/analysis/upload-and-process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      },
    })
    return response.data
  },

  async getPipelineProgress(analysisId: string): Promise<PipelineProgressResponse> {
    const response = await httpClient.get<PipelineProgressResponse>(`/api/analysis/${analysisId}/progress`)
    return response.data
  },
}

export default apiService


