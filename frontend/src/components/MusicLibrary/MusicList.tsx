'use client';

import { useState, useRef } from 'react';
import { Play, Pause, Trash2, Edit2, Search } from 'lucide-react';
import { useMusicLibrary } from '@/hooks/useMusicLibrary';
import toast from 'react-hot-toast';
import type { MusicMood, MusicTrack } from '@/lib/types';

const MOODS: { value: MusicMood | ''; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'upbeat', label: 'Upbeat' },
  { value: 'dramatic', label: 'Dramatic' },
  { value: 'calm', label: 'Calm' },
  { value: 'emotional', label: 'Emotional' },
  { value: 'inspiring', label: 'Inspiring' },
  { value: 'dark', label: 'Dark' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'epic', label: 'Epic' },
  { value: 'suspense', label: 'Suspense' },
];

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function MusicList() {
  const {
    tracks,
    total,
    isLoading,
    search,
    setSearch,
    moodFilter,
    setMoodFilter,
    deleteTrack,
    isDeleting,
    getPreviewUrl,
  } = useMusicLibrary();

  const [playingId, setPlayingId] = useState<string | null>(null);
  const [editingTrack, setEditingTrack] = useState<MusicTrack | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handlePlay = (trackId: string) => {
    if (playingId === trackId) {
      audioRef.current?.pause();
      setPlayingId(null);
    } else {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      audioRef.current = new Audio(getPreviewUrl(trackId));
      audioRef.current.play();
      audioRef.current.onended = () => setPlayingId(null);
      setPlayingId(trackId);
    }
  };

  const handleDelete = async (trackId: string) => {
    if (!confirm('Tem certeza que deseja excluir esta música?')) return;

    try {
      await deleteTrack(trackId);
      toast.success('Música excluída!');
    } catch {
      toast.error('Erro ao excluir música');
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      {/* Filters */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar músicas..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          {/* Mood filter */}
          <select
            value={moodFilter || ''}
            onChange={(e) => setMoodFilter((e.target.value || undefined) as MusicMood | undefined)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            {MOODS.map((mood) => (
              <option key={mood.value} value={mood.value}>
                {mood.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Track list */}
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {isLoading ? (
          <div className="p-6 text-center text-gray-500">Carregando...</div>
        ) : tracks.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            Nenhuma música encontrada. Faça upload de algumas músicas!
          </div>
        ) : (
          tracks.map((track) => (
            <div
              key={track.id}
              className="p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div className="flex items-center space-x-4 flex-1 min-w-0">
                {/* Play button */}
                <button
                  onClick={() => handlePlay(track.id)}
                  className={`w-10 h-10 flex items-center justify-center rounded-full transition-colors ${
                    playingId === track.id
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                  }`}
                >
                  {playingId === track.id ? (
                    <Pause className="w-5 h-5" />
                  ) : (
                    <Play className="w-5 h-5 ml-0.5" />
                  )}
                </button>

                {/* Track info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 dark:text-white truncate">
                    {track.originalName}
                  </p>
                  <div className="flex items-center space-x-3 text-sm text-gray-500">
                    <span>{formatDuration(track.durationMs)}</span>
                    <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">
                      {track.mood}
                    </span>
                    <span>{formatFileSize(track.fileSize)}</span>
                  </div>
                  {track.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {track.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-1.5 py-0.5 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded text-xs"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setEditingTrack(track)}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                  title="Editar"
                >
                  <Edit2 className="w-5 h-5" />
                </button>
                <button
                  onClick={() => handleDelete(track.id)}
                  disabled={isDeleting}
                  className="p-2 text-red-500 hover:text-red-700 transition-colors disabled:opacity-50"
                  title="Excluir"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      {total > 0 && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-500">
          Total: {total} músicas
        </div>
      )}

      {/* Edit modal placeholder */}
      {editingTrack && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Editar Música
            </h3>
            <p className="text-gray-600 dark:text-gray-300 mb-4">{editingTrack.originalName}</p>
            <button
              onClick={() => setEditingTrack(null)}
              className="w-full px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              Fechar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
