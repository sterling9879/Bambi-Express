'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Trash2,
  Play,
  Pause,
  Square,
  Download,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Upload,
  List,
  Folder,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { batchApi, channelsApi } from '@/lib/api';
import type {
  Batch,
  BatchListItem,
  BatchAnalysis,
  BatchCreateItem,
  BatchStatus,
  BatchItemStatus,
} from '@/lib/types';

type ViewMode = 'create' | 'list' | 'details';

interface ScriptInput {
  id: string;
  title: string;
  text: string;
}

export function BatchPanel() {
  const [viewMode, setViewMode] = useState<ViewMode>('create');
  const [scripts, setScripts] = useState<ScriptInput[]>([
    { id: '1', title: '', text: '' },
  ]);
  const [batchName, setBatchName] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<string>('');
  const [analysis, setAnalysis] = useState<BatchAnalysis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // List view state
  const [batches, setBatches] = useState<BatchListItem[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);

  // Details view state
  const [currentBatch, setCurrentBatch] = useState<Batch | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Fetch channels
  const { data: channels = [] } = useQuery({
    queryKey: ['channels'],
    queryFn: channelsApi.list,
  });

  // Load batches list
  const loadBatches = useCallback(async () => {
    setIsLoadingList(true);
    try {
      const response = await batchApi.list({ limit: 20 });
      setBatches(response.batches);
    } catch (err) {
      console.error('Failed to load batches:', err);
    } finally {
      setIsLoadingList(false);
    }
  }, []);

  // Load batch details
  const loadBatchDetails = useCallback(async (batchId: string) => {
    setIsLoadingDetails(true);
    try {
      const batch = await batchApi.getStatus(batchId);
      setCurrentBatch(batch);
    } catch (err) {
      console.error('Failed to load batch details:', err);
    } finally {
      setIsLoadingDetails(false);
    }
  }, []);

  // Poll for updates when viewing a processing batch
  useEffect(() => {
    if (viewMode !== 'details' || !currentBatch) return;

    const isActive = ['pending', 'processing', 'paused'].includes(currentBatch.status);
    if (!isActive) return;

    const interval = setInterval(() => {
      loadBatchDetails(currentBatch.batchId);
    }, 2000);

    return () => clearInterval(interval);
  }, [viewMode, currentBatch, loadBatchDetails]);

  // Load list when switching to list view
  useEffect(() => {
    if (viewMode === 'list') {
      loadBatches();
    }
  }, [viewMode, loadBatches]);

  // Add new script input
  const addScript = () => {
    setScripts([
      ...scripts,
      { id: Date.now().toString(), title: '', text: '' },
    ]);
    setAnalysis(null);
  };

  // Remove script input
  const removeScript = (id: string) => {
    if (scripts.length <= 1) return;
    setScripts(scripts.filter((s) => s.id !== id));
    setAnalysis(null);
  };

  // Update script
  const updateScript = (id: string, field: 'title' | 'text', value: string) => {
    setScripts(
      scripts.map((s) => (s.id === id ? { ...s, [field]: value } : s))
    );
    setAnalysis(null);
  };

  // Analyze batch
  const handleAnalyze = async () => {
    const validScripts = scripts.filter((s) => s.text.trim());
    if (validScripts.length === 0) {
      setError('Adicione pelo menos um roteiro com texto');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const items: BatchCreateItem[] = validScripts.map((s, idx) => ({
        title: s.title.trim() || `Roteiro ${idx + 1}`,
        text: s.text.trim(),
      }));

      const result = await batchApi.analyze(batchName || 'Batch', items);
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao analisar roteiros');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Create and start batch
  const handleCreate = async () => {
    const validScripts = scripts.filter((s) => s.text.trim());
    if (validScripts.length === 0) {
      setError('Adicione pelo menos um roteiro com texto');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const items: BatchCreateItem[] = validScripts.map((s, idx) => ({
        title: s.title.trim() || `Roteiro ${idx + 1}`,
        text: s.text.trim(),
      }));

      const name = batchName.trim() || `Batch ${new Date().toLocaleDateString()}`;
      const result = await batchApi.create(name, items, selectedChannel || undefined);

      // Switch to details view
      setViewMode('details');
      loadBatchDetails(result.batchId);

      // Reset form
      setScripts([{ id: '1', title: '', text: '' }]);
      setBatchName('');
      setSelectedChannel('');
      setAnalysis(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao criar batch');
    } finally {
      setIsCreating(false);
    }
  };

  // Batch actions
  const handlePause = async () => {
    if (!currentBatch) return;
    try {
      await batchApi.pause(currentBatch.batchId);
      loadBatchDetails(currentBatch.batchId);
    } catch (err) {
      console.error('Failed to pause batch:', err);
    }
  };

  const handleResume = async () => {
    if (!currentBatch) return;
    try {
      await batchApi.resume(currentBatch.batchId);
      loadBatchDetails(currentBatch.batchId);
    } catch (err) {
      console.error('Failed to resume batch:', err);
    }
  };

  const handleCancel = async () => {
    if (!currentBatch) return;
    try {
      await batchApi.cancel(currentBatch.batchId);
      loadBatchDetails(currentBatch.batchId);
    } catch (err) {
      console.error('Failed to cancel batch:', err);
    }
  };

  const handleDelete = async (batchId: string) => {
    if (!confirm('Tem certeza que deseja excluir este batch e todos os vídeos?')) {
      return;
    }
    try {
      await batchApi.delete(batchId);
      if (viewMode === 'details') {
        setViewMode('list');
        setCurrentBatch(null);
      }
      loadBatches();
    } catch (err) {
      console.error('Failed to delete batch:', err);
    }
  };

  // Status helpers
  const getStatusIcon = (status: BatchStatus | BatchItemStatus) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-400" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'paused':
        return <Pause className="w-4 h-4 text-yellow-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'cancelled':
      case 'skipped':
        return <AlertCircle className="w-4 h-4 text-gray-400" />;
      default:
        return null;
    }
  };

  const getStatusLabel = (status: BatchStatus | BatchItemStatus) => {
    const labels: Record<string, string> = {
      pending: 'Aguardando',
      processing: 'Processando',
      paused: 'Pausado',
      completed: 'Concluído',
      failed: 'Falhou',
      cancelled: 'Cancelado',
      skipped: 'Pulado',
    };
    return labels[status] || status;
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      {/* View Mode Tabs */}
      <div className="flex space-x-2">
        <button
          onClick={() => setViewMode('create')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
            viewMode === 'create'
              ? 'bg-primary-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          <Plus className="w-4 h-4" />
          <span>Criar Batch</span>
        </button>
        <button
          onClick={() => setViewMode('list')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
            viewMode === 'list'
              ? 'bg-primary-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
        >
          <List className="w-4 h-4" />
          <span>Meus Batches</span>
        </button>
      </div>

      {/* Create View */}
      {viewMode === 'create' && (
        <div className="space-y-6">
          {/* Batch Name and Channel */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Nome do Batch
                </label>
                <input
                  type="text"
                  value={batchName}
                  onChange={(e) => setBatchName(e.target.value)}
                  placeholder="Ex: Vídeos de Janeiro"
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  <div className="flex items-center space-x-1">
                    <Folder className="w-4 h-4" />
                    <span>Canal</span>
                  </div>
                </label>
                <select
                  value={selectedChannel}
                  onChange={(e) => setSelectedChannel(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">Sem canal (padrão)</option>
                  {channels.map((channel) => (
                    <option key={channel.id} value={channel.id}>
                      {channel.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Organiza os vídeos gerados por canal
                </p>
              </div>
            </div>
          </div>

          {/* Scripts */}
          <div className="space-y-4">
            {scripts.map((script, index) => (
              <div
                key={script.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    Roteiro {index + 1}
                  </h3>
                  {scripts.length > 1 && (
                    <button
                      onClick={() => removeScript(script.id)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  )}
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Título
                    </label>
                    <input
                      type="text"
                      value={script.title}
                      onChange={(e) => updateScript(script.id, 'title', e.target.value)}
                      placeholder="Título do vídeo (opcional)"
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Roteiro
                    </label>
                    <textarea
                      value={script.text}
                      onChange={(e) => updateScript(script.id, 'text', e.target.value)}
                      placeholder="Cole o roteiro aqui..."
                      rows={6}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-y"
                    />
                    {script.text && (
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        {script.text.length.toLocaleString()} caracteres
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}

            <button
              onClick={addScript}
              className="w-full py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-gray-500 dark:text-gray-400 hover:border-primary-500 hover:text-primary-500 transition-colors flex items-center justify-center space-x-2"
            >
              <Plus className="w-5 h-5" />
              <span>Adicionar Roteiro</span>
            </button>
          </div>

          {/* Analysis Results */}
          {analysis && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Análise do Batch
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <p className="text-2xl font-bold text-primary-600">{analysis.totalItems}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Roteiros</p>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <p className="text-2xl font-bold text-primary-600">
                    {analysis.totalCharacters.toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Caracteres</p>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <p className="text-2xl font-bold text-primary-600">
                    {formatDuration(analysis.estimatedTotalDurationSeconds)}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Duração Total</p>
                </div>
                <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <p className="text-2xl font-bold text-primary-600">
                    ~{Math.ceil(analysis.estimatedProcessingTimeMinutes)} min
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Tempo Estimado</p>
                </div>
              </div>

              <div className="space-y-2">
                {analysis.itemsAnalysis.map((item) => (
                  <div
                    key={item.index}
                    className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded"
                  >
                    <span className="text-sm text-gray-900 dark:text-white">
                      {item.title}
                    </span>
                    {item.error ? (
                      <span className="text-sm text-red-500">{item.error}</span>
                    ) : (
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {item.charCount?.toLocaleString()} chars | ~{formatDuration(item.estimatedDurationSeconds || 0)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex space-x-4">
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing || isCreating}
              className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
            >
              {isAnalyzing ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <FileText className="w-5 h-5" />
              )}
              <span>Analisar</span>
            </button>
            <button
              onClick={handleCreate}
              disabled={isAnalyzing || isCreating}
              className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
            >
              {isCreating ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Play className="w-5 h-5" />
              )}
              <span>Iniciar Batch</span>
            </button>
          </div>
        </div>
      )}

      {/* List View */}
      {viewMode === 'list' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          {isLoadingList ? (
            <div className="p-8 text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-600" />
              <p className="mt-2 text-gray-500 dark:text-gray-400">Carregando...</p>
            </div>
          ) : batches.length === 0 ? (
            <div className="p-8 text-center">
              <Upload className="w-12 h-12 mx-auto text-gray-400" />
              <p className="mt-2 text-gray-500 dark:text-gray-400">
                Nenhum batch encontrado
              </p>
              <button
                onClick={() => setViewMode('create')}
                className="mt-4 text-primary-600 hover:text-primary-700"
              >
                Criar primeiro batch
              </button>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {batches.map((batch) => (
                <div
                  key={batch.batchId}
                  className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                  onClick={() => {
                    setViewMode('details');
                    loadBatchDetails(batch.batchId);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(batch.status)}
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white">
                          {batch.name}
                        </h4>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {batch.completedItems}/{batch.totalItems} vídeos |{' '}
                          {getStatusLabel(batch.status)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="w-32 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full transition-all"
                          style={{ width: `${batch.progress}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-500 dark:text-gray-400 w-12 text-right">
                        {Math.round(batch.progress)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Details View */}
      {viewMode === 'details' && currentBatch && (
        <div className="space-y-6">
          {/* Back button */}
          <button
            onClick={() => {
              setViewMode('list');
              setCurrentBatch(null);
            }}
            className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          >
            &larr; Voltar para lista
          </button>

          {/* Batch Info */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                {getStatusIcon(currentBatch.status)}
                <div>
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                    {currentBatch.name}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {getStatusLabel(currentBatch.status)}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex space-x-2">
                {currentBatch.status === 'processing' && (
                  <button
                    onClick={handlePause}
                    className="flex items-center space-x-1 px-3 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
                  >
                    <Pause className="w-4 h-4" />
                    <span>Pausar</span>
                  </button>
                )}
                {currentBatch.status === 'paused' && (
                  <button
                    onClick={handleResume}
                    className="flex items-center space-x-1 px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                  >
                    <Play className="w-4 h-4" />
                    <span>Retomar</span>
                  </button>
                )}
                {['pending', 'processing', 'paused'].includes(currentBatch.status) && (
                  <button
                    onClick={handleCancel}
                    className="flex items-center space-x-1 px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                  >
                    <Square className="w-4 h-4" />
                    <span>Cancelar</span>
                  </button>
                )}
                <button
                  onClick={() => handleDelete(currentBatch.batchId)}
                  className="flex items-center space-x-1 px-3 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Excluir</span>
                </button>
              </div>
            </div>

            {/* Progress */}
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-500 dark:text-gray-400">
                  {currentBatch.completedItems} de {currentBatch.totalItems} concluídos
                  {currentBatch.failedItems > 0 && (
                    <span className="text-red-500 ml-2">
                      ({currentBatch.failedItems} falhas)
                    </span>
                  )}
                </span>
                <span className="text-gray-900 dark:text-white font-medium">
                  {Math.round(currentBatch.progress)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-3">
                <div
                  className="bg-primary-600 h-3 rounded-full transition-all"
                  style={{ width: `${currentBatch.progress}%` }}
                />
              </div>
            </div>

            {/* Current item */}
            {currentBatch.currentItemTitle && (
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  Processando: <strong>{currentBatch.currentItemTitle}</strong>
                </p>
                {currentBatch.currentItemStep && (
                  <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                    {currentBatch.currentItemStep}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Items List */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-medium text-gray-900 dark:text-white">
                Roteiros ({currentBatch.items.length})
              </h3>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {currentBatch.items.map((item, index) => (
                <div key={item.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(item.status)}
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white">
                          {item.title}
                        </h4>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {item.currentStep}
                          {item.durationSeconds && (
                            <span className="ml-2">
                              | Processado em {Math.round(item.durationSeconds)}s
                            </span>
                          )}
                        </p>
                        {item.error && (
                          <p className="text-sm text-red-500 mt-1">{item.error}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-4">
                      {item.status === 'processing' && (
                        <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all"
                            style={{ width: `${item.progress * 100}%` }}
                          />
                        </div>
                      )}
                      {item.status === 'completed' && item.videoPath && (
                        <a
                          href={batchApi.getItemDownloadUrl(currentBatch.batchId, index)}
                          className="flex items-center space-x-1 px-3 py-1 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Download className="w-4 h-4" />
                          <span>Download</span>
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
