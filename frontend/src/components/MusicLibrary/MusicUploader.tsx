'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Music } from 'lucide-react';
import { useMusicLibrary } from '@/hooks/useMusicLibrary';
import toast from 'react-hot-toast';
import type { MusicMood } from '@/lib/types';

const MOODS: { value: MusicMood; label: string }[] = [
  { value: 'alegre', label: 'Alegre' },
  { value: 'animado', label: 'Animado' },
  { value: 'calmo', label: 'Calmo' },
  { value: 'dramatico', label: 'Dramático' },
  { value: 'inspirador', label: 'Inspirador' },
  { value: 'melancolico', label: 'Melancólico' },
  { value: 'raiva', label: 'Raiva' },
  { value: 'romantico', label: 'Romântico' },
  { value: 'sombrio', label: 'Sombrio' },
  { value: 'vibrante', label: 'Vibrante' },
];

export function MusicUploader() {
  const { uploadFile, isUploading } = useMusicLibrary();
  const [selectedMood, setSelectedMood] = useState<MusicMood>('calmo');
  const [tags, setTags] = useState('');
  const [filesToUpload, setFilesToUpload] = useState<File[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFilesToUpload((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/mpeg': ['.mp3'],
      'audio/wav': ['.wav'],
      'audio/ogg': ['.ogg'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleUpload = async () => {
    if (filesToUpload.length === 0) return;

    const tagList = tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    for (const file of filesToUpload) {
      try {
        await uploadFile(file, selectedMood, tagList);
        toast.success(`${file.name} uploaded!`);
      } catch (error) {
        toast.error(`Erro ao fazer upload de ${file.name}`);
      }
    }

    setFilesToUpload([]);
    setTags('');
  };

  const removeFile = (index: number) => {
    setFilesToUpload((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center">
          <Music className="w-5 h-5 mr-2" />
          Biblioteca de Músicas
        </h2>
      </div>

      <div className="p-6 space-y-6">
        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-primary-400'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600 dark:text-gray-300">
            {isDragActive
              ? 'Solte os arquivos aqui...'
              : 'Arraste músicas aqui ou clique para selecionar'}
          </p>
          <p className="text-sm text-gray-500 mt-2">Formatos: MP3, WAV, OGG (máx 50MB)</p>
        </div>

        {/* Files to upload */}
        {filesToUpload.length > 0 && (
          <div className="space-y-4">
            <h3 className="font-medium text-gray-900 dark:text-white">
              Arquivos selecionados ({filesToUpload.length})
            </h3>

            <ul className="space-y-2">
              {filesToUpload.map((file, index) => (
                <li
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <Music className="w-5 h-5 text-gray-400" />
                    <span className="text-gray-700 dark:text-gray-300">{file.name}</span>
                    <span className="text-sm text-gray-500">
                      ({(file.size / 1024 / 1024).toFixed(1)} MB)
                    </span>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="text-red-500 hover:text-red-700"
                  >
                    Remover
                  </button>
                </li>
              ))}
            </ul>

            {/* Mood selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Mood para todos os arquivos
              </label>
              <div className="flex flex-wrap gap-2">
                {MOODS.map((mood) => (
                  <button
                    key={mood.value}
                    onClick={() => setSelectedMood(mood.value)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      selectedMood === mood.value
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    {mood.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tags */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tags (opcional, separadas por vírgula)
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="Ex: épico, batalha, orquestra"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            {/* Upload button */}
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              <Upload className="w-5 h-5" />
              <span>{isUploading ? 'Enviando...' : 'Fazer Upload'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
