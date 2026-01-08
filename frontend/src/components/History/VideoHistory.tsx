'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Video,
  Download,
  Trash2,
  Clock,
  Film,
  HardDrive,
  FolderOpen,
  ChevronDown,
  Play,
  AlertCircle,
  RefreshCw
} from 'lucide-react';
import { historyApi, channelsApi } from '@/lib/api';
import type { VideoHistory as VideoHistoryType, Channel } from '@/lib/types';

export function VideoHistory() {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null);
  const [expandedVideo, setExpandedVideo] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: channels = [], isError: channelsError, refetch: refetchChannels } = useQuery({
    queryKey: ['channels'],
    queryFn: channelsApi.list,
  });

  const { data: videosData, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['videos', selectedChannel],
    queryFn: () => historyApi.listVideos({
      channelId: selectedChannel || undefined,
      limit: 50
    }),
  });

  const deleteMutation = useMutation({
    mutationFn: historyApi.deleteVideo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      queryClient.invalidateQueries({ queryKey: ['history-stats'] });
    },
  });

  const videos = videosData?.videos || [];

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const handleDelete = (videoId: string) => {
    if (confirm('Tem certeza que deseja excluir este vídeo?')) {
      deleteMutation.mutate(videoId);
    }
  };

  return (
    <div className="space-y-6">
      {/* Channel Filter */}
      <div className="flex items-center space-x-4">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Filtrar por canal:
        </label>
        <select
          value={selectedChannel || ''}
          onChange={(e) => setSelectedChannel(e.target.value || null)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="">Todos os canais</option>
          {channels.map((channel) => (
            <option key={channel.id} value={channel.id}>
              {channel.name} ({channel.videoCount})
            </option>
          ))}
        </select>
      </div>

      {/* Videos List */}
      {isError ? (
        <div className="text-center py-12">
          <AlertCircle className="w-16 h-16 mx-auto text-red-400 mb-4" />
          <p className="text-red-500 dark:text-red-400 font-medium">
            Erro ao carregar histórico
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-md mx-auto">
            {error instanceof Error ? error.message : 'Erro desconhecido'}
          </p>
          <button
            onClick={() => {
              refetch();
              refetchChannels();
            }}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2 mx-auto"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Tentar novamente</span>
          </button>
        </div>
      ) : isLoading ? (
        <div className="text-center py-12 text-gray-500">
          Carregando...
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-12">
          <Video className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500 dark:text-gray-400">
            Nenhum vídeo encontrado
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            Os vídeos gerados aparecerão aqui
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {videos.map((video) => (
            <div
              key={video.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden"
            >
              {/* Video Header */}
              <div
                className="p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750"
                onClick={() => setExpandedVideo(expandedVideo === video.id ? null : video.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4">
                    {/* Thumbnail */}
                    <div className="w-32 h-20 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center overflow-hidden">
                      {video.thumbnailUrl ? (
                        <img
                          src={video.thumbnailUrl}
                          alt={video.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Play className="w-8 h-8 text-gray-400" />
                      )}
                    </div>

                    {/* Info */}
                    <div className="space-y-1">
                      <h3 className="font-medium text-gray-900 dark:text-white">
                        {video.title}
                      </h3>
                      {video.channelName && (
                        <div className="flex items-center space-x-1 text-sm text-gray-500 dark:text-gray-400">
                          <FolderOpen className="w-3 h-3" />
                          <span>{video.channelName}</span>
                        </div>
                      )}
                      <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                        <span className="flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{formatDate(video.createdAt)}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Film className="w-3 h-3" />
                          <span>{video.scenesCount} cenas</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Video className="w-3 h-3" />
                          <span>{formatDuration(video.durationSeconds)}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <HardDrive className="w-3 h-3" />
                          <span>{formatFileSize(video.fileSize)}</span>
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2">
                    <a
                      href={historyApi.getVideoDownloadUrl(video.id)}
                      download
                      onClick={(e) => e.stopPropagation()}
                      className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      title="Download"
                    >
                      <Download className="w-5 h-5" />
                    </a>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(video.id);
                      }}
                      className="p-2 text-gray-500 hover:text-red-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      title="Excluir"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                    <ChevronDown
                      className={`w-5 h-5 text-gray-400 transition-transform ${
                        expandedVideo === video.id ? 'rotate-180' : ''
                      }`}
                    />
                  </div>
                </div>
              </div>

              {/* Expanded Content */}
              {expandedVideo === video.id && (
                <div className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-4">
                  {/* Video Player */}
                  {video.videoUrl && (
                    <video
                      src={video.videoUrl}
                      controls
                      className="w-full max-w-2xl rounded-lg"
                    />
                  )}

                  {/* Text Preview */}
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Texto usado:
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
                      {video.textPreview}
                      {video.textPreview.length >= 200 && '...'}
                    </p>
                  </div>

                  {/* Details */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Resolução:</span>
                      <span className="ml-2 text-gray-900 dark:text-white">{video.resolution}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Job ID:</span>
                      <span className="ml-2 text-gray-900 dark:text-white font-mono text-xs">
                        {video.jobId.slice(0, 8)}...
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      {videosData && videosData.total > 0 && (
        <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
          Mostrando {videos.length} de {videosData.total} vídeos
        </div>
      )}
    </div>
  );
}
