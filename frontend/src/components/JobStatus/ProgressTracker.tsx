'use client';

import { useEffect, useRef, useState } from 'react';
import { Check, Loader2, Clock, XCircle, Terminal, ChevronDown, ChevronUp } from 'lucide-react';
import type { Job } from '@/lib/types';

interface ProgressTrackerProps {
  job: Job | null;
  onCancel: () => void;
}

const STEPS = [
  { key: 'processing_text', label: 'Processando texto', activeLabel: 'Processando texto...' },
  { key: 'generating_audio', label: 'Gerando áudio', activeLabel: 'Gerando áudio...' },
  { key: 'merging_audio', label: 'Concatenando áudio', activeLabel: 'Concatenando áudio...' },
  { key: 'transcribing', label: 'Transcrevendo', activeLabel: 'Transcrevendo áudio...' },
  { key: 'analyzing_scenes', label: 'Analisando cenas', activeLabel: 'Analisando cenas...' },
  { key: 'selecting_music', label: 'Selecionando música', activeLabel: 'Selecionando música...' },
  { key: 'generating_images', label: 'Gerando imagens', activeLabel: 'Gerando imagens...' },
  { key: 'mixing_audio', label: 'Mixando áudio', activeLabel: 'Mixando áudio...' },
  { key: 'composing_video', label: 'Montando vídeo', activeLabel: 'Montando vídeo...' },
];

function getStepIndex(status: string): number {
  const index = STEPS.findIndex((s) => s.key === status);
  return index >= 0 ? index : -1;
}

export function ProgressTracker({ job, onCancel }: ProgressTrackerProps) {
  const [showLogs, setShowLogs] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    if (showLogs && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [job?.logs, showLogs]);

  if (!job) {
    return null;
  }

  const currentStepIndex = getStepIndex(job.status);
  const progressPercent = Math.round(job.progress * 100);
  const logs = job.logs || [];

  const getStepStatus = (index: number) => {
    if (job.status === 'completed') return 'completed';
    if (job.status === 'failed') return index <= currentStepIndex ? 'failed' : 'pending';
    if (index < currentStepIndex) return 'completed';
    if (index === currentStepIndex) return 'active';
    return 'pending';
  };

  const getStepDetails = (step: typeof STEPS[0], index: number) => {
    if (index !== currentStepIndex) return null;

    const details = job.details;
    if (!details) return null;

    if (step.key === 'generating_audio' && details.chunks_completed !== undefined) {
      return `${details.chunks_completed}/${details.chunks_total}`;
    }
    if (step.key === 'generating_images' && details.images_completed !== undefined) {
      return `${details.images_completed}/${details.images_total}`;
    }
    return null;
  };

  const getLogColor = (log: string) => {
    if (log.includes('ERROR') || log.includes('error') || log.includes('Error') || log.includes('failed') || log.includes('Failed')) {
      return 'text-red-400';
    }
    if (log.includes('WARNING') || log.includes('warning') || log.includes('Warning') || log.includes('retry') || log.includes('Retry')) {
      return 'text-yellow-400';
    }
    if (log.includes('SUCCESS') || log.includes('success') || log.includes('Successfully') || log.includes('completed') || log.includes('Generated')) {
      return 'text-green-400';
    }
    return 'text-gray-300';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Gerando Vídeo
        </h3>
      </div>

      <div className="p-6 space-y-6">
        {/* Progress bar */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-600 dark:text-gray-400">Progresso geral</span>
            <span className="text-gray-900 dark:text-white font-medium">{progressPercent}%</span>
          </div>
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-600 rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {STEPS.map((step, index) => {
            const status = getStepStatus(index);
            const details = getStepDetails(step, index);

            return (
              <div key={step.key} className="flex items-center space-x-3">
                {/* Icon */}
                <div
                  className={`w-6 h-6 flex items-center justify-center rounded-full flex-shrink-0 ${
                    status === 'completed'
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                      : status === 'active'
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                      : status === 'failed'
                      ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-400'
                  }`}
                >
                  {status === 'completed' ? (
                    <Check className="w-4 h-4" />
                  ) : status === 'active' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : status === 'failed' ? (
                    <XCircle className="w-4 h-4" />
                  ) : (
                    <Clock className="w-4 h-4" />
                  )}
                </div>

                {/* Label */}
                <div className="flex-1">
                  <span
                    className={`${
                      status === 'completed'
                        ? 'text-green-600 dark:text-green-400'
                        : status === 'active'
                        ? 'text-gray-900 dark:text-white font-medium'
                        : status === 'failed'
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-gray-400'
                    }`}
                  >
                    {status === 'active' ? step.activeLabel : step.label}
                  </span>
                </div>

                {/* Details */}
                {details && (
                  <span className="text-sm text-gray-500">({details})</span>
                )}
              </div>
            );
          })}
        </div>

        {/* Logs Section */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Logs ({logs.length})
              </span>
            </div>
            {showLogs ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>

          {showLogs && (
            <div className="bg-gray-900 p-3 max-h-64 overflow-y-auto font-mono text-xs">
              {logs.length === 0 ? (
                <p className="text-gray-500">Aguardando logs...</p>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className={`${getLogColor(log)} py-0.5`}>
                    {log}
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>

        {/* Error message */}
        {job.status === 'failed' && job.error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-red-700 dark:text-red-300 text-sm font-medium">Erro:</p>
            <p className="text-red-700 dark:text-red-300 text-sm mt-1">{job.error}</p>
          </div>
        )}

        {/* Cancel button */}
        {job.status !== 'completed' && job.status !== 'failed' && (
          <button
            onClick={onCancel}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            Cancelar
          </button>
        )}
      </div>
    </div>
  );
}
