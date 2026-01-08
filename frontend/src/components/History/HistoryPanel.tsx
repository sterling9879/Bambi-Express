'use client';

import { useState } from 'react';
import { Video, Image, Music2, FolderOpen } from 'lucide-react';
import { VideoHistory } from './VideoHistory';
import { ElementHistory } from './ElementHistory';
import { ChannelManager } from './ChannelManager';

type HistoryTab = 'videos' | 'elements' | 'channels';

export function HistoryPanel() {
  const [activeTab, setActiveTab] = useState<HistoryTab>('videos');

  const tabs = [
    { id: 'videos' as HistoryTab, label: 'Vídeos', icon: Video },
    { id: 'elements' as HistoryTab, label: 'Elementos', icon: Image },
    { id: 'channels' as HistoryTab, label: 'Canais', icon: FolderOpen },
  ];

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex space-x-2 border-b border-gray-200 dark:border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'videos' && <VideoHistory />}
      {activeTab === 'elements' && <ElementHistory />}
      {activeTab === 'channels' && <ChannelManager />}
    </div>
  );
}
