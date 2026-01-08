'use client';

import { useState } from 'react';
import { Settings, Music, Video, FileText, History, Cpu } from 'lucide-react';
import { ApiConfig } from '@/components/ConfigPanel/ApiConfig';
import { MusicConfig } from '@/components/ConfigPanel/MusicConfig';
import { FFmpegConfig } from '@/components/ConfigPanel/FFmpegConfig';
import { GpuSettings } from '@/components/GpuSettings';
import { MusicUploader } from '@/components/MusicLibrary/MusicUploader';
import { MusicList } from '@/components/MusicLibrary/MusicList';
import { TextEditor } from '@/components/Editor/TextEditor';
import { ProgressTracker } from '@/components/JobStatus/ProgressTracker';
import { HistoryPanel } from '@/components/History';
import { useVideoGeneration } from '@/hooks/useVideoGeneration';
import { ErrorBoundary } from '@/components/ErrorBoundary';

type Tab = 'editor' | 'config' | 'music' | 'history';

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('editor');
  const [configSection, setConfigSection] = useState<'api' | 'gpu' | 'music' | 'ffmpeg'>('api');

  const {
    isGenerating,
    currentJob,
    result,
    error,
    textAnalysis,
    analyzeText,
    startGeneration,
    cancelGeneration,
    reset,
  } = useVideoGeneration({
    onComplete: (result) => {
      console.log('Video completed:', result);
    },
    onError: (error) => {
      console.error('Video generation error:', error);
    },
  });

  const tabs = [
    { id: 'editor' as Tab, label: 'Editor', icon: FileText },
    { id: 'history' as Tab, label: 'Histórico', icon: History },
    { id: 'config' as Tab, label: 'Configurações', icon: Settings },
    { id: 'music' as Tab, label: 'Músicas', icon: Music },
  ];

  return (
    <main className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Video className="w-8 h-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Video Generator
              </h1>
            </div>
            <div className="flex items-center space-x-2">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Editor Tab */}
        {activeTab === 'editor' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-6">
              <TextEditor
                onAnalyze={analyzeText}
                onGenerate={startGeneration}
                textAnalysis={textAnalysis}
                isGenerating={isGenerating}
              />
            </div>
            <div className="space-y-6">
              {(isGenerating || currentJob) && (
                <ProgressTracker
                  job={currentJob}
                  onCancel={cancelGeneration}
                />
              )}
              {result && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Vídeo Gerado
                  </h3>
                  <div className="space-y-4">
                    {result.videoUrl && (
                      <video
                        src={result.videoUrl}
                        controls
                        className="w-full rounded-lg"
                      />
                    )}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Duração:</span>
                        <span className="ml-2 text-gray-900 dark:text-white">
                          {result.durationSeconds?.toFixed(1)}s
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Cenas:</span>
                        <span className="ml-2 text-gray-900 dark:text-white">
                          {result.scenesCount}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Tamanho:</span>
                        <span className="ml-2 text-gray-900 dark:text-white">
                          {((result.fileSize || 0) / 1024 / 1024).toFixed(1)} MB
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Tempo:</span>
                        <span className="ml-2 text-gray-900 dark:text-white">
                          {result.processingTimeSeconds?.toFixed(1)}s
                        </span>
                      </div>
                    </div>
                    {result.videoUrl && (
                      <a
                        href={result.videoUrl}
                        download
                        className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                      >
                        Download
                      </a>
                    )}
                  </div>
                </div>
              )}
              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                  <h3 className="text-red-800 dark:text-red-200 font-medium">Erro</h3>
                  <p className="text-red-700 dark:text-red-300 mt-1">{error}</p>
                  <button
                    onClick={reset}
                    className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
                  >
                    Tentar novamente
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Config Tab */}
        {activeTab === 'config' && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            <div className="lg:col-span-1">
              <nav className="space-y-2">
                {[
                  { id: 'api' as const, label: 'APIs', icon: Settings },
                  { id: 'gpu' as const, label: 'GPU Local', icon: Cpu },
                  { id: 'music' as const, label: 'Música', icon: Music },
                  { id: 'ffmpeg' as const, label: 'Vídeo', icon: Video },
                ].map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setConfigSection(item.id)}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                      configSection === item.id
                        ? 'bg-primary-600 text-white'
                        : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <item.icon className="w-5 h-5" />
                    <span>{item.label}</span>
                  </button>
                ))}
              </nav>
            </div>
            <div className="lg:col-span-3">
              <ErrorBoundary>
                {configSection === 'api' && <ApiConfig />}
                {configSection === 'gpu' && <GpuSettings />}
                {configSection === 'music' && <MusicConfig />}
                {configSection === 'ffmpeg' && <FFmpegConfig />}
              </ErrorBoundary>
            </div>
          </div>
        )}

        {/* Music Tab */}
        {activeTab === 'music' && (
          <div className="space-y-8">
            <MusicUploader />
            <MusicList />
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <ErrorBoundary>
            <HistoryPanel />
          </ErrorBoundary>
        )}
      </div>
    </main>
  );
}
