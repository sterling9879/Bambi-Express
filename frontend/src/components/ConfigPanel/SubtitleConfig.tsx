'use client';

import { useState, useEffect } from 'react';
import { Subtitles, Save, AlignCenter, AlignVerticalJustifyEnd, AlignVerticalJustifyStart } from 'lucide-react';
import { useApiConfig } from '@/hooks/useApiConfig';
import type { SubtitleConfig as SubtitleConfigType, SubtitlePosition } from '@/lib/types';
import toast from 'react-hot-toast';

const POSITIONS: { value: SubtitlePosition; label: string; description: string; icon: typeof AlignCenter }[] = [
  { value: 'bottom', label: 'Inferior', description: 'Estilo filme tradicional', icon: AlignVerticalJustifyEnd },
  { value: 'top', label: 'Superior', description: 'Topo do vídeo', icon: AlignVerticalJustifyStart },
  { value: 'middle', label: 'Centro', description: 'Centralizado', icon: AlignCenter },
];

const COLORS = [
  { value: 'white', label: 'Branco', hex: '#FFFFFF' },
  { value: 'yellow', label: 'Amarelo', hex: '#FFFF00' },
  { value: 'cyan', label: 'Ciano', hex: '#00FFFF' },
  { value: 'green', label: 'Verde', hex: '#00FF00' },
];

const OUTLINE_COLORS = [
  { value: 'black', label: 'Preto', hex: '#000000' },
  { value: 'blue', label: 'Azul', hex: '#0000FF' },
  { value: 'red', label: 'Vermelho', hex: '#FF0000' },
];

export function SubtitleConfig() {
  const { config: fullConfig, isSaving, saveConfig } = useApiConfig();

  // Local state for subtitle config
  const [localConfig, setLocalConfig] = useState<SubtitleConfigType>({
    enabled: false,
    position: 'bottom',
    fontSize: 48,
    fontColor: 'white',
    outlineColor: 'black',
    outlineWidth: 3,
    backgroundOpacity: 0.0,
    marginVertical: 50,
  });

  // Sync local config with full config
  useEffect(() => {
    if (fullConfig?.subtitles) {
      setLocalConfig(fullConfig.subtitles);
    }
  }, [fullConfig?.subtitles]);

  const handleConfigChange = (newConfig: SubtitleConfigType) => {
    setLocalConfig(newConfig);
  };

  const handleSave = async () => {
    if (!fullConfig) return;
    try {
      await saveConfig({ ...fullConfig, subtitles: localConfig });
      toast.success('Configurações de legendas salvas!');
    } catch (error) {
      toast.error('Erro ao salvar configurações');
    }
  };

  const config = localConfig;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
            <Subtitles className="w-5 h-5 mr-2" />
            Legendas
          </h2>
          <div className="flex items-center space-x-2">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.enabled}
                onChange={(e) => handleConfigChange({ ...config, enabled: e.target.checked })}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Ativar legendas</span>
            </label>
          </div>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Adicione legendas estilo cinema aos seus vídeos
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Position Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-900 dark:text-white mb-3">
            Posição das Legendas
          </label>
          <div className="grid grid-cols-3 gap-3">
            {POSITIONS.map((pos) => (
              <button
                key={pos.value}
                onClick={() => handleConfigChange({ ...config, position: pos.value })}
                className={`p-4 border-2 rounded-lg transition-all ${
                  config.position === pos.value
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                }`}
              >
                <pos.icon className={`w-6 h-6 mx-auto mb-2 ${
                  config.position === pos.value
                    ? 'text-primary-600'
                    : 'text-gray-400'
                }`} />
                <p className={`font-medium text-sm ${
                  config.position === pos.value
                    ? 'text-primary-600'
                    : 'text-gray-700 dark:text-gray-300'
                }`}>
                  {pos.label}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {pos.description}
                </p>
              </button>
            ))}
          </div>
        </div>

        {/* Preview */}
        <div className="bg-gray-900 rounded-lg p-4 relative aspect-video flex items-end justify-center">
          <div
            className="absolute w-full text-center px-4"
            style={{
              bottom: config.position === 'bottom' ? `${config.marginVertical}px` : 'auto',
              top: config.position === 'top' ? `${config.marginVertical}px` : 'auto',
              ...(config.position === 'middle' && { top: '50%', transform: 'translateY(-50%)' }),
            }}
          >
            <span
              style={{
                fontSize: `${Math.min(config.fontSize / 2, 24)}px`,
                color: COLORS.find(c => c.value === config.fontColor)?.hex || '#FFFFFF',
                textShadow: `
                  -${config.outlineWidth}px -${config.outlineWidth}px 0 ${OUTLINE_COLORS.find(c => c.value === config.outlineColor)?.hex || '#000'},
                  ${config.outlineWidth}px -${config.outlineWidth}px 0 ${OUTLINE_COLORS.find(c => c.value === config.outlineColor)?.hex || '#000'},
                  -${config.outlineWidth}px ${config.outlineWidth}px 0 ${OUTLINE_COLORS.find(c => c.value === config.outlineColor)?.hex || '#000'},
                  ${config.outlineWidth}px ${config.outlineWidth}px 0 ${OUTLINE_COLORS.find(c => c.value === config.outlineColor)?.hex || '#000'}
                `,
              }}
            >
              Preview da legenda
            </span>
          </div>
          <div className="absolute top-2 left-2 text-xs text-gray-500">Preview</div>
        </div>

        {/* Font Settings */}
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Tamanho da Fonte ({config.fontSize}px)
            </label>
            <input
              type="range"
              min="24"
              max="72"
              step="2"
              value={config.fontSize}
              onChange={(e) => handleConfigChange({ ...config, fontSize: parseInt(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Pequeno</span>
              <span>Grande</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Margem Vertical ({config.marginVertical}px)
            </label>
            <input
              type="range"
              min="20"
              max="150"
              step="5"
              value={config.marginVertical}
              onChange={(e) => handleConfigChange({ ...config, marginVertical: parseInt(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Perto da borda</span>
              <span>Longe da borda</span>
            </div>
          </div>
        </div>

        {/* Color Settings */}
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Cor do Texto
            </label>
            <div className="flex space-x-2">
              {COLORS.map((color) => (
                <button
                  key={color.value}
                  onClick={() => handleConfigChange({ ...config, fontColor: color.value })}
                  className={`w-10 h-10 rounded-lg border-2 transition-all ${
                    config.fontColor === color.value
                      ? 'border-primary-500 ring-2 ring-primary-200'
                      : 'border-gray-300 dark:border-gray-600'
                  }`}
                  style={{ backgroundColor: color.hex }}
                  title={color.label}
                />
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Cor do Contorno
            </label>
            <div className="flex space-x-2">
              {OUTLINE_COLORS.map((color) => (
                <button
                  key={color.value}
                  onClick={() => handleConfigChange({ ...config, outlineColor: color.value })}
                  className={`w-10 h-10 rounded-lg border-2 transition-all ${
                    config.outlineColor === color.value
                      ? 'border-primary-500 ring-2 ring-primary-200'
                      : 'border-gray-300 dark:border-gray-600'
                  }`}
                  style={{ backgroundColor: color.hex }}
                  title={color.label}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Outline Width */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Espessura do Contorno ({config.outlineWidth}px)
          </label>
          <input
            type="range"
            min="1"
            max="6"
            step="1"
            value={config.outlineWidth}
            onChange={(e) => handleConfigChange({ ...config, outlineWidth: parseInt(e.target.value) })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Fino</span>
            <span>Grosso</span>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
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
    </div>
  );
}
