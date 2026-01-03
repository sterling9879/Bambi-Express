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
  startGeneration: (text: string) => Promise<void>;
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
      const errorMsg = err instanceof Error ? err.message : 'Failed to get job status';
      setError(errorMsg);
      setIsGenerating(false);
      onError?.(errorMsg);
    }
  }, [pollInterval, onComplete, onError]);

  const analyzeText = useCallback(async (text: string): Promise<TextAnalysis> => {
    const analysis = await videoApi.analyzeText(text);
    setTextAnalysis(analysis);
    return analysis;
  }, []);

  const startGeneration = useCallback(
    async (text: string) => {
      setIsGenerating(true);
      setError(null);
      setResult(null);

      try {
        const response = await videoApi.generate(text);
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
