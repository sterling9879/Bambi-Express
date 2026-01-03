'use client';

import { useState, useEffect } from 'react';
import { Eye, EyeOff, Check, X, RefreshCw, Save } from 'lucide-react';
import { useApiConfig } from '@/hooks/useApiConfig';
import toast from 'react-hot-toast';
import type { ApiConfig as ApiConfigType } from '@/lib/types';

export function ApiConfig() {
  const {
    config,
    isLoading,
    isSaving,
    saveConfig,
    testApi,
    testingApi,
    testResults,
    credits,
    refetchCredits,
    voices,
  } = useApiConfig();

  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [localConfig, setLocalConfig] = useState<ApiConfigType | null>(null);

  // Update local config when config changes
  useEffect(() => {
    if (config?.api && !localConfig) {
      setLocalConfig(config.api);
    }
  }, [config?.api, localConfig]);

  const toggleShowKey = (key: string) => {
    setShowKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const updateField = (path: string, value: string) => {
    if (!localConfig) return;

    const keys = path.split('.');
    const newConfig = JSON.parse(JSON.stringify(localConfig));
    let obj: Record<string, unknown> = newConfig;

    for (let i = 0; i < keys.length - 1; i++) {
      obj = obj[keys[i]] as Record<string, unknown>;
    }
    obj[keys[keys.length - 1]] = value;

    setLocalConfig(newConfig);
  };

  const handleSave = async () => {
    if (!config || !localConfig) return;

    try {
      await saveConfig({ ...config, api: localConfig });
      toast.success('Configurações salvas!');
    } catch (error) {
      toast.error('Erro ao salvar configurações');
    }
  };

  const handleTestApi = async (apiName: string) => {
    try {
      const result = await testApi(apiName);
      if (result.connected) {
        toast.success(`${apiName} conectado!`);
      } else {
        toast.error(`Falha na conexão: ${result.error}`);
      }
    } catch (error) {
      toast.error('Erro ao testar API');
    }
  };

  const handleTestAll = async () => {
    const apis = ['elevenlabs', 'assemblyai', 'gemini', 'wavespeed'];
    for (const api of apis) {
      await handleTestApi(api);
    }
  };

  if (isLoading || !localConfig) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  const ApiSection = ({
    title,
    apiName,
    children,
    status,
  }: {
    title: string;
    apiName: string;
    children: React.ReactNode;
    status?: React.ReactNode;
  }) => (
    <div className="border-b border-gray-200 dark:border-gray-700 pb-6 last:border-0">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">{title}</h3>
        <div className="flex items-center space-x-2">
          {testResults[apiName] && (
            <span
              className={`flex items-center space-x-1 text-sm ${
                testResults[apiName].connected
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-red-600 dark:text-red-400'
              }`}
            >
              {testResults[apiName].connected ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Conectado</span>
                </>
              ) : (
                <>
                  <X className="w-4 h-4" />
                  <span>Falha</span>
                </>
              )}
            </span>
          )}
          {status}
        </div>
      </div>
      {children}
    </div>
  );

  const ApiKeyInput = ({
    label,
    value,
    onChange,
    keyName,
  }: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    keyName: string;
  }) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label}
      </label>
      <div className="relative">
        <input
          type={showKeys[keyName] ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-4 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          placeholder="••••••••••••••••"
        />
        <button
          type="button"
          onClick={() => toggleShowKey(keyName)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {showKeys[keyName] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
          Configuração de APIs
        </h2>
      </div>

      <div className="p-6 space-y-6">
        {/* ElevenLabs */}
        <ApiSection
          title="ElevenLabs"
          apiName="elevenlabs"
          status={
            credits?.elevenlabs != null && (
              <span className="text-sm text-gray-500">
                Créditos: {credits.elevenlabs.toLocaleString()}
              </span>
            )
          }
        >
          <div className="space-y-4">
            <ApiKeyInput
              label="API Key"
              value={localConfig.elevenlabs.apiKey}
              onChange={(v) => updateField('elevenlabs.apiKey', v)}
              keyName="elevenlabs"
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Voice ID
              </label>
              <select
                value={localConfig.elevenlabs.voiceId}
                onChange={(e) => updateField('elevenlabs.voiceId', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">Selecionar voz...</option>
                {voices.map((voice) => (
                  <option key={voice.voiceId} value={voice.voiceId}>
                    {voice.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={() => handleTestApi('elevenlabs')}
              disabled={testingApi === 'elevenlabs'}
              className="text-sm text-primary-600 hover:text-primary-700 disabled:opacity-50"
            >
              {testingApi === 'elevenlabs' ? 'Testando...' : 'Testar conexão'}
            </button>
          </div>
        </ApiSection>

        {/* AssemblyAI */}
        <ApiSection title="AssemblyAI (Transcrição)" apiName="assemblyai">
          <div className="space-y-4">
            <ApiKeyInput
              label="API Key"
              value={localConfig.assemblyai.apiKey}
              onChange={(v) => updateField('assemblyai.apiKey', v)}
              keyName="assemblyai"
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Idioma
              </label>
              <select
                value={localConfig.assemblyai.languageCode}
                onChange={(e) => updateField('assemblyai.languageCode', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="pt">Português (BR)</option>
                <option value="en">English</option>
                <option value="es">Español</option>
                <option value="auto">Auto-detectar</option>
              </select>
            </div>
            <button
              onClick={() => handleTestApi('assemblyai')}
              disabled={testingApi === 'assemblyai'}
              className="text-sm text-primary-600 hover:text-primary-700 disabled:opacity-50"
            >
              {testingApi === 'assemblyai' ? 'Testando...' : 'Testar conexão'}
            </button>
          </div>
        </ApiSection>

        {/* Gemini */}
        <ApiSection title="Google Gemini" apiName="gemini">
          <div className="space-y-4">
            <ApiKeyInput
              label="API Key"
              value={localConfig.gemini.apiKey}
              onChange={(v) => updateField('gemini.apiKey', v)}
              keyName="gemini"
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Modelo
              </label>
              <select
                value={localConfig.gemini.model}
                onChange={(e) => updateField('gemini.model', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                <option value="gemini-2.0-flash-lite">Gemini 2.0 Flash Lite</option>
                <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
              </select>
            </div>
            <button
              onClick={() => handleTestApi('gemini')}
              disabled={testingApi === 'gemini'}
              className="text-sm text-primary-600 hover:text-primary-700 disabled:opacity-50"
            >
              {testingApi === 'gemini' ? 'Testando...' : 'Testar conexão'}
            </button>
          </div>
        </ApiSection>

        {/* WaveSpeed */}
        <ApiSection
          title="WaveSpeed Flux"
          apiName="wavespeed"
          status={
            credits?.wavespeed != null && (
              <span className="text-sm text-gray-500">
                Créditos: ${credits.wavespeed.toFixed(2)}
              </span>
            )
          }
        >
          <div className="space-y-4">
            <ApiKeyInput
              label="API Key"
              value={localConfig.wavespeed.apiKey}
              onChange={(v) => updateField('wavespeed.apiKey', v)}
              keyName="wavespeed"
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Modelo
              </label>
              <select
                value={localConfig.wavespeed.model}
                onChange={(e) => updateField('wavespeed.model', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="flux-dev-ultra-fast">Flux Dev Ultra Fast (Recomendado)</option>
                <option value="flux-schnell">Flux Schnell</option>
                <option value="flux-dev">Flux Dev</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Resolução
              </label>
              <select
                value={localConfig.wavespeed.resolution}
                onChange={(e) => updateField('wavespeed.resolution', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="1920x1080">1920x1080 (Landscape)</option>
                <option value="1080x1920">1080x1920 (Vertical)</option>
                <option value="1280x720">1280x720 (HD)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Estilo Visual das Imagens
              </label>
              <textarea
                value={localConfig.wavespeed.imageStyle || ''}
                onChange={(e) => updateField('wavespeed.imageStyle', e.target.value)}
                placeholder="cinematic, dramatic lighting, 8k, hyperrealistic, professional photography"
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
              />
              <p className="text-xs text-gray-500 mt-1">
                Este estilo será adicionado a todos os prompts de imagem gerados
              </p>
            </div>
            <button
              onClick={() => handleTestApi('wavespeed')}
              disabled={testingApi === 'wavespeed'}
              className="text-sm text-primary-600 hover:text-primary-700 disabled:opacity-50"
            >
              {testingApi === 'wavespeed' ? 'Testando...' : 'Testar conexão'}
            </button>
          </div>
        </ApiSection>
      </div>

      {/* Actions */}
      <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-4">
        <button
          onClick={handleTestAll}
          disabled={!!testingApi}
          className="flex items-center space-x-2 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${testingApi ? 'animate-spin' : ''}`} />
          <span>Testar Todas</span>
        </button>
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
