import { useCallback, useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configApi } from '@/lib/api';
import { useConfigStore } from '@/stores/configStore';
import type { FullConfig, ApiTestResult, CreditsResponse, Voice, MinimaxVoice } from '@/lib/types';

export function useApiConfig() {
  const queryClient = useQueryClient();
  const { config, setConfig, setLoading, setError } = useConfigStore();

  // Fetch config
  const {
    data: fetchedConfig,
    isLoading,
    error: fetchError,
  } = useQuery({
    queryKey: ['config'],
    queryFn: configApi.get,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Update store when config is fetched
  useEffect(() => {
    if (fetchedConfig) {
      setConfig(fetchedConfig);
    }
  }, [fetchedConfig, setConfig]);

  useEffect(() => {
    setLoading(isLoading);
  }, [isLoading, setLoading]);

  useEffect(() => {
    if (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Failed to fetch config');
    }
  }, [fetchError, setError]);

  // Save config mutation
  const saveMutation = useMutation({
    mutationFn: configApi.update,
    onSuccess: (data) => {
      setConfig(data);
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
    onError: (error) => {
      setError(error instanceof Error ? error.message : 'Failed to save config');
    },
  });

  // Test API connection
  const [testingApi, setTestingApi] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ApiTestResult>>({});

  const testApi = useCallback(async (apiName: string): Promise<ApiTestResult> => {
    setTestingApi(apiName);
    try {
      const result = await configApi.testApi(apiName);
      setTestResults((prev) => ({ ...prev, [apiName]: result }));
      return result;
    } finally {
      setTestingApi(null);
    }
  }, []);

  // Get credits
  const {
    data: credits,
    refetch: refetchCredits,
  } = useQuery({
    queryKey: ['credits'],
    queryFn: configApi.getCredits,
    staleTime: 60 * 1000, // 1 minute
    enabled: !!config?.api?.elevenlabs?.apiKey || !!config?.api?.wavespeed?.apiKey,
  });

  // Get voices
  const {
    data: voices,
    refetch: refetchVoices,
  } = useQuery({
    queryKey: ['voices'],
    queryFn: configApi.getVoices,
    staleTime: 5 * 60 * 1000,
    enabled: !!config?.api?.elevenlabs?.apiKey,
  });

  // Get Minimax voices
  const {
    data: minimaxVoices,
  } = useQuery({
    queryKey: ['minimaxVoices'],
    queryFn: configApi.getMinimaxVoices,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - static data
  });

  // Get Minimax emotions
  const {
    data: minimaxEmotions,
  } = useQuery({
    queryKey: ['minimaxEmotions'],
    queryFn: configApi.getMinimaxEmotions,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - static data
  });

  const saveConfig = useCallback(
    async (newConfig: FullConfig) => {
      await saveMutation.mutateAsync(newConfig);
    },
    [saveMutation]
  );

  return {
    config: config || fetchedConfig,
    isLoading,
    isSaving: saveMutation.isPending,
    error: fetchError,
    saveConfig,
    testApi,
    testingApi,
    testResults,
    credits,
    refetchCredits,
    voices: voices || [],
    refetchVoices,
    minimaxVoices: minimaxVoices || [],
    minimaxEmotions: minimaxEmotions || [],
  };
}
