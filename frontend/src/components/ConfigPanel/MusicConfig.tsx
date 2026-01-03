'use client';

import { useState, useEffect } from 'react';
import { Save } from 'lucide-react';
import { useApiConfig } from '@/hooks/useApiConfig';
import { useMusicLibrary } from '@/hooks/useMusicLibrary';
import toast from 'react-hot-toast';
import type { MusicConfig as MusicConfigType, MusicMode, MusicPreset } from '@/lib/types';

export function MusicConfig() {
  const { config, isSaving, saveConfig } = useApiConfig();
  const { tracks } = useMusicLibrary();

  const [localConfig, setLocalConfig] = useState<MusicConfigType | null>(null);

  useEffect(() => {
    if (config?.music && !localConfig) {
      setLocalConfig(config.music);
    }
  }, [config?.music, localConfig]);

  const updateField = (field: string, value: unknown) => {
    if (!localConfig) return;

    setLocalConfig((prev) => {
      if (!prev) return prev;
      const keys = field.split('.');
      const newConfig = { ...prev };
      let obj: Record<string, unknown> = newConfig;

      for (let i = 0; i < keys.length - 1; i++) {
        obj[keys[i]] = { ...(obj[keys[i]] as Record<string, unknown>) };
        obj = obj[keys[i]] as Record<string, unknown>;
      }
      obj[keys[keys.length - 1]] = value;

      return newConfig as MusicConfigType;
    });
  };

  const handleSave = async () => {
    if (!config || !localConfig) return;

    try {
      await saveConfig({ ...config, music: localConfig });
      toast.success('Configurações de música salvas!');
    } catch {
      toast.error('Erro ao salvar configurações');
    }
  };

  if (!localConfig) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Configuração de Música
        </h2>
      </div>

      <div className="p-6 space-y-6">
        {/* Mode Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Modo de música
          </label>
          <div className="space-y-2">
            {[
              { value: 'none', label: 'Sem música' },
              { value: 'library', label: 'Usar biblioteca (músicas uploadadas)' },
              { value: 'ai_generated', label: 'Gerar com IA (Suno) - Requer API key' },
            ].map((option) => (
              <label key={option.value} className="flex items-center space-x-3">
                <input
                  type="radio"
                  name="musicMode"
                  value={option.value}
                  checked={localConfig.mode === option.value}
                  onChange={(e) => updateField('mode', e.target.value as MusicMode)}
                  className="w-4 h-4 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-gray-700 dark:text-gray-300">{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        {localConfig.mode !== 'none' && (
          <>
            {/* Volume */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Volume da música: {Math.round(localConfig.volume * 100)}%
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={localConfig.volume}
                onChange={(e) => updateField('volume', parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Baixo</span>
                <span>Alto</span>
              </div>
            </div>

            {/* Ducking */}
            <div className="space-y-4">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={localConfig.duckingEnabled}
                  onChange={(e) => updateField('duckingEnabled', e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <span className="text-gray-700 dark:text-gray-300">
                  Ducking (abaixar música durante fala)
                </span>
              </label>

              {localConfig.duckingEnabled && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Intensidade do ducking
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={localConfig.duckingIntensity}
                    onChange={(e) => updateField('duckingIntensity', parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Suave</span>
                    <span>Forte</span>
                  </div>
                </div>
              )}
            </div>

            {/* Fade Settings */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Fade in (ms)
                </label>
                <input
                  type="number"
                  value={localConfig.fadeInMs}
                  onChange={(e) => updateField('fadeInMs', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Fade out (ms)
                </label>
                <input
                  type="number"
                  value={localConfig.fadeOutMs}
                  onChange={(e) => updateField('fadeOutMs', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Crossfade (ms)
                </label>
                <input
                  type="number"
                  value={localConfig.crossfadeMs}
                  onChange={(e) => updateField('crossfadeMs', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>

            {/* Library Mode Options */}
            {localConfig.mode === 'library' && (
              <div className="space-y-4">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={localConfig.autoSelectByMood}
                    onChange={(e) => updateField('autoSelectByMood', e.target.checked)}
                    className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                  />
                  <span className="text-gray-700 dark:text-gray-300">
                    Deixar IA escolher músicas baseado no mood
                  </span>
                </label>

                {!localConfig.autoSelectByMood && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Música principal
                    </label>
                    <select
                      value={localConfig.manualTrackId || ''}
                      onChange={(e) => updateField('manualTrackId', e.target.value || undefined)}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">Selecionar...</option>
                      {tracks.map((track) => (
                        <option key={track.id} value={track.id}>
                          {track.originalName} ({track.mood})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}

            {/* AI Generation Options */}
            {localConfig.mode === 'ai_generated' && (
              <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <h4 className="font-medium text-gray-900 dark:text-white">
                  Geração de Música com IA
                </h4>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Estilo musical
                  </label>
                  <textarea
                    value={localConfig.aiConfig?.stylePrompt || ''}
                    onChange={(e) => updateField('aiConfig.stylePrompt', e.target.value)}
                    placeholder="Ex: Música épica orquestral com violinos e tambores, estilo trailer de filme"
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Ou usar preset
                  </label>
                  <select
                    value={localConfig.aiConfig?.preset || ''}
                    onChange={(e) =>
                      updateField('aiConfig.preset', e.target.value as MusicPreset || undefined)
                    }
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="">Sem preset</option>
                    <option value="corporate">Corporate (neutro, profissional)</option>
                    <option value="cinematic_epic">Cinematic Epic (épico, emocional)</option>
                    <option value="lofi_chill">Lo-fi Chill (relaxante, moderno)</option>
                    <option value="upbeat_pop">Upbeat Pop (energético, positivo)</option>
                    <option value="ambient">Ambient (atmosférico, suave)</option>
                  </select>
                </div>

                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={localConfig.aiConfig?.instrumentalOnly ?? true}
                    onChange={(e) => updateField('aiConfig.instrumentalOnly', e.target.checked)}
                    className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                  />
                  <span className="text-gray-700 dark:text-gray-300">Instrumental only (sem vocais)</span>
                </label>
              </div>
            )}
          </>
        )}
      </div>

      {/* Actions */}
      <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>{isSaving ? 'Salvando...' : 'Salvar'}</span>
        </button>
      </div>
    </div>
  );
}
