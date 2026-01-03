import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { musicApi } from '@/lib/api';
import type { MusicTrack, MusicMood } from '@/lib/types';

interface UseMusicLibraryOptions {
  mood?: MusicMood;
  search?: string;
  page?: number;
  limit?: number;
}

export function useMusicLibrary(options: UseMusicLibraryOptions = {}) {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(options.page || 1);
  const [search, setSearch] = useState(options.search || '');
  const [moodFilter, setMoodFilter] = useState<MusicMood | undefined>(options.mood);

  // Fetch tracks
  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['music', { mood: moodFilter, search, page, limit: options.limit || 20 }],
    queryFn: () =>
      musicApi.list({
        mood: moodFilter,
        search: search || undefined,
        page,
        limit: options.limit || 20,
      }),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: ({
      file,
      mood,
      tags,
    }: {
      file: File;
      mood: MusicMood;
      tags?: string[];
    }) => musicApi.upload(file, mood, tags),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['music'] });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({
      trackId,
      updates,
    }: {
      trackId: string;
      updates: Partial<MusicTrack>;
    }) => musicApi.update(trackId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['music'] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (trackId: string) => musicApi.delete(trackId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['music'] });
    },
  });

  // Get waveform
  const getWaveform = useCallback(async (trackId: string): Promise<number[]> => {
    return musicApi.getWaveform(trackId);
  }, []);

  // Get preview URL
  const getPreviewUrl = useCallback((trackId: string): string => {
    return musicApi.getPreviewUrl(trackId);
  }, []);

  // Upload file
  const uploadFile = useCallback(
    async (file: File, mood: MusicMood, tags?: string[]) => {
      return uploadMutation.mutateAsync({ file, mood, tags });
    },
    [uploadMutation]
  );

  // Update track
  const updateTrack = useCallback(
    async (trackId: string, updates: Partial<MusicTrack>) => {
      return updateMutation.mutateAsync({ trackId, updates });
    },
    [updateMutation]
  );

  // Delete track
  const deleteTrack = useCallback(
    async (trackId: string) => {
      return deleteMutation.mutateAsync(trackId);
    },
    [deleteMutation]
  );

  return {
    tracks: data?.tracks || [],
    total: data?.total || 0,
    page,
    setPage,
    search,
    setSearch,
    moodFilter,
    setMoodFilter,
    isLoading,
    error,
    refetch,
    uploadFile,
    isUploading: uploadMutation.isPending,
    updateTrack,
    isUpdating: updateMutation.isPending,
    deleteTrack,
    isDeleting: deleteMutation.isPending,
    getWaveform,
    getPreviewUrl,
  };
}
