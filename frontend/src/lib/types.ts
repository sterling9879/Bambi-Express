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
  };
  wavespeed: {
    apiKey: string;
    model: 'flux-dev-ultra-fast' | 'flux-schnell' | 'flux-dev';
    resolution: '1920x1080' | '1280x720' | '1080x1920';
    imageStyle?: string;
  };
  suno?: {
    apiKey: string;
    enabled: boolean;
  };
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
  sceneDuration: SceneDurationConfig;
  transition: TransitionConfig;
  effects: EffectsConfig;
  audio: AudioConfig;
}

// Full Config
export interface FullConfig {
  api: ApiConfig;
  music: MusicConfig;
  ffmpeg: FFmpegConfig;
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
