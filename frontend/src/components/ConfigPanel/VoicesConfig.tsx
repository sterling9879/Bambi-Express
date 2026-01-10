'use client';

import { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, Save, X, Mic } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configApi } from '@/lib/api';
import toast from 'react-hot-toast';
import type { CustomVoice, MinimaxVoice } from '@/lib/types';

export function VoicesConfig() {
  const queryClient = useQueryClient();
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Form states
  const [newVoice, setNewVoice] = useState({
    voiceId: '',
    name: '',
    gender: 'neutral' as 'male' | 'female' | 'neutral',
    description: '',
  });

  const [editVoice, setEditVoice] = useState({
    voiceId: '',
    name: '',
    gender: 'neutral' as 'male' | 'female' | 'neutral',
    description: '',
  });

  // Fetch custom voices
  const { data: voicesData, isLoading } = useQuery({
    queryKey: ['customVoices'],
    queryFn: configApi.getCustomVoices,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: configApi.createCustomVoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customVoices'] });
      queryClient.invalidateQueries({ queryKey: ['config'] });
      setIsAdding(false);
      setNewVoice({ voiceId: '', name: '', gender: 'neutral', description: '' });
      toast.success('Voz adicionada!');
    },
    onError: () => {
      toast.error('Erro ao adicionar voz');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<typeof editVoice> }) =>
      configApi.updateCustomVoice(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customVoices'] });
      queryClient.invalidateQueries({ queryKey: ['config'] });
      setEditingId(null);
      toast.success('Voz atualizada!');
    },
    onError: () => {
      toast.error('Erro ao atualizar voz');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: configApi.deleteCustomVoice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customVoices'] });
      queryClient.invalidateQueries({ queryKey: ['config'] });
      toast.success('Voz removida!');
    },
    onError: () => {
      toast.error('Erro ao remover voz');
    },
  });

  const handleAdd = () => {
    if (!newVoice.voiceId.trim() || !newVoice.name.trim()) {
      toast.error('ID da voz e nome são obrigatórios');
      return;
    }
    createMutation.mutate(newVoice);
  };

  const handleEdit = (voice: CustomVoice) => {
    setEditingId(voice.id);
    setEditVoice({
      voiceId: voice.voiceId,
      name: voice.name,
      gender: voice.gender,
      description: voice.description,
    });
  };

  const handleSaveEdit = () => {
    if (!editingId) return;
    updateMutation.mutate({ id: editingId, updates: editVoice });
  };

  const handleDelete = (voiceId: string) => {
    if (confirm('Tem certeza que deseja remover esta voz?')) {
      deleteMutation.mutate(voiceId);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
          <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
          <Mic className="w-5 h-5 mr-2" />
          Vozes Minimax
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Adicione vozes personalizadas com seus IDs para usar no Minimax
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Add new voice button */}
        {!isAdding && (
          <button
            onClick={() => setIsAdding(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Adicionar Voz</span>
          </button>
        )}

        {/* Add new voice form */}
        {isAdding && (
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-4">
            <h3 className="font-medium text-gray-900 dark:text-white">Nova Voz</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  ID da Voz (API)
                </label>
                <input
                  type="text"
                  value={newVoice.voiceId}
                  onChange={(e) => setNewVoice({ ...newVoice, voiceId: e.target.value })}
                  placeholder="Ex: Narrator_Man"
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Nome de Exibição
                </label>
                <input
                  type="text"
                  value={newVoice.name}
                  onChange={(e) => setNewVoice({ ...newVoice, name: e.target.value })}
                  placeholder="Ex: Narrador Masculino"
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Gênero
                </label>
                <select
                  value={newVoice.gender}
                  onChange={(e) => setNewVoice({ ...newVoice, gender: e.target.value as 'male' | 'female' | 'neutral' })}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="male">Masculino</option>
                  <option value="female">Feminino</option>
                  <option value="neutral">Neutro</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Descrição (opcional)
                </label>
                <input
                  type="text"
                  value={newVoice.description}
                  onChange={(e) => setNewVoice({ ...newVoice, description: e.target.value })}
                  placeholder="Ex: Voz grave para narrações"
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => {
                  setIsAdding(false);
                  setNewVoice({ voiceId: '', name: '', gender: 'neutral', description: '' });
                }}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Cancelar
              </button>
              <button
                onClick={handleAdd}
                disabled={createMutation.isPending}
                className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                <span>{createMutation.isPending ? 'Salvando...' : 'Salvar'}</span>
              </button>
            </div>
          </div>
        )}

        {/* Custom voices list */}
        {voicesData?.customVoices && voicesData.customVoices.length > 0 && (
          <div className="space-y-4">
            <h3 className="font-medium text-gray-900 dark:text-white">
              Vozes Personalizadas ({voicesData.customVoices.length})
            </h3>
            <div className="space-y-2">
              {voicesData.customVoices.map((voice) => (
                <div
                  key={voice.id}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                >
                  {editingId === voice.id ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            ID da Voz (API)
                          </label>
                          <input
                            type="text"
                            value={editVoice.voiceId}
                            onChange={(e) => setEditVoice({ ...editVoice, voiceId: e.target.value })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Nome
                          </label>
                          <input
                            type="text"
                            value={editVoice.name}
                            onChange={(e) => setEditVoice({ ...editVoice, name: e.target.value })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Gênero
                          </label>
                          <select
                            value={editVoice.gender}
                            onChange={(e) => setEditVoice({ ...editVoice, gender: e.target.value as 'male' | 'female' | 'neutral' })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          >
                            <option value="male">Masculino</option>
                            <option value="female">Feminino</option>
                            <option value="neutral">Neutro</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Descrição
                          </label>
                          <input
                            type="text"
                            value={editVoice.description}
                            onChange={(e) => setEditVoice({ ...editVoice, description: e.target.value })}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          />
                        </div>
                      </div>
                      <div className="flex justify-end space-x-2">
                        <button
                          onClick={() => setEditingId(null)}
                          className="px-3 py-1 text-gray-600 dark:text-gray-400 hover:text-gray-800"
                        >
                          <X className="w-4 h-4" />
                        </button>
                        <button
                          onClick={handleSaveEdit}
                          disabled={updateMutation.isPending}
                          className="px-3 py-1 text-primary-600 hover:text-primary-700"
                        >
                          <Save className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-gray-900 dark:text-white">
                            {voice.name}
                          </span>
                          <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                            {voice.gender === 'male' ? 'Masculino' : voice.gender === 'female' ? 'Feminino' : 'Neutro'}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          ID: <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{voice.voiceId}</code>
                        </div>
                        {voice.description && (
                          <div className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                            {voice.description}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleEdit(voice)}
                          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(voice.id)}
                          disabled={deleteMutation.isPending}
                          className="p-2 text-red-400 hover:text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Default voices reference */}
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900 dark:text-white">
            Vozes Padrão do Minimax
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Estas vozes estão disponíveis por padrão. Você pode usar os IDs abaixo ou adicionar vozes personalizadas.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-60 overflow-y-auto">
            {voicesData?.defaultVoices?.map((voice) => (
              <div
                key={voice.voice_id}
                className="text-sm p-2 bg-gray-50 dark:bg-gray-700/50 rounded"
              >
                <div className="font-medium text-gray-700 dark:text-gray-300">
                  {voice.name}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {voice.voice_id}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
