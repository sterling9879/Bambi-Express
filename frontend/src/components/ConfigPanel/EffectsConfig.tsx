'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
  Upload,
  Trash2,
  Play,
  Check,
  X,
  Loader2,
  Film,
  Settings,
  Save,
} from 'lucide-react';
import { effectsApi } from '@/lib/api';
import { useApiConfig } from '@/hooks/useApiConfig';
import type { VideoEffect, EffectsConfig as EffectsConfigType, BlendMode } from '@/lib/types';
import toast from 'react-hot-toast';

export function EffectsConfig() {
  const queryClient = useQueryClient();
  const { config: fullConfig, isSaving, saveConfig } = useApiConfig();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadCategory, setUploadCategory] = useState('geral');
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewEffect, setPreviewEffect] = useState<string | null>(null);

  // Local state for effects config
  const [localConfig, setLocalConfig] = useState<EffectsConfigType>({
    enabled: false,
    effectId: undefined,
    blendMode: 'lighten',
    opacity: 1.0,
  });

  // Sync local config with full config
  useEffect(() => {
    if (fullConfig?.effects) {
      setLocalConfig(fullConfig.effects);
    }
  }, [fullConfig?.effects]);

  // Fetch effects list
  const { data: effects = [], isLoading } = useQuery({
    queryKey: ['effects'],
    queryFn: () => effectsApi.list(),
  });

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['effects-categories'],
    queryFn: () => effectsApi.getCategories(),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile || !uploadName.trim()) {
        throw new Error('Selecione um arquivo e defina um nome');
      }
      return effectsApi.upload(selectedFile, uploadName.trim(), '', uploadCategory);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['effects'] });
      queryClient.invalidateQueries({ queryKey: ['effects-categories'] });
      setShowUploadForm(false);
      setSelectedFile(null);
      setUploadName('');
      toast.success('Efeito adicionado com sucesso!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Erro ao fazer upload do efeito');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: effectsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['effects'] });
      queryClient.invalidateQueries({ queryKey: ['effects-categories'] });
      toast.success('Efeito removido');
    },
    onError: () => {
      toast.error('Erro ao remover efeito');
    },
  });

  const handleConfigChange = (newConfig: EffectsConfigType) => {
    setLocalConfig(newConfig);
  };

  const handleSave = async () => {
    if (!fullConfig) return;
    try {
      await saveConfig({ ...fullConfig, effects: localConfig });
      toast.success('Configurações de efeitos salvas!');
    } catch (error) {
      toast.error('Erro ao salvar configurações');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      if (!uploadName) {
        setUploadName(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleUpload = async () => {
    setIsUploading(true);
    try {
      await uploadMutation.mutateAsync();
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (effectId: string) => {
    if (!confirm('Tem certeza que deseja remover este efeito?')) return;

    // If deleting the selected effect, clear selection
    if (localConfig.effectId === effectId) {
      handleConfigChange({ ...localConfig, effectId: undefined, enabled: false });
    }

    deleteMutation.mutate(effectId);
  };

  const handleSelectEffect = (effect: VideoEffect) => {
    if (localConfig.effectId === effect.id) {
      // Deselect
      handleConfigChange({ ...localConfig, effectId: undefined, enabled: false });
    } else {
      // Select
      handleConfigChange({ ...localConfig, effectId: effect.id, enabled: true });
    }
  };

  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const config = localConfig;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
            <Sparkles className="w-5 h-5 mr-2" />
            Efeitos de Vídeo
          </h2>
          <div className="flex items-center space-x-2">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.enabled}
                onChange={(e) => handleConfigChange({ ...config, enabled: e.target.checked })}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Ativar efeitos</span>
            </label>
          </div>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Adicione efeitos de overlay com fundo preto aos seus vídeos
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Settings */}
        {config.enabled && (
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center">
              <Settings className="w-4 h-4 mr-2" />
              Configurações do Efeito
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Modo de Blend
                </label>
                <select
                  value={config.blendMode}
                  onChange={(e) => handleConfigChange({ ...config, blendMode: e.target.value as BlendMode })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm"
                >
                  <option value="lighten">Lighten (Clarear)</option>
                  <option value="screen">Screen (Tela)</option>
                  <option value="add">Add (Adicionar)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Define como o efeito se mistura com o vídeo
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Opacidade ({Math.round(config.opacity * 100)}%)
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={config.opacity}
                  onChange={(e) => handleConfigChange({ ...config, opacity: parseFloat(e.target.value) })}
                  className="w-full"
                />
              </div>
            </div>
          </div>
        )}

        {/* Upload Form */}
        {showUploadForm ? (
          <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Arquivo de Vídeo
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFileSelect}
                  className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                />
                {selectedFile && (
                  <p className="text-sm text-gray-500 mt-1">
                    {selectedFile.name} ({formatFileSize(selectedFile.size)})
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Nome do Efeito
                  </label>
                  <input
                    type="text"
                    value={uploadName}
                    onChange={(e) => setUploadName(e.target.value)}
                    placeholder="Ex: Partículas Douradas"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Categoria
                  </label>
                  <input
                    type="text"
                    value={uploadCategory}
                    onChange={(e) => setUploadCategory(e.target.value)}
                    placeholder="geral"
                    list="categories-list"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <datalist id="categories-list">
                    {categories.map((cat) => (
                      <option key={cat} value={cat} />
                    ))}
                  </datalist>
                </div>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setShowUploadForm(false);
                    setSelectedFile(null);
                    setUploadName('');
                  }}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleUpload}
                  disabled={isUploading || !selectedFile || !uploadName.trim()}
                  className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {isUploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4" />
                  )}
                  <span>Enviar</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowUploadForm(true)}
            className="w-full py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-gray-500 dark:text-gray-400 hover:border-primary-500 hover:text-primary-500 transition-colors flex items-center justify-center space-x-2"
          >
            <Upload className="w-5 h-5" />
            <span>Adicionar Novo Efeito</span>
          </button>
        )}

        {/* Effects List */}
        <div>
          <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
            Biblioteca de Efeitos ({effects.length})
          </h3>

          {isLoading ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-gray-400" />
            </div>
          ) : effects.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Film className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>Nenhum efeito adicionado ainda</p>
              <p className="text-sm">Adicione vídeos com fundo preto para usar como overlay</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {effects.map((effect) => (
                <div
                  key={effect.id}
                  className={`relative border-2 rounded-lg overflow-hidden cursor-pointer transition-all ${
                    config.effectId === effect.id
                      ? 'border-primary-500 ring-2 ring-primary-200'
                      : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
                  }`}
                  onClick={() => handleSelectEffect(effect)}
                >
                  {/* Thumbnail */}
                  <div className="aspect-video bg-gray-900 relative">
                    {effect.thumbnailUrl ? (
                      <img
                        src={effectsApi.getThumbnailUrl(effect.id)}
                        alt={effect.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Film className="w-8 h-8 text-gray-600" />
                      </div>
                    )}

                    {/* Selected indicator */}
                    {config.effectId === effect.id && (
                      <div className="absolute top-2 right-2 bg-primary-500 text-white rounded-full p-1">
                        <Check className="w-4 h-4" />
                      </div>
                    )}

                    {/* Preview button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setPreviewEffect(previewEffect === effect.id ? null : effect.id);
                      }}
                      className="absolute bottom-2 right-2 bg-black/70 text-white rounded-full p-1.5 hover:bg-black/90"
                    >
                      <Play className="w-3 h-3" />
                    </button>

                    {/* Duration badge */}
                    <div className="absolute bottom-2 left-2 bg-black/70 text-white text-xs px-2 py-0.5 rounded">
                      {formatDuration(effect.durationMs)}
                    </div>
                  </div>

                  {/* Info */}
                  <div className="p-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-sm text-gray-900 dark:text-white truncate">
                        {effect.name}
                      </h4>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(effect.id);
                        }}
                        className="text-gray-400 hover:text-red-500 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {effect.category} • {formatFileSize(effect.fileSize)}
                    </p>
                  </div>

                  {/* Preview Video */}
                  {previewEffect === effect.id && (
                    <div className="absolute inset-0 bg-black">
                      <video
                        src={effectsApi.getPreviewUrl(effect.id)}
                        autoPlay
                        loop
                        muted
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setPreviewEffect(null);
                        }}
                        className="absolute top-2 right-2 bg-black/70 text-white rounded-full p-1"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
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
