'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Image,
  Music2,
  Trash2,
  Clock,
  Download,
  Eye,
  X,
  FileAudio,
  Layers
} from 'lucide-react';
import { historyApi } from '@/lib/api';
import type { Element, ElementType } from '@/lib/types';

export function ElementHistory() {
  const [selectedType, setSelectedType] = useState<ElementType | null>(null);
  const [previewElement, setPreviewElement] = useState<Element | null>(null);
  const queryClient = useQueryClient();

  const { data: elementsData, isLoading } = useQuery({
    queryKey: ['elements', selectedType],
    queryFn: () => historyApi.listElements({
      elementType: selectedType || undefined,
      limit: 100
    }),
  });

  const deleteMutation = useMutation({
    mutationFn: historyApi.deleteElement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['elements'] });
      queryClient.invalidateQueries({ queryKey: ['history-stats'] });
    },
  });

  const elements = elementsData?.elements || [];

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) {
      return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const handleDelete = (elementId: string) => {
    if (confirm('Tem certeza que deseja excluir este elemento?')) {
      deleteMutation.mutate(elementId);
    }
  };

  const getElementIcon = (type: ElementType) => {
    switch (type) {
      case 'image':
        return Image;
      case 'audio':
        return FileAudio;
      default:
        return Layers;
    }
  };

  const imageElements = elements.filter(e => e.elementType === 'image');
  const audioElements = elements.filter(e => e.elementType === 'audio');

  return (
    <div className="space-y-6">
      {/* Type Filter */}
      <div className="flex items-center space-x-4">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Filtrar por tipo:
        </label>
        <div className="flex space-x-2">
          <button
            onClick={() => setSelectedType(null)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              selectedType === null
                ? 'bg-primary-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => setSelectedType('image')}
            className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              selectedType === 'image'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            <Image className="w-4 h-4" />
            <span>Imagens</span>
          </button>
          <button
            onClick={() => setSelectedType('audio')}
            className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              selectedType === 'audio'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            <FileAudio className="w-4 h-4" />
            <span>Áudios</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">
          Carregando...
        </div>
      ) : elements.length === 0 ? (
        <div className="text-center py-12">
          <Layers className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500 dark:text-gray-400">
            Nenhum elemento encontrado
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            As imagens e áudios gerados aparecerão aqui
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Images Section */}
          {(selectedType === null || selectedType === 'image') && imageElements.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center space-x-2">
                <Image className="w-5 h-5" />
                <span>Imagens ({imageElements.length})</span>
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {imageElements.map((element) => (
                  <div
                    key={element.id}
                    className="group relative bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden"
                  >
                    {/* Image Thumbnail */}
                    <div className="aspect-video bg-gray-100 dark:bg-gray-900 relative">
                      {element.fileUrl ? (
                        <img
                          src={element.fileUrl}
                          alt={element.prompt || 'Imagem gerada'}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Image className="w-8 h-8 text-gray-400" />
                        </div>
                      )}

                      {/* Overlay Actions */}
                      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center space-x-2">
                        <button
                          onClick={() => setPreviewElement(element)}
                          className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
                          title="Visualizar"
                        >
                          <Eye className="w-5 h-5 text-white" />
                        </button>
                        {element.fileUrl && (
                          <a
                            href={element.fileUrl}
                            download
                            className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
                            title="Download"
                          >
                            <Download className="w-5 h-5 text-white" />
                          </a>
                        )}
                        <button
                          onClick={() => handleDelete(element.id)}
                          className="p-2 bg-red-500/50 hover:bg-red-500/70 rounded-lg transition-colors"
                          title="Excluir"
                        >
                          <Trash2 className="w-5 h-5 text-white" />
                        </button>
                      </div>

                      {/* Scene Badge */}
                      {element.sceneIndex !== null && element.sceneIndex !== undefined && (
                        <div className="absolute top-2 left-2 px-2 py-0.5 bg-black/50 text-white text-xs rounded">
                          Cena {element.sceneIndex + 1}
                        </div>
                      )}
                    </div>

                    {/* Info */}
                    <div className="p-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {element.prompt || 'Sem prompt'}
                      </p>
                      <div className="flex items-center justify-between mt-1 text-xs text-gray-400">
                        <span>{formatDate(element.createdAt)}</span>
                        <span>{formatFileSize(element.fileSize)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Audio Section */}
          {(selectedType === null || selectedType === 'audio') && audioElements.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center space-x-2">
                <FileAudio className="w-5 h-5" />
                <span>Áudios ({audioElements.length})</span>
              </h3>
              <div className="space-y-2">
                {audioElements.map((element) => (
                  <div
                    key={element.id}
                    className="flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-4"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
                        <FileAudio className="w-5 h-5 text-primary-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {element.sceneIndex !== null && element.sceneIndex !== undefined
                            ? `Áudio - Cena ${element.sceneIndex + 1}`
                            : 'Áudio de narração'}
                        </p>
                        <div className="flex items-center space-x-3 text-xs text-gray-500 dark:text-gray-400">
                          <span className="flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{formatDate(element.createdAt)}</span>
                          </span>
                          <span>{formatFileSize(element.fileSize)}</span>
                          {element.durationMs && (
                            <span>{(element.durationMs / 1000).toFixed(1)}s</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {element.fileUrl && (
                        <>
                          <audio
                            src={element.fileUrl}
                            controls
                            className="h-8"
                          />
                          <a
                            href={element.fileUrl}
                            download
                            className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            title="Download"
                          >
                            <Download className="w-5 h-5" />
                          </a>
                        </>
                      )}
                      <button
                        onClick={() => handleDelete(element.id)}
                        className="p-2 text-gray-500 hover:text-red-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        title="Excluir"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Stats */}
      {elementsData && elementsData.total > 0 && (
        <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
          Mostrando {elements.length} de {elementsData.total} elementos
        </div>
      )}

      {/* Image Preview Modal */}
      {previewElement && previewElement.elementType === 'image' && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setPreviewElement(null)}
        >
          <div
            className="relative max-w-4xl max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setPreviewElement(null)}
              className="absolute -top-10 right-0 text-white hover:text-gray-300"
            >
              <X className="w-6 h-6" />
            </button>
            {previewElement.fileUrl && (
              <img
                src={previewElement.fileUrl}
                alt={previewElement.prompt || 'Imagem gerada'}
                className="max-w-full max-h-[80vh] rounded-lg"
              />
            )}
            {previewElement.prompt && (
              <p className="mt-4 text-white text-center text-sm">
                {previewElement.prompt}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
