import { SearchResult } from '../types';
import { useTranslation } from 'react-i18next';
import { DocumentCard } from './DocumentCard';

interface SearchResultsProps {
  results: SearchResult[];
  favorites: string[];
  onToggleFavorite: (docId: string) => void;
  onViewCode: (doc: any) => void;
}

export function SearchResults({ results, favorites, onToggleFavorite, onViewCode }: SearchResultsProps) {
  const { t } = useTranslation();

  if (results.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 dark:text-gray-600 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-800 dark:text-white mb-2">
          {t('noResults')}
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Try different keywords or browse categories
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">
        {t('searchResults')} ({results.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {results.map((result) => (
          <DocumentCard
            key={result.document.id}
            document={result.document}
            isFavorite={favorites.includes(result.document.id)}
            onToggleFavorite={onToggleFavorite}
            onViewCode={onViewCode}
          />
        ))}
      </div>
    </div>
  );
}
