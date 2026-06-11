import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { SearchResults } from './components/SearchResults';
import { Favorites } from './components/Favorites';
import { History } from './components/History';
import { QASection } from './components/QASection';
import { CodeViewer } from './components/CodeViewer';
import { useLocalStorage } from './hooks/useLocalStorage';
import { searchDocuments, getDocumentsByCategory } from './utils/search';
import { Document, SearchResult, SearchHistoryItem } from './types';
import { documents } from './data/documents';

type View = 'home' | 'favorites' | 'history' | 'qa';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [currentView, setCurrentView] = useState<View>('home');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [favoriteIds, setFavoriteIds] = useLocalStorage<string[]>('favorites', []);
  const [searchHistory, setSearchHistory] = useLocalStorage<SearchHistoryItem[]>('searchHistory', []);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setCurrentView('home');
    
    if (query.trim()) {
      const results = searchDocuments(query);
      setSearchResults(results);
      
      // Add to search history
      const newHistory: SearchHistoryItem = {
        query,
        timestamp: Date.now()
      };
      setSearchHistory(prev => {
        const filtered = prev.filter(h => h.query !== query);
        return [newHistory, ...filtered].slice(0, 20);
      });
    } else {
      setSearchResults([]);
    }
  };

  const handleToggleFavorite = (docId: string) => {
    setFavoriteIds(prev => 
      prev.includes(docId) 
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const handleDeleteHistoryItem = (query: string) => {
    setSearchHistory(prev => prev.filter(h => h.query !== query));
  };

  const getDisplayDocuments = (): Document[] => {
    if (searchQuery) {
      return searchResults.map(r => r.document);
    }
    
    if (selectedCategory === 'all') {
      return documents;
    }
    
    return getDocumentsByCategory(selectedCategory);
  };

  const displayDocuments = getDisplayDocuments();

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <Header 
        onSearch={handleSearch}
        onShowFavorites={() => setCurrentView('favorites')}
        onShowHistory={() => setCurrentView('history')}
        currentView={currentView}
      />

      <div className="flex pt-16">
        <Sidebar 
          selectedCategory={selectedCategory}
          onCategoryChange={(cat) => {
            setSelectedCategory(cat);
            setSearchQuery('');
            setCurrentView('home');
          }}
        />

        <main className="flex-1 ml-64 p-6">
          {currentView === 'home' && (
            <>
              {searchQuery ? (
                <SearchResults
                  results={searchResults}
                  favorites={favoriteIds}
                  onToggleFavorite={handleToggleFavorite}
                  onViewCode={setSelectedDocument}
                />
              ) : selectedCategory === 'all' ? (
                <QASection />
              ) : (
                <div>
                  <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">
                    {selectedCategory.charAt(0).toUpperCase() + selectedCategory.slice(1)} ({displayDocuments.length})
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {displayDocuments.map(doc => (
                      <div key={doc.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                        <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-2">
                          {doc.name}
                        </h3>
                        {doc.description && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                            {doc.description}
                          </p>
                        )}
                        <button
                          onClick={() => window.open(`../${doc.path}`, '_blank')}
                          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
                        >
                          Download
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {currentView === 'favorites' && (
            <Favorites
              favoriteIds={favoriteIds}
              allDocuments={documents}
              onToggleFavorite={handleToggleFavorite}
              onViewCode={setSelectedDocument}
            />
          )}

          {currentView === 'history' && (
            <History
              history={searchHistory}
              onSearch={handleSearch}
              onClearHistory={() => setSearchHistory([])}
              onDeleteItem={handleDeleteHistoryItem}
            />
          )}

          {currentView === 'qa' && <QASection />}
        </main>
      </div>

      {selectedDocument && (
        <CodeViewer
          document={selectedDocument}
          onClose={() => setSelectedDocument(null)}
        />
      )}

      <footer className="fixed bottom-0 left-64 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 py-3 px-6 text-center text-sm text-gray-600 dark:text-gray-400">
        © 2025 WHEELTEC. All rights reserved. | Version 1.0.0
      </footer>
    </div>
  );
}

export default App;
