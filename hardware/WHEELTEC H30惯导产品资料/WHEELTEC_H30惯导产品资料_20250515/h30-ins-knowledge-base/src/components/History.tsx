import { SearchHistoryItem } from '../types';
import { useTranslation } from 'react-i18next';
import { Clock, Trash2, ArrowRight } from 'lucide-react';

interface HistoryProps {
  history: SearchHistoryItem[];
  onSearch: (query: string) => void;
  onClearHistory: () => void;
  onDeleteItem: (query: string) => void;
}

export function History({ history, onSearch, onClearHistory, onDeleteItem }: HistoryProps) {
  const { t } = useTranslation();

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (history.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 dark:text-gray-600 mb-4">
          <Clock className="w-16 h-16 mx-auto" />
        </div>
        <h3 className="text-lg font-medium text-gray-800 dark:text-white mb-2">
          No Search History
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Your search history will appear here
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
          {t('recentSearches')} ({history.length})
        </h2>
        <button
          onClick={onClearHistory}
          className="flex items-center space-x-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-md transition-colors dark:text-red-400 dark:hover:bg-red-900/20"
        >
          <Trash2 className="w-4 h-4" />
          <span>{t('clearHistory')}</span>
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {history.map((item, index) => (
            <li
              key={`${item.query}-${index}`}
              className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <button
                onClick={() => onSearch(item.query)}
                className="flex-1 flex items-center space-x-4 text-left"
              >
                <Clock className="w-5 h-5 text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-gray-800 dark:text-white font-medium truncate">
                    {item.query}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {formatDate(item.timestamp)}
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
              </button>

              <button
                onClick={() => onDeleteItem(item.query)}
                className="ml-4 p-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
                title="Delete"
              >
                <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-600" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
