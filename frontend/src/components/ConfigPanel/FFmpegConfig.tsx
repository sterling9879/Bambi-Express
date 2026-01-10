'use client';

import { useState, useEffect } from 'react';
import { Save } from 'lucide-react';
import { useApiConfig } from '@/hooks/useApiConfig';
import toast from 'react-hot-toast';
import type { FFmpegConfig as FFmpegConfigType, TransitionType, SceneDurationMode, SceneSplitMode } from '@/lib/types';

const TRANSITION_TYPES: { value: TransitionType; label: string }[] = [
  { value: 'fade', label: 'Fade (dissolve suave)' },
  { value: 'wipeleft', label: 'Wipe Left' },
  { value: 'wiperight', label: 'Wipe Right' },
  { value: 'slideup', label: 'Slide Up' },
  { value: 'slidedown', label: 'Slide Down' },
  { value: 'circleopen', label: 'Circle Open' },
  { value: 'circleclose', label: 'Circle Close' },
  { value: 'dissolve', label: 'Dissolve' },
  { value: 'pixelize', label: 'Pixelize' },
  { value: 'radial', label: 'Radial' },
  { value: 'none', label: 'Nenhuma (corte seco)' },
];

export function FFmpegConfig() {
  const { config, isSaving, saveConfig } = useApiConfig();
  const [localConfig, setLocalConfig] = useState<FFmpegConfigType | null>(null);

  useEffect(() => {
    if (config?.ffmpeg && !localConfig) {
      setLocalConfig(config.ffmpeg);
    }
  }, [config?.ffmpeg, localConfig]);

  const updateField = (path: string, value: unknown) => {
    if (!localConfig) return;

    setLocalConfig((prev) => {
      if (!prev) return prev;
      const newConfig = JSON.parse(JSON.stringify(prev));
      const keys = path.split('.');
      let obj = newConfig;

      for (let i = 0; i < keys.length - 1; i++) {
        obj = obj[keys[i]];
      }
      obj[keys[keys.length - 1]] = value;

      return newConfig;
    });
  };

  const handleSave = async () => {
    if (!config || !localConfig) return;

    try {
      await saveConfig({ ...config, ffmpeg: localConfig });
      toast.success('Configurações de vídeo salvas!');
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
          Configurações de Vídeo (FFMPEG)
        </h2>
      </div>

      <div className="p-6 space-y-8">
        {/* Resolution & Quality */}
        <section>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Dimensões e Qualidade
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Resolução
              </label>
              <div className="space-y-2">
                {[
                  { value: '1080p_landscape', width: 1920, height: 1080, label: '1920x1080 (Full HD - Landscape)' },
                  { value: '1080p_vertical', width: 1080, height: 1920, label: '1080x1920 (Full HD - Vertical/Stories)' },
                  { value: '720p', width: 1280, height: 720, label: '1280x720 (HD)' },
                ].map((option) => (
                  <label key={option.value} className="flex items-center space-x-3">
                    <input
                      type="radio"
                      name="resolution"
                      checked={
                        localConfig.resolution.width === option.width &&
                        localConfig.resolution.height === option.height
                      }
                      onChange={() => {
                        updateField('resolution.width', option.width);
                        updateField('resolution.height', option.height);
                        updateField('resolution.preset', option.value);
                      }}
                      className="w-4 h-4 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-gray-700 dark:text-gray-300">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  FPS
                </label>
                <select
                  value={localConfig.fps}
                  onChange={(e) => updateField('fps', parseInt(e.target.value))}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value={24}>24</option>
                  <option value={30}>30</option>
                  <option value={60}>60</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Preset de encoding
                </label>
                <select
                  value={localConfig.preset}
                  onChange={(e) => updateField('preset', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="ultrafast">Ultrafast (rápido, arquivo maior)</option>
                  <option value="fast">Fast</option>
                  <option value="medium">Medium (balanceado)</option>
                  <option value="slow">Slow</option>
                  <option value="veryslow">Very Slow (lento, menor arquivo)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Qualidade (CRF): {localConfig.crf}
              </label>
              <input
                type="range"
                min="18"
                max="28"
                value={localConfig.crf}
                onChange={(e) => updateField('crf', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Maior qualidade</span>
                <span>Menor arquivo</span>
              </div>
            </div>
          </div>
        </section>

        {/* Scene Config */}
        <section>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Divisão de Cenas
          </h3>
          <div className="space-y-4">
            <div className="space-y-2">
              {[
                { value: 'sentences', label: 'Por sentenças (recomendado)', description: 'Divide cenas por pontos finais (.!?). Mais cenas, mais controle.' },
                { value: 'paragraphs', label: 'Por parágrafos', description: 'Usa parágrafos da AssemblyAI. Menos cenas, mais longas.' },
                { value: 'gemini', label: 'Automático com IA', description: 'O Gemini decide onde dividir. Pode ser impreciso.' },
              ].map((option) => (
                <label key={option.value} className="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 dark:border-gray-600 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <input
                    type="radio"
                    name="sceneSplitMode"
                    value={option.value}
                    checked={(localConfig.sceneConfig?.splitMode || 'sentences') === option.value}
                    onChange={(e) => updateField('sceneConfig.splitMode', e.target.value as SceneSplitMode)}
                    className="w-4 h-4 mt-1 text-primary-600 focus:ring-primary-500"
                  />
                  <div>
                    <span className="block text-gray-700 dark:text-gray-300 font-medium">{option.label}</span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">{option.description}</span>
                  </div>
                </label>
              ))}
            </div>

            {(localConfig.sceneConfig?.splitMode || 'sentences') === 'sentences' && (
              <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Sentenças por cena: {localConfig.sceneConfig?.sentencesPerScene || 2}
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={localConfig.sceneConfig?.sentencesPerScene || 2}
                  onChange={(e) => updateField('sceneConfig.sentencesPerScene', parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Mais cenas (curtas)</span>
                  <span>Menos cenas (longas)</span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Ex: 30 sentenças com 2 por cena = 15 cenas
                </p>
              </div>
            )}

            {localConfig.sceneConfig?.splitMode === 'paragraphs' && (
              <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Parágrafos por cena: {localConfig.sceneConfig?.paragraphsPerScene || 3}
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={localConfig.sceneConfig?.paragraphsPerScene || 3}
                  onChange={(e) => updateField('sceneConfig.paragraphsPerScene', parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Mais cenas (curtas)</span>
                  <span>Menos cenas (longas)</span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Ex: 10 parágrafos com 2 por cena = 5 cenas
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Scene Duration */}
        <section>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Duração das Cenas
          </h3>
          <div className="space-y-4">
            <div className="space-y-2">
              {[
                { value: 'auto', label: 'Automático (baseado no áudio/transcrição)' },
                { value: 'fixed', label: 'Duração fixa por cena' },
                { value: 'range', label: 'Intervalo (min-max)' },
              ].map((option) => (
                <label key={option.value} className="flex items-center space-x-3">
                  <input
                    type="radio"
                    name="sceneDurationMode"
                    value={option.value}
                    checked={localConfig.sceneDuration.mode === option.value}
                    onChange={(e) => updateField('sceneDuration.mode', e.target.value as SceneDurationMode)}
                    className="w-4 h-4 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-gray-700 dark:text-gray-300">{option.label}</span>
                </label>
              ))}
            </div>

            {localConfig.sceneDuration.mode === 'fixed' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Duração de cada cena (segundos)
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={localConfig.sceneDuration.fixedDuration}
                  onChange={(e) => updateField('sceneDuration.fixedDuration', parseFloat(e.target.value))}
                  className="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            )}

            {localConfig.sceneDuration.mode === 'range' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Mínimo (s)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={localConfig.sceneDuration.minDuration}
                    onChange={(e) => updateField('sceneDuration.minDuration', parseFloat(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Máximo (s)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={localConfig.sceneDuration.maxDuration}
                    onChange={(e) => updateField('sceneDuration.maxDuration', parseFloat(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Transitions */}
        <section>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Transições</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tipo de transição
              </label>
              <select
                value={localConfig.transition.type}
                onChange={(e) => updateField('transition.type', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                {TRANSITION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Duração da transição: {localConfig.transition.duration}s
              </label>
              <input
                type="range"
                min="0.1"
                max="2"
                step="0.1"
                value={localConfig.transition.duration}
                onChange={(e) => updateField('transition.duration', parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <label className="flex items-center space-x-3">
              <input
                type="checkbox"
                checked={localConfig.transition.vary}
                onChange={(e) => updateField('transition.vary', e.target.checked)}
                className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
              />
              <span className="text-gray-700 dark:text-gray-300">
                Variar transições automaticamente
              </span>
            </label>
          </div>
        </section>

        {/* Visual Effects */}
        <section>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Efeitos Visuais</h3>
          <div className="space-y-6">
            {/* Ken Burns */}
            <div className="space-y-3">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={localConfig.effects.kenBurns.enabled}
                  onChange={(e) => updateField('effects.kenBurns.enabled', e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <span className="text-gray-700 dark:text-gray-300">Ken Burns (zoom/pan nas imagens)</span>
              </label>

              {localConfig.effects.kenBurns.enabled && (
                <div className="ml-7 space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Intensidade: {Math.round(localConfig.effects.kenBurns.intensity * 100)}%
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="0.2"
                      step="0.01"
                      value={localConfig.effects.kenBurns.intensity}
                      onChange={(e) => updateField('effects.kenBurns.intensity', parseFloat(e.target.value))}
                      className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Direção
                    </label>
                    <select
                      value={localConfig.effects.kenBurns.direction}
                      onChange={(e) => updateField('effects.kenBurns.direction', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="zoom_in">Sempre zoom in</option>
                      <option value="alternate">Alternar (in/out)</option>
                      <option value="random">Aleatório</option>
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Vignette */}
            <div className="space-y-3">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={localConfig.effects.vignette.enabled}
                  onChange={(e) => updateField('effects.vignette.enabled', e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                />
                <span className="text-gray-700 dark:text-gray-300">Vinheta (bordas escuras)</span>
              </label>

              {localConfig.effects.vignette.enabled && (
                <div className="ml-7">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Intensidade
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={localConfig.effects.vignette.intensity}
                    onChange={(e) => updateField('effects.vignette.intensity', parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  />
                </div>
              )}
            </div>

            {/* Grain */}
            <label className="flex items-center space-x-3">
              <input
                type="checkbox"
                checked={localConfig.effects.grain.enabled}
                onChange={(e) => updateField('effects.grain.enabled', e.target.checked)}
                className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
              />
              <span className="text-gray-700 dark:text-gray-300">Grain/noise (efeito filme)</span>
            </label>
          </div>
        </section>

        {/* Audio */}
        <section>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Áudio</h3>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Codec
                </label>
                <select
                  value={localConfig.audio.codec}
                  onChange={(e) => updateField('audio.codec', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="aac">AAC</option>
                  <option value="mp3">MP3</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Bitrate (kbps)
                </label>
                <select
                  value={localConfig.audio.bitrate}
                  onChange={(e) => updateField('audio.bitrate', parseInt(e.target.value))}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value={128}>128</option>
                  <option value={192}>192</option>
                  <option value={256}>256</option>
                  <option value={320}>320</option>
                </select>
              </div>
            </div>

            <label className="flex items-center space-x-3">
              <input
                type="checkbox"
                checked={localConfig.audio.normalize}
                onChange={(e) => updateField('audio.normalize', e.target.checked)}
                className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
              />
              <span className="text-gray-700 dark:text-gray-300">Normalizar áudio (loudnorm)</span>
            </label>

            {localConfig.audio.normalize && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Target LUFS
                </label>
                <select
                  value={localConfig.audio.targetLufs}
                  onChange={(e) => updateField('audio.targetLufs', parseInt(e.target.value))}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value={-14}>-14 LUFS (YouTube/Spotify)</option>
                  <option value={-16}>-16 LUFS (Broadcast)</option>
                  <option value={-23}>-23 LUFS (EBU)</option>
                </select>
              </div>
            )}
          </div>
        </section>
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
