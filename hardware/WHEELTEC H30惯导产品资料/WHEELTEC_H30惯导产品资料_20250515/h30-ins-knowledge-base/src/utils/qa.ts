import { qaData } from '../data/qaData';

export function findAnswer(question: string): string | null {
  const lowerQuestion = question.toLowerCase();
  
  // Find matching question
  for (const qa of qaData) {
    if (qa.question.toLowerCase().includes(lowerQuestion)) {
      return qa.answer;
    }
  }
  
  // If no exact match, try keyword matching
  const keywords = lowerQuestion.split(' ').filter(w => w.length > 2);
  let bestMatch: string | null = null;
  let maxMatches = 0;

  for (const qa of qaData) {
    const answer = qa.answer.toLowerCase();
    let matches = 0;
    for (const keyword of keywords) {
      if (answer.includes(keyword)) {
        matches++;
      }
    }
    if (matches > maxMatches) {
      maxMatches = matches;
      bestMatch = qa.answer;
    }
  }

  return bestMatch;
}

export function getSimilarQuestions(question: string, limit: number = 3): string[] {
  const lowerQuestion = question.toLowerCase();
  const keywords = lowerQuestion.split(' ').filter(w => w.length > 2);
  
  const scores = qaData.map(qa => {
    let score = 0;
    const qText = qa.question.toLowerCase();
    
    keywords.forEach(keyword => {
      if (qText.includes(keyword)) score++;
    });
    
    return { question: qa.question, score };
  });

  return scores
    .filter(s => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(s => s.question);
}
