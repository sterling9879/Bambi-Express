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
  MinimaxVoice,
  CustomVoice,
  CustomVoiceCreate,
  Channel,
  ChannelCreate,
  VideoHistory,
  VideoHistoryList,
  Element,
  ElementList,
  ElementType,
  HistoryStats,
  Batch,
  BatchListItem,
  BatchAnalysis,
  BatchCreateItem,
  BatchDownloadItem,
  VideoEffect,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// Convert snake_case to camelCase
function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

// Convert camelCase to snake_case
function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

// Deep transform object keys
function transformKeys(obj: unknown, transformer: (key: string) => string): unknown {
  if (Array.isArray(obj)) {
    return obj.map((item) => transformKeys(item, transformer));
  }
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([key, value]) => [
        transformer(key),
        transformKeys(value, transformer),
      ])
    );
  }
  return obj;
}

const toCamelCase = <T>(data: unknown): T => transformKeys(data, snakeToCamel) as T;
const toSnakeCase = <T>(data: unknown): T => transformKeys(data, camelToSnake) as T;

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutos timeout (backend pode estar ocupado gerando)
});

// Interceptor para tratar erros de forma consistente
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Timeout - não é erro crítico durante geração
    if (error.code === 'ECONNABORTED') {
      const customError = new Error('Servidor ocupado processando. A geração continua em segundo plano.');
      return Promise.reject(customError);
    }

    // Sem conexão
    if (!error.response) {
      const customError = new Error('Erro de conexão com o servidor. Verifique se o backend está rodando.');
      return Promise.reject(customError);
    }

    // Erro HTTP
    const status = error.response.status;
    const data = error.response.data;

    let message = data?.detail || data?.message || data?.error || `Erro ${status}`;

    // Mensagens amigáveis por código
    if (status === 500) {
      message = `Erro interno do servidor: ${message}`;
    } else if (status === 503) {
      message = 'Servidor temporariamente indisponível. Aguarde e tente novamente.';
    } else if (status === 504) {
      message = 'Timeout do servidor. A operação demorou muito.';
    }

    const customError = new Error(message);
    return Promise.reject(customError);
  }
);

// Config API
export const configApi = {
  get: async (): Promise<FullConfig> => {
    const { data } = await api.get('/api/config');
    return toCamelCase<FullConfig>(data);
  },

  update: async (config: FullConfig): Promise<FullConfig> => {
    const { data } = await api.put('/api/config', toSnakeCase(config));
    return toCamelCase<FullConfig>(data);
  },

  updateApi: async (apiConfig: ApiConfig): Promise<ApiConfig> => {
    const { data } = await api.patch('/api/config/api', toSnakeCase(apiConfig));
    return toCamelCase<ApiConfig>(data);
  },

  updateMusic: async (musicConfig: MusicConfig): Promise<MusicConfig> => {
    const { data } = await api.patch('/api/config/music', toSnakeCase(musicConfig));
    return toCamelCase<MusicConfig>(data);
  },

  updateFFmpeg: async (ffmpegConfig: FFmpegConfig): Promise<FFmpegConfig> => {
    const { data } = await api.patch('/api/config/ffmpeg', toSnakeCase(ffmpegConfig));
    return toCamelCase<FFmpegConfig>(data);
  },

  testApi: async (apiName: string): Promise<ApiTestResult> => {
    const { data } = await api.post('/api/config/test-api', { api: apiName });
    return toCamelCase<ApiTestResult>(data);
  },

  getCredits: async (): Promise<CreditsResponse> => {
    const { data } = await api.get('/api/config/credits');
    return toCamelCase<CreditsResponse>(data);
  },

  getVoices: async (): Promise<Voice[]> => {
    const { data } = await api.get('/api/config/voices');
    return toCamelCase<Voice[]>(data.voices);
  },

  getMinimaxVoices: async (): Promise<MinimaxVoice[]> => {
    const { data } = await api.get('/api/config/minimax-voices');
    return data.voices as MinimaxVoice[];
  },

  getMinimaxEmotions: async (): Promise<string[]> => {
    const { data } = await api.get('/api/config/minimax-emotions');
    return data.emotions as string[];
  },

  getCustomVoices: async (): Promise<{
    customVoices: CustomVoice[];
    defaultVoices: MinimaxVoice[];
  }> => {
    const { data } = await api.get('/api/config/custom-voices');
    return toCamelCase(data);
  },

  createCustomVoice: async (voice: CustomVoiceCreate): Promise<CustomVoice> => {
    const { data } = await api.post('/api/config/custom-voices', toSnakeCase(voice));
    return toCamelCase<CustomVoice>(data);
  },

  updateCustomVoice: async (voiceId: string, updates: Partial<CustomVoiceCreate>): Promise<CustomVoice> => {
    const { data } = await api.put(`/api/config/custom-voices/${voiceId}`, toSnakeCase(updates));
    return toCamelCase<CustomVoice>(data);
  },

  deleteCustomVoice: async (voiceId: string): Promise<void> => {
    await api.delete(`/api/config/custom-voices/${voiceId}`);
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
    return toCamelCase<{ tracks: MusicTrack[]; total: number }>(data);
  },

  get: async (trackId: string): Promise<MusicTrack> => {
    const { data } = await api.get(`/api/music/${trackId}`);
    return toCamelCase<MusicTrack>(data);
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
    return toCamelCase<MusicTrack>(data);
  },

  update: async (
    trackId: string,
    updates: Partial<MusicTrack>
  ): Promise<MusicTrack> => {
    const { data } = await api.put(`/api/music/${trackId}`, toSnakeCase(updates));
    return toCamelCase<MusicTrack>(data);
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
    return toCamelCase(data);
  },
};

// Video API
export const videoApi = {
  analyzeText: async (text: string): Promise<TextAnalysis> => {
    const { data } = await api.post('/api/video/analyze-text', { text });
    return toCamelCase<TextAnalysis>(data);
  },

  generate: async (
    text: string,
    title?: string,
    channelId?: string,
    configOverride?: Record<string, unknown>
  ): Promise<{ jobId: string; status: string; message: string }> => {
    const { data } = await api.post('/api/video/generate', {
      text,
      title,
      channel_id: channelId,
      config_override: configOverride ? toSnakeCase(configOverride) : undefined,
    });
    return toCamelCase(data);
  },
};

// Jobs API
export const jobsApi = {
  list: async (params?: {
    status?: string;
    limit?: number;
  }): Promise<{ jobs: Job[]; total: number }> => {
    const { data } = await api.get('/api/jobs', { params });
    return toCamelCase<{ jobs: Job[]; total: number }>(data);
  },

  getStatus: async (jobId: string): Promise<Job> => {
    const { data } = await api.get(`/api/jobs/${jobId}/status`);
    return toCamelCase<Job>(data);
  },

  getResult: async (jobId: string): Promise<JobResult> => {
    const { data } = await api.get(`/api/jobs/${jobId}/result`);
    return toCamelCase<JobResult>(data);
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

// Channels API
export const channelsApi = {
  list: async (): Promise<Channel[]> => {
    const { data } = await api.get('/api/history/channels');
    return toCamelCase<Channel[]>(data);
  },

  get: async (channelId: string): Promise<Channel> => {
    const { data } = await api.get(`/api/history/channels/${channelId}`);
    return toCamelCase<Channel>(data);
  },

  create: async (channel: ChannelCreate): Promise<Channel> => {
    const { data } = await api.post('/api/history/channels', toSnakeCase(channel));
    return toCamelCase<Channel>(data);
  },

  update: async (channelId: string, updates: Partial<ChannelCreate>): Promise<Channel> => {
    const { data } = await api.put(`/api/history/channels/${channelId}`, toSnakeCase(updates));
    return toCamelCase<Channel>(data);
  },

  delete: async (channelId: string): Promise<void> => {
    await api.delete(`/api/history/channels/${channelId}`);
  },
};

// History API
export const historyApi = {
  listVideos: async (params?: {
    channelId?: string;
    limit?: number;
    offset?: number;
  }): Promise<VideoHistoryList> => {
    const { data } = await api.get('/api/history/videos', { params: toSnakeCase(params) });
    return toCamelCase<VideoHistoryList>(data);
  },

  getVideo: async (videoId: string): Promise<VideoHistory> => {
    const { data } = await api.get(`/api/history/videos/${videoId}`);
    return toCamelCase<VideoHistory>(data);
  },

  deleteVideo: async (videoId: string): Promise<void> => {
    await api.delete(`/api/history/videos/${videoId}`);
  },

  listElements: async (params?: {
    jobId?: string;
    elementType?: ElementType;
    limit?: number;
    offset?: number;
  }): Promise<ElementList> => {
    const { data } = await api.get('/api/history/elements', { params: toSnakeCase(params) });
    return toCamelCase<ElementList>(data);
  },

  getElement: async (elementId: string): Promise<Element> => {
    const { data } = await api.get(`/api/history/elements/${elementId}`);
    return toCamelCase<Element>(data);
  },

  deleteElement: async (elementId: string): Promise<void> => {
    await api.delete(`/api/history/elements/${elementId}`);
  },

  getStats: async (): Promise<HistoryStats> => {
    const { data } = await api.get('/api/history/stats');
    return toCamelCase<HistoryStats>(data);
  },

  getVideoDownloadUrl: (videoId: string): string => {
    return `${API_BASE}/api/history/videos/${videoId}/download`;
  },

  getElementUrl: (elementId: string): string => {
    return `${API_BASE}/api/history/elements/${elementId}/file`;
  },
};

// Batch API
export const batchApi = {
  analyze: async (
    name: string,
    items: BatchCreateItem[],
    configOverride?: Record<string, unknown>
  ): Promise<BatchAnalysis> => {
    const { data } = await api.post('/api/batch/analyze', {
      name,
      items: items.map((item) => toSnakeCase(item)),
      config_override: configOverride ? toSnakeCase(configOverride) : undefined,
    });
    return toCamelCase<BatchAnalysis>(data);
  },

  create: async (
    name: string,
    items: BatchCreateItem[],
    channelId?: string,
    configOverride?: Record<string, unknown>
  ): Promise<{ batchId: string; status: string; message: string; totalItems: number }> => {
    const { data } = await api.post('/api/batch', {
      name,
      items: items.map((item) => toSnakeCase(item)),
      channel_id: channelId,
      config_override: configOverride ? toSnakeCase(configOverride) : undefined,
    });
    return toCamelCase(data);
  },

  list: async (params?: {
    status?: string;
    limit?: number;
  }): Promise<{ batches: BatchListItem[]; total: number }> => {
    const { data } = await api.get('/api/batch', { params });
    return toCamelCase<{ batches: BatchListItem[]; total: number }>(data);
  },

  getStatus: async (batchId: string): Promise<Batch> => {
    const { data } = await api.get(`/api/batch/${batchId}`);
    return toCamelCase<Batch>(data);
  },

  pause: async (batchId: string): Promise<void> => {
    await api.post(`/api/batch/${batchId}/pause`);
  },

  resume: async (batchId: string): Promise<void> => {
    await api.post(`/api/batch/${batchId}/resume`);
  },

  cancel: async (batchId: string): Promise<void> => {
    await api.post(`/api/batch/${batchId}/cancel`);
  },

  delete: async (batchId: string): Promise<void> => {
    await api.delete(`/api/batch/${batchId}`);
  },

  getItemDownloadUrl: (batchId: string, itemIndex: number): string => {
    return `${API_BASE}/api/batch/${batchId}/items/${itemIndex}/download`;
  },

  listDownloads: async (batchId: string): Promise<{
    batchId: string;
    totalAvailable: number;
    downloads: BatchDownloadItem[];
  }> => {
    const { data } = await api.get(`/api/batch/${batchId}/download-all`);
    return toCamelCase(data);
  },
};

// Effects API
export const effectsApi = {
  list: async (category?: string): Promise<VideoEffect[]> => {
    const { data } = await api.get('/api/effects', { params: { category } });
    return toCamelCase<VideoEffect[]>(data);
  },

  getCategories: async (): Promise<string[]> => {
    const { data } = await api.get('/api/effects/categories');
    return data;
  },

  get: async (effectId: string): Promise<VideoEffect> => {
    const { data } = await api.get(`/api/effects/${effectId}`);
    return toCamelCase<VideoEffect>(data);
  },

  upload: async (
    file: File,
    name: string,
    description?: string,
    category?: string
  ): Promise<VideoEffect> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    if (description) formData.append('description', description);
    if (category) formData.append('category', category);

    const { data } = await api.post('/api/effects', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return toCamelCase<VideoEffect>(data);
  },

  update: async (
    effectId: string,
    updates: { name?: string; description?: string; category?: string }
  ): Promise<VideoEffect> => {
    const { data } = await api.put(`/api/effects/${effectId}`, toSnakeCase(updates));
    return toCamelCase<VideoEffect>(data);
  },

  delete: async (effectId: string): Promise<void> => {
    await api.delete(`/api/effects/${effectId}`);
  },

  getThumbnailUrl: (effectId: string): string => {
    return `${API_BASE}/api/effects/${effectId}/thumbnail`;
  },

  getPreviewUrl: (effectId: string): string => {
    return `${API_BASE}/api/effects/${effectId}/preview`;
  },
};

export default api;
