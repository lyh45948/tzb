import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageCircle, Send, Lightbulb } from 'lucide-react';
import { findAnswer, getSimilarQuestions } from '../utils/qa';

export function QASection() {
  const { t } = useTranslation();
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<string | null>(null);
  const [similarQuestions, setSimilarQuestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    
    setTimeout(() => {
      const result = findAnswer(question);
      const similar = getSimilarQuestions(question);
      setAnswer(result);
      setSimilarQuestions(similar);
      setLoading(false);
    }, 500);
  };

  const handleQuestionClick = (q: string) => {
    setQuestion(q);
    handleSubmit(new Event('submit') as any);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8">
        <div className="flex items-center space-x-3 mb-6">
          <MessageCircle className="w-8 h-8 text-blue-600" />
          <h2 className="text-2xl font-bold text-gray-800 dark:text-white">
            Ask About H30 INS
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="mb-6">
          <div className="flex space-x-4">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={t('askQuestion')}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span>{t('submit')}</span>
                </>
              )}
            </button>
          </div>
        </form>

        {loading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Searching for answer...</p>
          </div>
        )}

        {answer && !loading && (
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-3">
              {t('answer')}:
            </h3>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">
              {answer}
            </p>
          </div>
        )}

        {!answer && !loading && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            Ask a question about H30 INS module usage, configuration, or troubleshooting
          </div>
        )}

        {similarQuestions.length > 0 && !loading && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-3 flex items-center">
              <Lightbulb className="w-5 h-5 mr-2 text-yellow-500" />
              Similar Questions
            </h3>
            <div className="space-y-2">
              {similarQuestions.map((q, index) => (
                <button
                  key={index}
                  onClick={() => handleQuestionClick(q)}
                  className="w-full text-left px-4 py-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors text-gray-700 dark:text-gray-300"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
          Tips for Better Answers
        </h3>
        <ul className="space-y-2 text-gray-700 dark:text-gray-300">
          <li className="flex items-start space-x-2">
            <span className="text-blue-600 dark:text-blue-400 mt-1">•</span>
            <span>Be specific about the issue or question</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-blue-600 dark:text-blue-400 mt-1">•</span>
            <span>Include relevant details like model number (H30, H30mini)</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-blue-600 dark:text-blue-400 mt-1">•</span>
            <span>Mention the interface you're using (serial, Ethernet, I2C)</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-blue-600 dark:text-blue-400 mt-1">•</span>
            <span>Check the documentation first for common issues</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
