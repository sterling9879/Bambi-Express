'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FolderOpen,
  Plus,
  Edit2,
  Trash2,
  Video,
  Save,
  X,
  Palette
} from 'lucide-react';
import { channelsApi } from '@/lib/api';
import type { Channel, ChannelCreate } from '@/lib/types';

const CHANNEL_COLORS = [
  '#ef4444', // red
  '#f97316', // orange
  '#f59e0b', // amber
  '#84cc16', // lime
  '#22c55e', // green
  '#14b8a6', // teal
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#6366f1', // indigo
  '#8b5cf6', // violet
  '#a855f7', // purple
  '#ec4899', // pink
];

export function ChannelManager() {
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<ChannelCreate>({
    name: '',
    description: '',
    color: CHANNEL_COLORS[0],
  });
  const queryClient = useQueryClient();

  const { data: channels = [], isLoading } = useQuery({
    queryKey: ['channels'],
    queryFn: channelsApi.list,
  });

  const createMutation = useMutation({
    mutationFn: channelsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setIsCreating(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ChannelCreate> }) =>
      channelsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setEditingId(null);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: channelsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      queryClient.invalidateQueries({ queryKey: ['videos'] });
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      color: CHANNEL_COLORS[0],
    });
  };

  const handleStartEdit = (channel: Channel) => {
    setEditingId(channel.id);
    setFormData({
      name: channel.name,
      description: channel.description || '',
      color: channel.color,
    });
    setIsCreating(false);
  };

  const handleSave = () => {
    if (!formData.name.trim()) return;

    if (editingId) {
      updateMutation.mutate({ id: editingId, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleCancel = () => {
    setIsCreating(false);
    setEditingId(null);
    resetForm();
  };

  const handleDelete = (channel: Channel) => {
    if (channel.videoCount > 0) {
      if (!confirm(
        `O canal "${channel.name}" contém ${channel.videoCount} vídeo(s). ` +
        `Os vídeos serão mantidos mas não estarão mais associados a este canal. Continuar?`
      )) {
        return;
      }
    } else {
      if (!confirm(`Tem certeza que deseja excluir o canal "${channel.name}"?`)) {
        return;
      }
    }
    deleteMutation.mutate(channel.id);
  };

  const ChannelForm = () => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-4 space-y-4">
      <h3 className="font-medium text-gray-900 dark:text-white">
        {editingId ? 'Editar Canal' : 'Novo Canal'}
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Nome
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Ex: Vídeos de Tecnologia"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Descrição (opcional)
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Descrição do canal..."
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Cor
          </label>
          <div className="flex flex-wrap gap-2">
            {CHANNEL_COLORS.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setFormData({ ...formData, color })}
                className={`w-8 h-8 rounded-lg transition-transform ${
                  formData.color === color ? 'ring-2 ring-offset-2 ring-gray-400 scale-110' : ''
                }`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-2">
        <button
          onClick={handleCancel}
          className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          Cancelar
        </button>
        <button
          onClick={handleSave}
          disabled={!formData.name.trim() || createMutation.isPending || updateMutation.isPending}
          className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          <span>{editingId ? 'Salvar' : 'Criar'}</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Organize seus vídeos em canais para facilitar a busca
        </p>
        {!isCreating && !editingId && (
          <button
            onClick={() => setIsCreating(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Novo Canal</span>
          </button>
        )}
      </div>

      {/* Create/Edit Form */}
      {(isCreating || editingId) && <ChannelForm />}

      {/* Channels List */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">
          Carregando...
        </div>
      ) : channels.length === 0 && !isCreating ? (
        <div className="text-center py-12">
          <FolderOpen className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500 dark:text-gray-400">
            Nenhum canal criado
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            Crie canais para organizar seus vídeos
          </p>
          <button
            onClick={() => setIsCreating(true)}
            className="mt-4 flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors mx-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Criar primeiro canal</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {channels.map((channel) => (
            <div
              key={channel.id}
              className={`bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden ${
                editingId === channel.id ? 'ring-2 ring-primary-500' : ''
              }`}
            >
              {/* Color Bar */}
              <div
                className="h-2"
                style={{ backgroundColor: channel.color }}
              />

              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${channel.color}20` }}
                    >
                      <FolderOpen
                        className="w-5 h-5"
                        style={{ color: channel.color }}
                      />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-white">
                        {channel.name}
                      </h3>
                      <div className="flex items-center space-x-1 text-sm text-gray-500 dark:text-gray-400">
                        <Video className="w-3 h-3" />
                        <span>{channel.videoCount} vídeo(s)</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => handleStartEdit(channel)}
                      className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      title="Editar"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(channel)}
                      className="p-2 text-gray-500 hover:text-red-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      title="Excluir"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {channel.description && (
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    {channel.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
