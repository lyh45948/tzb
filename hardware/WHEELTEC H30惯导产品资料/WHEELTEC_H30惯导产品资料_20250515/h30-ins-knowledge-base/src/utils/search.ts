import { Document, SearchResult } from '../types';
import { documents } from '../data/documents';

export function searchDocuments(query: string): SearchResult[] {
  if (!query.trim()) {
    return [];
  }

  const lowerQuery = query.toLowerCase();
  const results: SearchResult[] = [];

  documents.forEach(doc => {
    let relevance = 0;
    let snippet = '';

    // Search in name
    if (doc.name.toLowerCase().includes(lowerQuery)) {
      relevance += 10;
    }

    // Search in description
    if (doc.description?.toLowerCase().includes(lowerQuery)) {
      relevance += 5;
      snippet = doc.description.substring(0, 100) + '...';
    }

    // Search in category
    if (doc.category.toLowerCase().includes(lowerQuery)) {
      relevance += 3;
    }

    if (relevance > 0) {
      results.push({
        document: doc,
        relevance,
        snippet
      });
    }
  });

  // Sort by relevance
  results.sort((a, b) => b.relevance - a.relevance);

  return results.slice(0, 20);
}

export function getDocumentsByCategory(category: string): Document[] {
  return documents.filter(doc => doc.category === category);
}
