import { useState, useCallback, useEffect, useRef } from 'react';
import { videoApi, jobsApi } from '@/lib/api';
import type { Job, JobResult, TextAnalysis } from '@/lib/types';

interface UseVideoGenerationOptions {
  pollInterval?: number;
  onComplete?: (result: JobResult) => void;
  onError?: (error: string) => void;
}

interface UseVideoGenerationReturn {
  isGenerating: boolean;
  currentJob: Job | null;
  result: JobResult | null;
  error: string | null;
  textAnalysis: TextAnalysis | null;

  analyzeText: (text: string) => Promise<TextAnalysis>;
  startGeneration: (text: string, title?: string, channelId?: string) => Promise<void>;
  cancelGeneration: () => Promise<void>;
  reset: () => void;
}

export function useVideoGeneration(
  options: UseVideoGenerationOptions = {}
): UseVideoGenerationReturn {
  const { pollInterval = 2000, onComplete, onError } = options;

  const [isGenerating, setIsGenerating] = useState(false);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [textAnalysis, setTextAnalysis] = useState<TextAnalysis | null>(null);

  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const pollErrorCountRef = useRef<number>(0);
  const consecutiveErrorsRef = useRef<number>(0);
  const MAX_POLL_ERRORS = 30; // Aumentado para operações longas
  const MAX_CONSECUTIVE_ERRORS = 10; // Erros seguidos sem sucesso

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, []);

  const pollJobStatus = useCallback(async () => {
    if (!jobIdRef.current) return;

    try {
      const status = await jobsApi.getStatus(jobIdRef.current);
      setCurrentJob(status);
      // Reset counters on success
      consecutiveErrorsRef.current = 0;

      if (status.status === 'completed') {
        const jobResult = await jobsApi.getResult(jobIdRef.current);
        setResult(jobResult);
        setIsGenerating(false);
        onComplete?.(jobResult);
      } else if (status.status === 'failed' || status.status === 'cancelled') {
        setIsGenerating(false);
        const errorMsg = status.error || 'Job failed';
        setError(errorMsg);
        onError?.(errorMsg);
      } else {
        // Continue polling
        pollTimeoutRef.current = setTimeout(pollJobStatus, pollInterval);
      }
    } catch (err) {
      // Increment error counts
      pollErrorCountRef.current += 1;
      consecutiveErrorsRef.current += 1;

      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      const isTimeout = errorMsg.includes('ocupado') || errorMsg.includes('timeout');

      console.warn(
        `Poll error ${consecutiveErrorsRef.current}/${MAX_CONSECUTIVE_ERRORS} ` +
        `(total: ${pollErrorCountRef.current}/${MAX_POLL_ERRORS}): ${errorMsg}`
      );

      // Timeout não é erro fatal - backend ainda está trabalhando
      if (isTimeout && consecutiveErrorsRef.current < MAX_CONSECUTIVE_ERRORS) {
        // Retry com delay maior para timeout
        const backoffDelay = Math.min(5000 * consecutiveErrorsRef.current, 30000);
        console.log(`Retrying in ${backoffDelay}ms (server busy)...`);
        pollTimeoutRef.current = setTimeout(pollJobStatus, backoffDelay);
        return;
      }

      // Para erros não-timeout, usar lógica normal
      if (pollErrorCountRef.current < MAX_POLL_ERRORS && consecutiveErrorsRef.current < MAX_CONSECUTIVE_ERRORS) {
        const backoffDelay = Math.min(pollInterval * Math.pow(2, consecutiveErrorsRef.current), 15000);
        pollTimeoutRef.current = setTimeout(pollJobStatus, backoffDelay);
      } else {
        // Too many errors, stop polling
        setError(errorMsg);
        setIsGenerating(false);
        onError?.(errorMsg);
      }
    }
  }, [pollInterval, onComplete, onError]);

  const analyzeText = useCallback(async (text: string): Promise<TextAnalysis> => {
    const analysis = await videoApi.analyzeText(text);
    setTextAnalysis(analysis);
    return analysis;
  }, []);

  const startGeneration = useCallback(
    async (text: string, title?: string, channelId?: string) => {
      setIsGenerating(true);
      setError(null);
      setResult(null);
      pollErrorCountRef.current = 0;
      consecutiveErrorsRef.current = 0;

      try {
        const response = await videoApi.generate(text, title, channelId);
        jobIdRef.current = response.jobId;

        // Start polling
        pollTimeoutRef.current = setTimeout(pollJobStatus, pollInterval);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to start generation';
        setError(errorMsg);
        setIsGenerating(false);
        onError?.(errorMsg);
      }
    },
    [pollInterval, pollJobStatus, onError]
  );

  const cancelGeneration = useCallback(async () => {
    if (!jobIdRef.current) return;

    try {
      await jobsApi.cancel(jobIdRef.current);
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
      setIsGenerating(false);
    } catch (err) {
      console.error('Failed to cancel job:', err);
    }
  }, []);

  const reset = useCallback(() => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
    }
    jobIdRef.current = null;
    setIsGenerating(false);
    setCurrentJob(null);
    setResult(null);
    setError(null);
    setTextAnalysis(null);
  }, []);

  return {
    isGenerating,
    currentJob,
    result,
    error,
    textAnalysis,
    analyzeText,
    startGeneration,
    cancelGeneration,
    reset,
  };
}
