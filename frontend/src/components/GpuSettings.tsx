'use client';

import { useState, useEffect } from 'react';
import { Cpu, Check, X, RefreshCw, Loader2, Zap, HardDrive } from 'lucide-react';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface GPUInfo {
  available: boolean;
  name?: string;
  vramTotalGb?: number;
  vramFreeGb?: number;
  computeCapability?: string;
  recommendedMode?: string;
  error?: string;
}

interface ModelInfo {
  mode: string;
  modelName: string;
  hfId: string;
  maxResolution: number;
  defaultSteps: number;
  loaded: boolean;
  quantized: boolean;
}

interface AvailableModel {
  name: string;
  hfId: string;
  maxResolution: number;
  defaultSteps: number;
  vramRequired: string;
  quantized: boolean;
}

export function GpuSettings() {
  const [gpuInfo, setGpuInfo] = useState<GPUInfo | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [availableModels, setAvailableModels] = useState<Record<string, AvailableModel>>({});
  const [provider, setProvider] = useState<'local' | 'wavespeed'>('wavespeed');
  const [vramMode, setVramMode] = useState<string>('auto');
  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState<string>('');
  const [testResult, setTestResult] = useState<{
    status: string;
    timeSeconds: number;
    imageSizeBytes: number;
  } | null>(null);

  useEffect(() => {
    fetchGpuInfo();
    fetchAvailableModels();
  }, []);

  const fetchGpuInfo = async () => {
    try {
      const res = await api.get('/config/gpu');
      setGpuInfo(res.data);
      if (res.data.recommendedMode) {
        setVramMode(res.data.recommendedMode);
      }
    } catch (e) {
      console.error('Erro ao buscar info GPU:', e);
      setGpuInfo({ available: false, error: 'Erro ao conectar com backend' });
    }
  };

  const fetchAvailableModels = async () => {
    try {
      const res = await api.get('/config/gpu/models');
      setAvailableModels(res.data);
    } catch (e) {
      console.error('Erro ao buscar modelos:', e);
    }
  };

  const loadModel = async () => {
    setLoading(true);
    setLoadingAction('loading');
    try {
      const res = await api.post(`/config/gpu/load-model?vram_mode=${vramMode}`);
      setModelInfo(res.data);
      toast.success('Modelo carregado com sucesso!');
    } catch (e: any) {
      const error = e.response?.data?.detail || 'Erro ao carregar modelo';
      toast.error(error);
      console.error('Erro ao carregar modelo:', e);
    }
    setLoading(false);
    setLoadingAction('');
  };

  const unloadModel = async () => {
    setLoading(true);
    setLoadingAction('unloading');
    try {
      await api.post('/config/gpu/unload-model');
      setModelInfo(null);
      toast.success('Modelo descarregado');
    } catch (e) {
      toast.error('Erro ao descarregar modelo');
      console.error('Erro ao descarregar modelo:', e);
    }
    setLoading(false);
    setLoadingAction('');
  };

  const testGeneration = async () => {
    setLoading(true);
    setLoadingAction('testing');
    setTestResult(null);
    try {
      const res = await api.post('/config/gpu/test-generation');
      setTestResult(res.data);
      setModelInfo(res.data.model);
      toast.success(`Imagem gerada em ${res.data.timeSeconds}s!`);
    } catch (e: any) {
      const error = e.response?.data?.detail || 'Erro no teste';
      toast.error(error);
      console.error('Erro no teste:', e);
    }
    setLoading(false);
    setLoadingAction('');
  };

  const setImageProvider = async (newProvider: 'local' | 'wavespeed') => {
    setLoading(true);
    setLoadingAction('switching');
    try {
      const res = await api.post('/config/image-provider', {
        provider: newProvider,
        vramMode: vramMode,
      });
      if (res.data.status === 'ok') {
        setProvider(newProvider);
        if (res.data.model) {
          setModelInfo(res.data.model);
        }
        toast.success(
          newProvider === 'local'
            ? 'GPU Local ativada!'
            : 'WaveSpeed API ativada'
        );
      }
    } catch (e: any) {
      const error = e.response?.data?.detail || 'Erro ao configurar provider';
      toast.error(error);
      console.error('Erro ao configurar provider:', e);
    }
    setLoading(false);
    setLoadingAction('');
  };

  const getVramModeLabel = (mode: string) => {
    const model = availableModels[mode];
    if (model) {
      return `${mode.toUpperCase()} - ${model.name} (${model.maxResolution}x${model.maxResolution})`;
    }
    switch (mode) {
      case '4gb':
        return '4GB - SDXL Turbo (512x512)';
      case '6gb':
        return '6GB - Flux Schnell (768x768)';
      case '8gb':
        return '8GB - Flux Schnell Full (1024x1024)';
      default:
        return 'Auto (Detectar)';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Cpu className="w-5 h-5" />
          Geracao de Imagens Local (GPU)
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Use sua GPU NVIDIA para gerar imagens localmente, sem custos de API
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Info da GPU */}
        <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Status da GPU
          </h3>

          {gpuInfo === null ? (
            <div className="flex items-center gap-2 text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Detectando GPU...</span>
            </div>
          ) : gpuInfo.available ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Check className="w-4 h-4 text-green-500" />
                <span className="text-green-600 dark:text-green-400 font-medium">
                  GPU Detectada
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Modelo:</span>
                  <span className="ml-2 text-gray-900 dark:text-white">{gpuInfo.name}</span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">VRAM Total:</span>
                  <span className="ml-2 text-gray-900 dark:text-white">{gpuInfo.vramTotalGb}GB</span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">VRAM Livre:</span>
                  <span className="ml-2 text-gray-900 dark:text-white">{gpuInfo.vramFreeGb}GB</span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Compute:</span>
                  <span className="ml-2 text-gray-900 dark:text-white">{gpuInfo.computeCapability}</span>
                </div>
              </div>
              <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
                <span className="text-gray-500 dark:text-gray-400">Modo Recomendado:</span>
                <span className="ml-2 text-blue-600 dark:text-blue-400 font-medium">
                  {getVramModeLabel(gpuInfo.recommendedMode || 'auto')}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <X className="w-4 h-4 text-red-500" />
              <span className="text-red-600 dark:text-red-400">
                {gpuInfo.error || 'GPU nao disponivel'}
              </span>
            </div>
          )}

          <button
            onClick={fetchGpuInfo}
            className="mt-3 text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            Atualizar
          </button>
        </div>

        {/* Seletor de Provider */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Provider de Imagens
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setImageProvider('wavespeed')}
              disabled={loading}
              className={`p-4 rounded-lg border-2 transition-all ${
                provider === 'wavespeed'
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
              } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-5 h-5 text-yellow-500" />
                <span className="font-medium text-gray-900 dark:text-white">WaveSpeed API</span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 text-left">
                Geracao na nuvem. Mais rapido, pago por uso.
              </p>
            </button>

            <button
              onClick={() => setImageProvider('local')}
              disabled={loading || !gpuInfo?.available}
              className={`p-4 rounded-lg border-2 transition-all ${
                provider === 'local'
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
              } ${loading || !gpuInfo?.available ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <div className="flex items-center gap-2 mb-2">
                <HardDrive className="w-5 h-5 text-green-500" />
                <span className="font-medium text-gray-900 dark:text-white">GPU Local</span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 text-left">
                Geracao local. Gratuito, requer GPU NVIDIA.
              </p>
            </button>
          </div>
        </div>

        {/* Configuracoes de GPU Local */}
        {provider === 'local' && gpuInfo?.available && (
          <>
            {/* Seletor de VRAM Mode */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Modo de VRAM
              </label>
              <select
                value={vramMode}
                onChange={(e) => setVramMode(e.target.value)}
                disabled={loading}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50"
              >
                <option value="auto">Auto (Detectar VRAM)</option>
                <option value="4gb">4GB - SDXL Turbo (512x512)</option>
                <option value="6gb">6GB - Flux Schnell NF4 (768x768)</option>
                <option value="8gb">8GB - Flux Schnell Full (1024x1024)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Escolha o modelo baseado na VRAM disponivel na sua GPU
              </p>
            </div>

            {/* Botoes de Acao */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={loadModel}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loadingAction === 'loading' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <HardDrive className="w-4 h-4" />
                )}
                {loadingAction === 'loading' ? 'Carregando...' : 'Carregar Modelo'}
              </button>

              <button
                onClick={testGeneration}
                disabled={loading || !modelInfo?.loaded}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loadingAction === 'testing' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Zap className="w-4 h-4" />
                )}
                {loadingAction === 'testing' ? 'Gerando...' : 'Testar Geracao'}
              </button>

              {modelInfo?.loaded && (
                <button
                  onClick={unloadModel}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loadingAction === 'unloading' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <X className="w-4 h-4" />
                  )}
                  Descarregar
                </button>
              )}
            </div>

            {/* Info do Modelo Carregado */}
            {modelInfo && (
              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Modelo Carregado
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Nome:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">{modelInfo.modelName}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Resolucao Max:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">
                      {modelInfo.maxResolution}x{modelInfo.maxResolution}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Status:</span>
                    <span
                      className={`ml-2 ${
                        modelInfo.loaded ? 'text-green-600 dark:text-green-400' : 'text-yellow-600'
                      }`}
                    >
                      {modelInfo.loaded ? 'Carregado' : 'Nao carregado'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Quantizado:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">
                      {modelInfo.quantized ? 'Sim (4-bit)' : 'Nao'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Resultado do Teste */}
            {testResult && (
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <div className="flex items-center gap-2 mb-2">
                  <Check className="w-4 h-4 text-green-500" />
                  <span className="text-green-700 dark:text-green-400 font-medium">
                    Teste bem sucedido!
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Tempo:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">
                      {testResult.timeSeconds}s
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Tamanho:</span>
                    <span className="ml-2 text-gray-900 dark:text-white">
                      {(testResult.imageSizeBytes / 1024).toFixed(1)}KB
                    </span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Nota sobre instalacao */}
        {!gpuInfo?.available && (
          <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
            <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">
              Requisitos para GPU Local
            </h4>
            <ul className="text-xs text-yellow-700 dark:text-yellow-300 space-y-1 list-disc list-inside">
              <li>GPU NVIDIA com CUDA 11.8+</li>
              <li>Minimo 4GB de VRAM</li>
              <li>PyTorch com suporte CUDA instalado</li>
              <li>Dependencias GPU: pip install -r requirements-gpu.txt</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default GpuSettings;
