import axios from 'axios';
import type {
  FullConfig,
  ApiConfig,
  MusicConfig,
  FFmpegConfig,
  MusicTrack,
  Job,
  JobResult,
  TextAnalysis,
  ApiTestResult,
  CreditsResponse,
  Voice,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Config API
export const configApi = {
  get: async (): Promise<FullConfig> => {
    const { data } = await api.get('/api/config');
    return data;
  },

  update: async (config: FullConfig): Promise<FullConfig> => {
    const { data } = await api.put('/api/config', config);
    return data;
  },

  updateApi: async (apiConfig: ApiConfig): Promise<ApiConfig> => {
    const { data } = await api.patch('/api/config/api', apiConfig);
    return data;
  },

  updateMusic: async (musicConfig: MusicConfig): Promise<MusicConfig> => {
    const { data } = await api.patch('/api/config/music', musicConfig);
    return data;
  },

  updateFFmpeg: async (ffmpegConfig: FFmpegConfig): Promise<FFmpegConfig> => {
    const { data } = await api.patch('/api/config/ffmpeg', ffmpegConfig);
    return data;
  },

  testApi: async (apiName: string): Promise<ApiTestResult> => {
    const { data } = await api.post('/api/config/test-api', { api: apiName });
    return data;
  },

  getCredits: async (): Promise<CreditsResponse> => {
    const { data } = await api.get('/api/config/credits');
    return data;
  },

  getVoices: async (): Promise<Voice[]> => {
    const { data } = await api.get('/api/config/voices');
    return data.voices;
  },
};

// Music API
export const musicApi = {
  list: async (params?: {
    mood?: string;
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<{ tracks: MusicTrack[]; total: number }> => {
    const { data } = await api.get('/api/music', { params });
    return data;
  },

  get: async (trackId: string): Promise<MusicTrack> => {
    const { data } = await api.get(`/api/music/${trackId}`);
    return data;
  },

  upload: async (
    file: File,
    mood: string,
    tags: string[] = []
  ): Promise<MusicTrack> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mood', mood);
    formData.append('tags', tags.join(','));

    const { data } = await api.post('/api/music/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  update: async (
    trackId: string,
    updates: Partial<MusicTrack>
  ): Promise<MusicTrack> => {
    const { data } = await api.put(`/api/music/${trackId}`, updates);
    return data;
  },

  delete: async (trackId: string): Promise<void> => {
    await api.delete(`/api/music/${trackId}`);
  },

  getWaveform: async (trackId: string): Promise<number[]> => {
    const { data } = await api.get(`/api/music/${trackId}/waveform`);
    return data.waveform;
  },

  getPreviewUrl: (trackId: string): string => {
    return `${API_BASE}/api/music/${trackId}/preview`;
  },

  getStats: async (): Promise<{
    totalTracks: number;
    totalDurationMs: number;
    tracksByMood: Record<string, number>;
    totalSizeBytes: number;
  }> => {
    const { data } = await api.get('/api/music/stats');
    return data;
  },
};

// Video API
export const videoApi = {
  analyzeText: async (text: string): Promise<TextAnalysis> => {
    const { data } = await api.post('/api/video/analyze-text', { text });
    return data;
  },

  generate: async (
    text: string,
    configOverride?: Record<string, unknown>
  ): Promise<{ jobId: string; status: string; message: string }> => {
    const { data } = await api.post('/api/video/generate', {
      text,
      config_override: configOverride,
    });
    return data;
  },
};

// Jobs API
export const jobsApi = {
  list: async (params?: {
    status?: string;
    limit?: number;
  }): Promise<{ jobs: Job[]; total: number }> => {
    const { data } = await api.get('/api/jobs', { params });
    return data;
  },

  getStatus: async (jobId: string): Promise<Job> => {
    const { data } = await api.get(`/api/jobs/${jobId}/status`);
    return data;
  },

  getResult: async (jobId: string): Promise<JobResult> => {
    const { data } = await api.get(`/api/jobs/${jobId}/result`);
    return data;
  },

  getDownloadUrl: (jobId: string): string => {
    return `${API_BASE}/api/jobs/${jobId}/download`;
  },

  cancel: async (jobId: string): Promise<void> => {
    await api.post(`/api/jobs/${jobId}/cancel`);
  },

  delete: async (jobId: string): Promise<void> => {
    await api.delete(`/api/jobs/${jobId}`);
  },
};

export default api;
