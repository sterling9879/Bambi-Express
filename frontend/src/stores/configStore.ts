import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { FullConfig, ApiConfig, MusicConfig, FFmpegConfig } from '@/lib/types';

interface ConfigState {
  config: FullConfig | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setConfig: (config: FullConfig) => void;
  updateApiConfig: (apiConfig: Partial<ApiConfig>) => void;
  updateMusicConfig: (musicConfig: Partial<MusicConfig>) => void;
  updateFFmpegConfig: (ffmpegConfig: Partial<FFmpegConfig>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const defaultApiConfig: ApiConfig = {
  elevenlabs: {
    apiKey: '',
    voiceId: '',
    modelId: 'eleven_multilingual_v2',
  },
  assemblyai: {
    apiKey: '',
    languageCode: 'pt',
  },
  gemini: {
    apiKey: '',
    model: 'gemini-2.0-flash',
  },
  wavespeed: {
    apiKey: '',
    model: 'flux-dev-ultra-fast',
    resolution: '1920x1080',
    imageStyle: '',
  },
};

const defaultMusicConfig: MusicConfig = {
  mode: 'none',
  volume: 0.15,
  duckingEnabled: true,
  duckingIntensity: 0.7,
  fadeInMs: 1000,
  fadeOutMs: 2000,
  crossfadeMs: 1500,
  autoSelectByMood: true,
};

const defaultFFmpegConfig: FFmpegConfig = {
  resolution: {
    width: 1920,
    height: 1080,
    preset: '1080p_landscape',
  },
  fps: 30,
  crf: 23,
  preset: 'medium',
  sceneDuration: {
    mode: 'auto',
    fixedDuration: 4.0,
    minDuration: 3.0,
    maxDuration: 6.0,
  },
  transition: {
    type: 'fade',
    duration: 0.5,
    vary: false,
  },
  effects: {
    kenBurns: {
      enabled: true,
      intensity: 0.05,
      direction: 'alternate',
    },
    vignette: {
      enabled: false,
      intensity: 0.3,
    },
    grain: {
      enabled: false,
      intensity: 0.1,
    },
  },
  audio: {
    codec: 'aac',
    bitrate: 192,
    narrationVolume: 1.0,
    normalize: true,
    targetLufs: -14,
  },
};

const defaultConfig: FullConfig = {
  api: defaultApiConfig,
  music: defaultMusicConfig,
  ffmpeg: defaultFFmpegConfig,
};

export const useConfigStore = create<ConfigState>()(
  persist(
    (set) => ({
      config: null,
      isLoading: false,
      error: null,

      setConfig: (config) => set({ config, error: null }),

      updateApiConfig: (apiConfig) =>
        set((state) => ({
          config: state.config
            ? {
                ...state.config,
                api: { ...state.config.api, ...apiConfig },
              }
            : { ...defaultConfig, api: { ...defaultApiConfig, ...apiConfig } },
        })),

      updateMusicConfig: (musicConfig) =>
        set((state) => ({
          config: state.config
            ? {
                ...state.config,
                music: { ...state.config.music, ...musicConfig },
              }
            : { ...defaultConfig, music: { ...defaultMusicConfig, ...musicConfig } },
        })),

      updateFFmpegConfig: (ffmpegConfig) =>
        set((state) => ({
          config: state.config
            ? {
                ...state.config,
                ffmpeg: { ...state.config.ffmpeg, ...ffmpegConfig },
              }
            : { ...defaultConfig, ffmpeg: { ...defaultFFmpegConfig, ...ffmpegConfig } },
        })),

      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      reset: () => set({ config: defaultConfig, isLoading: false, error: null }),
    }),
    {
      name: 'video-generator-config',
      partialize: (state) => ({ config: state.config }),
    }
  )
);
