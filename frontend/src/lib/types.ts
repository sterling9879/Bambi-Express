// Audio Provider Type
export type AudioProvider = 'elevenlabs' | 'minimax';

// Minimax Emotion Type
export type MinimaxEmotion = 'neutral' | 'happy' | 'sad' | 'angry' | 'fearful' | 'disgusted' | 'surprised';

// API Configuration Types
export interface ApiConfig {
  elevenlabs: {
    apiKey: string;
    voiceId: string;
    modelId: string;
  };
  assemblyai: {
    apiKey: string;
    languageCode: string;
  };
  gemini: {
    apiKey: string;
    model: 'gemini-2.0-flash' | 'gemini-2.0-flash-lite' | 'gemini-2.5-pro';
    sceneContext?: string;
  };
  wavespeed: {
    apiKey: string;
    model: 'flux-dev-ultra-fast' | 'flux-schnell' | 'flux-dev';
    resolution: '1920x1080' | '1280x720' | '1080x1920';
    imageStyle?: string;
    outputFormat?: 'png' | 'jpeg';
  };
  suno?: {
    apiKey: string;
    enabled: boolean;
  };
  minimax: {
    voiceId: string;
    emotion: MinimaxEmotion;
    speed: number;
    pitch: number;
    volume: number;
    customVoices: CustomVoice[];
  };
  audioProvider: AudioProvider;
}

// Music Types
export type MusicMood =
  | 'alegre'
  | 'animado'
  | 'calmo'
  | 'dramatico'
  | 'inspirador'
  | 'melancolico'
  | 'raiva'
  | 'romantico'
  | 'sombrio'
  | 'vibrante';

export interface MusicTrack {
  id: string;
  filename: string;
  originalName: string;
  durationMs: number;
  mood: MusicMood;
  tags: string[];
  loopStartMs?: number;
  loopEndMs?: number;
  uploadedAt: string;
  fileSize: number;
  waveformData?: number[];
}

export type MusicMode = 'none' | 'library' | 'ai_generated';

export type MusicPreset =
  | 'corporate'
  | 'cinematic_epic'
  | 'lofi_chill'
  | 'upbeat_pop'
  | 'ambient';

export interface AIMusicConfig {
  stylePrompt: string;
  preset?: MusicPreset;
  generateVariations: boolean;
  variationsCount: number;
  instrumentalOnly: boolean;
}

export interface MusicConfig {
  mode: MusicMode;
  volume: number;
  duckingEnabled: boolean;
  duckingIntensity: number;
  fadeInMs: number;
  fadeOutMs: number;
  crossfadeMs: number;
  autoSelectByMood: boolean;
  manualTrackId?: string;
  secondaryTrackId?: string;
  aiConfig?: AIMusicConfig;
}

// FFmpeg Types
export type TransitionType =
  | 'fade'
  | 'wipeleft'
  | 'wiperight'
  | 'slideup'
  | 'slidedown'
  | 'circleopen'
  | 'circleclose'
  | 'dissolve'
  | 'pixelize'
  | 'radial'
  | 'none';

export type SceneDurationMode = 'auto' | 'fixed' | 'range';
export type SceneSplitMode = 'paragraphs' | 'gemini';

export interface SceneConfig {
  splitMode: SceneSplitMode;
  paragraphsPerScene: number;
}

export interface Resolution {
  width: number;
  height: number;
  preset?: '1080p_landscape' | '1080p_vertical' | '720p' | 'custom';
}

export interface SceneDurationConfig {
  mode: SceneDurationMode;
  fixedDuration?: number;
  minDuration?: number;
  maxDuration?: number;
}

export interface TransitionConfig {
  type: TransitionType;
  duration: number;
  vary: boolean;
  allowedTypes?: TransitionType[];
}

export interface KenBurnsConfig {
  enabled: boolean;
  intensity: number;
  direction: 'zoom_in' | 'alternate' | 'random';
}

export interface VignetteConfig {
  enabled: boolean;
  intensity: number;
}

export interface GrainConfig {
  enabled: boolean;
  intensity: number;
}

export interface EffectsConfig {
  kenBurns: KenBurnsConfig;
  vignette: VignetteConfig;
  grain: GrainConfig;
}

export interface AudioConfig {
  codec: 'aac' | 'mp3';
  bitrate: number;
  narrationVolume: number;
  normalize: boolean;
  targetLufs: number;
}

export interface FFmpegConfig {
  resolution: Resolution;
  fps: 24 | 30 | 60;
  crf: number;
  preset: 'ultrafast' | 'fast' | 'medium' | 'slow' | 'veryslow';
  sceneConfig: SceneConfig;
  sceneDuration: SceneDurationConfig;
  transition: TransitionConfig;
  effects: EffectsConfig;
  audio: AudioConfig;
}

// GPU / Local Image Generation Types
export type ImageProvider = 'wavespeed' | 'local';
export type VramMode = 'auto' | '4gb' | '6gb' | '8gb';

export interface GPUConfig {
  enabled: boolean;
  provider: ImageProvider;
  vramMode: VramMode;
  autoFallbackToApi: boolean;
}

export interface GPUInfo {
  available: boolean;
  name?: string;
  vramTotalGb?: number;
  vramFreeGb?: number;
  computeCapability?: string;
  recommendedMode?: string;
  error?: string;
}

export interface ModelInfo {
  mode: string;
  modelName: string;
  hfId: string;
  maxResolution: number;
  defaultSteps: number;
  loaded: boolean;
  quantized: boolean;
}

// Effects Config
export type BlendMode = 'lighten' | 'screen' | 'add';

export interface EffectsConfig {
  enabled: boolean;
  effectId?: string;
  blendMode: BlendMode;
  opacity: number;
}

export interface VideoEffect {
  id: string;
  name: string;
  filename: string;
  durationMs: number;
  description: string;
  category: string;
  thumbnailUrl?: string;
  createdAt: string;
  fileSize: number;
}

// Subtitle Config
export type SubtitlePosition = 'bottom' | 'top' | 'middle';
export type SubtitleLanguage = 'pt' | 'en' | 'es' | 'auto';

export interface SubtitleConfig {
  enabled: boolean;
  language: SubtitleLanguage;
  position: SubtitlePosition;
  fontSize: number;
  fontColor: string;
  outlineColor: string;
  outlineWidth: number;
  backgroundOpacity: number;
  marginVertical: number;
}

// Full Config
export interface FullConfig {
  api: ApiConfig;
  music: MusicConfig;
  ffmpeg: FFmpegConfig;
  gpu: GPUConfig;
  effects: EffectsConfig;
  subtitles: SubtitleConfig;
}

// Job Types
export type JobStatus =
  | 'pending'
  | 'processing_text'
  | 'generating_audio'
  | 'merging_audio'
  | 'transcribing'
  | 'analyzing_scenes'
  | 'selecting_music'
  | 'generating_images'
  | 'mixing_audio'
  | 'composing_video'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface Job {
  jobId: string;
  status: JobStatus;
  progress: number;
  currentStep: string;
  details: Record<string, unknown>;
  logs: string[];
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

export interface JobResult {
  jobId: string;
  status: JobStatus;
  videoPath?: string;
  videoUrl?: string;
  durationSeconds?: number;
  scenesCount?: number;
  fileSize?: number;
  processingTimeSeconds?: number;
}

// API Response Types
export interface TextAnalysis {
  charCount: number;
  wordCount: number;
  estimatedDurationSeconds: number;
  estimatedChunks: number;
}

export interface ApiTestResult {
  connected: boolean;
  error?: string;
  details?: Record<string, unknown>;
}

export interface CreditsResponse {
  elevenlabs?: number;
  wavespeed?: number;
  errors: Record<string, string>;
}

export interface Voice {
  voiceId: string;
  name: string;
  category?: string;
  labels?: Record<string, string>;
}

export interface MinimaxVoice {
  voice_id: string;
  name: string;
  gender: 'male' | 'female' | 'neutral';
  language: string;
}

export interface CustomVoice {
  id: string;
  voiceId: string;
  name: string;
  gender: 'male' | 'female' | 'neutral';
  description: string;
}

export interface CustomVoiceCreate {
  voiceId: string;
  name: string;
  gender?: 'male' | 'female' | 'neutral';
  description?: string;
}

// History Types
export interface Channel {
  id: string;
  name: string;
  description?: string;
  color: string;
  createdAt: string;
  videoCount: number;
}

export interface ChannelCreate {
  name: string;
  description?: string;
  color?: string;
}

export interface VideoHistory {
  id: string;
  jobId: string;
  title: string;
  channelId?: string;
  channelName?: string;
  textPreview: string;
  videoPath: string;
  videoUrl?: string;
  thumbnailUrl?: string;
  durationSeconds: number;
  scenesCount: number;
  fileSize: number;
  resolution: string;
  createdAt: string;
}

export interface VideoHistoryList {
  videos: VideoHistory[];
  total: number;
  page: number;
  limit: number;
}

export type ElementType = 'image' | 'audio' | 'narration' | 'music';

export interface Element {
  id: string;
  jobId: string;
  elementType: ElementType;
  filePath: string;
  fileUrl?: string;
  fileSize: number;
  sceneIndex?: number;
  prompt?: string;
  durationMs?: number;
  metadata?: Record<string, unknown>;
  createdAt: string;
}

export interface ElementList {
  elements: Element[];
  total: number;
}

export interface HistoryStats {
  totalVideos: number;
  totalDurationSeconds: number;
  totalSizeBytes: number;
  videosByChannel: Record<string, number>;
  recentVideos: VideoHistory[];
}

// Batch Types
export type BatchStatus =
  | 'pending'
  | 'processing'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type BatchItemStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'skipped';

export interface BatchItem {
  id: string;
  title: string;
  status: BatchItemStatus;
  jobId?: string;
  progress: number;
  currentStep: string;
  videoPath?: string;
  error?: string;
  startedAt?: string;
  completedAt?: string;
  durationSeconds?: number;
}

export interface Batch {
  batchId: string;
  name: string;
  status: BatchStatus;
  totalItems: number;
  completedItems: number;
  failedItems: number;
  currentItemIndex: number;
  currentItemTitle?: string;
  currentItemStep?: string;
  progress: number;
  items: BatchItem[];
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

export interface BatchListItem {
  batchId: string;
  name: string;
  status: BatchStatus;
  totalItems: number;
  completedItems: number;
  failedItems: number;
  progress: number;
  createdAt: string;
  completedAt?: string;
}

export interface BatchAnalysis {
  totalItems: number;
  totalCharacters: number;
  totalWords: number;
  estimatedTotalDurationSeconds: number;
  estimatedProcessingTimeMinutes: number;
  itemsAnalysis: Array<{
    index: number;
    title: string;
    charCount?: number;
    wordCount?: number;
    estimatedDurationSeconds?: number;
    estimatedChunks?: number;
    error?: string;
  }>;
}

export interface BatchCreateItem {
  title: string;
  text: string;
}

export interface BatchDownloadItem {
  index: number;
  title: string;
  downloadUrl: string;
  fileSize: number;
}
