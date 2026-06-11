import { useTranslation } from 'react-i18next';
import { Search, BookOpen, Heart, Clock, Globe, Sun, Moon } from 'lucide-react';
import { useState } from 'react';

export function Header({ 
  onSearch, 
  onShowFavorites, 
  onShowHistory,
  currentView 
}: { 
  onSearch: (query: string) => void;
  onShowFavorites: () => void;
  onShowHistory: () => void;
  currentView: 'home' | 'favorites' | 'history';
}) {
  const { t, i18n } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [isDark, setIsDark] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  const toggleLanguage = () => {
    const newLang = i18n.language === 'zh' ? 'en' : 'zh';
    i18n.changeLanguage(newLang);
  };

  const toggleTheme = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <header className="bg-white dark:bg-gray-800 shadow-md fixed top-0 left-0 right-0 z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <BookOpen className="w-8 h-8 text-blue-600" />
            <h1 className="text-xl font-bold text-gray-800 dark:text-white">
              {t('title')}
            </h1>
          </div>

          <div className="flex-1 max-w-2xl mx-8">
            <form onSubmit={handleSearch} className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('searchPlaceholder')}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 transform -translate-y-1/2 px-4 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                {t('search')}
              </button>
            </form>
          </div>

          <div className="flex items-center space-x-4">
            <button
              onClick={onShowFavorites}
              className={`flex items-center space-x-1 px-3 py-2 rounded-md transition-colors ${
                currentView === 'favorites' 
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300' 
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              <Heart className="w-5 h-5" />
              <span>{t('favorites')}</span>
            </button>

            <button
              onClick={onShowHistory}
              className={`flex items-center space-x-1 px-3 py-2 rounded-md transition-colors ${
                currentView === 'history' 
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300' 
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              <Clock className="w-5 h-5" />
              <span>{t('history')}</span>
            </button>

            <div className="h-6 w-px bg-gray-300 dark:bg-gray-600" />

            <button
              onClick={toggleLanguage}
              className="flex items-center space-x-1 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-md transition-colors dark:text-gray-300 dark:hover:bg-gray-700"
            >
              <Globe className="w-5 h-5" />
              <span>{i18n.language === 'zh' ? 'EN' : '中文'}</span>
            </button>

            <button
              onClick={toggleTheme}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-md transition-colors dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
