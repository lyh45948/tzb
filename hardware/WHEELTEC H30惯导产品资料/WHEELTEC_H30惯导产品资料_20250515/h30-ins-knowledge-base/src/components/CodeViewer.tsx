import { Document } from '../types';
import { X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeViewerProps {
  document: Document | null;
  onClose: () => void;
}

export function CodeViewer({ document, onClose }: CodeViewerProps) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (document) {
      loadCode();
    }
  }, [document]);

  const loadCode = async () => {
    if (!document) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const fullPath = `../${document.path}`;
      const response = await fetch(fullPath);
      
      if (!response.ok) {
        throw new Error('Failed to load file');
      }
      
      const text = await response.text();
      setContent(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load code');
      console.error('Error loading code:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!document) return null;

  const getLanguage = () => {
    if (document.name.endsWith('.py')) return 'python';
    if (document.name.endsWith('.js')) return 'javascript';
    if (document.name.endsWith('.ts')) return 'typescript';
    if (document.name.endsWith('.c')) return 'c';
    if (document.name.endsWith('.cpp')) return 'cpp';
    if (document.name.endsWith('.h')) return 'cpp';
    if (document.name.endsWith('.java')) return 'java';
    if (document.name.endsWith('.txt')) return 'text';
    return 'text';
  };

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
            {document.name}
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="text-red-500 mb-4">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-800 dark:text-white mb-2">
                Error Loading File
              </h3>
              <p className="text-gray-600 dark:text-gray-400">{error}</p>
              <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                Path: {document.path}
              </p>
            </div>
          ) : (
            <div className="rounded-lg overflow-hidden">
              <SyntaxHighlighter
                language={getLanguage()}
                style={vscDarkPlus}
                customStyle={{
                  margin: 0,
                  borderRadius: '8px',
                  fontSize: '14px',
                }}
              >
                {content}
              </SyntaxHighlighter>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <button
            onClick={() => {
              const fullPath = `../${document.path}`;
              window.open(fullPath, '_blank');
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
          >
            Download File
          </button>
        </div>
      </div>
    </div>
  );
}
