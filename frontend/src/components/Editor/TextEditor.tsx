'use client';

import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Play, FileText, Clock, Hash, FolderOpen } from 'lucide-react';
import { channelsApi } from '@/lib/api';
import type { TextAnalysis } from '@/lib/types';

interface TextEditorProps {
  onAnalyze: (text: string) => Promise<TextAnalysis>;
  onGenerate: (text: string, title?: string, channelId?: string) => Promise<void>;
  textAnalysis: TextAnalysis | null;
  isGenerating: boolean;
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

export function TextEditor({
  onAnalyze,
  onGenerate,
  textAnalysis,
  isGenerating,
}: TextEditorProps) {
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const { data: channels = [] } = useQuery({
    queryKey: ['channels'],
    queryFn: channelsApi.list,
  });

  // Debounce analysis
  useEffect(() => {
    if (!text.trim()) return;

    const timer = setTimeout(async () => {
      setIsAnalyzing(true);
      try {
        await onAnalyze(text);
      } catch (error) {
        console.error('Analysis error:', error);
      } finally {
        setIsAnalyzing(false);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [text, onAnalyze]);

  const handleGenerate = useCallback(async () => {
    if (!text.trim() || isGenerating) return;
    await onGenerate(
      text,
      title.trim() || undefined,
      selectedChannel || undefined
    );
  }, [text, title, selectedChannel, isGenerating, onGenerate]);

  const charCount = text.length;
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
          <FileText className="w-5 h-5 mr-2" />
          Texto do Vídeo
        </h2>
      </div>

      <div className="p-6 space-y-4">
        {/* Title and Channel */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Título do Vídeo (opcional)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Dicas de Produtividade"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              <span className="flex items-center space-x-1">
                <FolderOpen className="w-4 h-4" />
                <span>Canal (opcional)</span>
              </span>
            </label>
            <select
              value={selectedChannel}
              onChange={(e) => setSelectedChannel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">Sem canal</option>
              {channels.map((channel) => (
                <option key={channel.id} value={channel.id}>
                  {channel.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Text area */}
        <div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Digite ou cole o texto que será narrado...

O sistema irá:
• Dividir em cenas automaticamente
• Gerar narração com a voz selecionada
• Criar imagens para cada cena
• Adicionar música de fundo"
            rows={12}
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
          />
        </div>

        {/* Stats */}
        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center space-x-1">
            <Hash className="w-4 h-4" />
            <span>Caracteres: {charCount.toLocaleString()}</span>
          </div>
          <div className="flex items-center space-x-1">
            <FileText className="w-4 h-4" />
            <span>Palavras: {wordCount.toLocaleString()}</span>
          </div>
          {textAnalysis && (
            <>
              <div className="flex items-center space-x-1">
                <Clock className="w-4 h-4" />
                <span>Estimativa: {formatDuration(textAnalysis.estimatedDurationSeconds)}</span>
              </div>
              <div className="flex items-center space-x-1">
                <span>~{textAnalysis.estimatedChunks} chunks</span>
              </div>
            </>
          )}
          {isAnalyzing && (
            <span className="text-primary-600 animate-pulse">Analisando...</span>
          )}
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={!text.trim() || isGenerating}
          className="w-full flex items-center justify-center space-x-2 px-6 py-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-lg font-medium"
        >
          <Play className="w-6 h-6" />
          <span>{isGenerating ? 'Gerando...' : 'GERAR VÍDEO'}</span>
        </button>

        {/* Tips */}
        <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
          <p>Dicas para melhores resultados:</p>
          <ul className="list-disc list-inside space-y-0.5 ml-2">
            <li>Use parágrafos para separar ideias diferentes</li>
            <li>Evite frases muito longas</li>
            <li>Use pontuação para dar ritmo à narração</li>
            <li>Máximo recomendado: 5.000 palavras por vídeo</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
