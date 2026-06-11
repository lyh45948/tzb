import { Document } from '../types';
import { useTranslation } from 'react-i18next';
import { Download, FileText, Archive, Code as CodeIcon } from 'lucide-react';
import { useState } from 'react';

interface DocumentCardProps {
  document: Document;
  isFavorite: boolean;
  onToggleFavorite: (docId: string) => void;
  onViewCode: (doc: Document) => void;
}

export function DocumentCard({ document, isFavorite, onToggleFavorite, onViewCode }: DocumentCardProps) {
  const { t } = useTranslation();

  const getFileIcon = () => {
    switch (document.type) {
      case 'pdf':
        return <FileText className="w-8 h-8 text-red-500" />;
      case 'zip':
        return <Archive className="w-8 h-8 text-yellow-500" />;
      case 'code':
        return <CodeIcon className="w-8 h-8 text-blue-500" />;
      default:
        return <FileText className="w-8 h-8 text-gray-500" />;
    }
  };

  const handleDownload = () => {
    const fullPath = `../${document.path}`;
    window.open(fullPath, '_blank');
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-4 flex-1">
          <div className="flex-shrink-0">
            {getFileIcon()}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-2 truncate">
              {document.name}
            </h3>
            {document.description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
                {document.description}
              </p>
            )}
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-md dark:bg-blue-900 dark:text-blue-200">
                {t(`${document.category}`)}
              </span>
              <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-md dark:bg-gray-700 dark:text-gray-300">
                {t(`${document.type}Document`) || t('codeFile')}
              </span>
            </div>
          </div>
        </div>
        
        <button
          onClick={() => onToggleFavorite(document.id)}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors flex-shrink-0"
          title={isFavorite ? t('removeFromFavorites') : t('addToFavorites')}
        >
          <svg
            className={`w-6 h-6 ${isFavorite ? 'fill-red-500 text-red-500' : 'text-gray-400'}`}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
        </button>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <button
          onClick={handleDownload}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
        >
          <Download className="w-4 h-4" />
          <span>{t('download')}</span>
        </button>

        {document.type === 'code' && (
          <button
            onClick={() => onViewCode(document)}
            className="flex items-center space-x-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-md transition-colors text-sm dark:text-blue-400 dark:hover:bg-blue-900/20"
          >
            <CodeIcon className="w-4 h-4" />
            <span>{t('viewCode')}</span>
          </button>
        )}
      </div>
    </div>
  );
}
