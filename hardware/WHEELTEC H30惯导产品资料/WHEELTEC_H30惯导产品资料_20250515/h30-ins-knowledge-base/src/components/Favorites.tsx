import { Document } from '../types';
import { useTranslation } from 'react-i18next';
import { DocumentCard } from './DocumentCard';
import { Trash2 } from 'lucide-react';

interface FavoritesProps {
  favoriteIds: string[];
  allDocuments: Document[];
  onToggleFavorite: (docId: string) => void;
  onViewCode: (doc: Document) => void;
}

export function Favorites({ favoriteIds, allDocuments, onToggleFavorite, onViewCode }: FavoritesProps) {
  const { t } = useTranslation();

  const favoriteDocuments = allDocuments.filter(doc => favoriteIds.includes(doc.id));

  const handleClearAll = () => {
    favoriteIds.forEach(id => onToggleFavorite(id));
  };

  if (favoriteDocuments.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 dark:text-gray-600 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-800 dark:text-white mb-2">
          No Favorites Yet
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Click the heart icon on any document to add it to your favorites
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
          {t('favorites')} ({favoriteDocuments.length})
        </h2>
        <button
          onClick={handleClearAll}
          className="flex items-center space-x-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-md transition-colors dark:text-red-400 dark:hover:bg-red-900/20"
        >
          <Trash2 className="w-4 h-4" />
          <span>Clear All</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {favoriteDocuments.map(doc => (
          <DocumentCard
            key={doc.id}
            document={doc}
            isFavorite={true}
            onToggleFavorite={onToggleFavorite}
            onViewCode={onViewCode}
          />
        ))}
      </div>
    </div>
  );
}
