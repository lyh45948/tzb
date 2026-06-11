export interface Document {
  id: string;
  name: string;
  category: string;
  type: 'pdf' | 'code' | 'zip';
  path: string;
  description?: string;
  language?: string;
}

export interface FavoriteItem {
  id: string;
  documentId: string;
  timestamp: number;
}

export interface SearchHistoryItem {
  query: string;
  timestamp: number;
}

export interface SearchResult {
  document: Document;
  relevance: number;
  snippet?: string;
}
