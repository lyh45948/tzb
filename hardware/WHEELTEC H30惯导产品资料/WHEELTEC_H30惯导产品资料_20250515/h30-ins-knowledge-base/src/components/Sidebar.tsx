import { useTranslation } from 'react-i18next';
import { FileText, Code, Settings, Cpu, Box, HelpCircle, RotateCcw, Phone } from 'lucide-react';

interface SidebarProps {
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
}

export function Sidebar({ selectedCategory, onCategoryChange }: SidebarProps) {
  const { t } = useTranslation();

  const categories = [
    { id: 'all', name: 'All Categories / 所有分类', icon: FileText },
    { id: 'userManual', name: t('userManual'), icon: FileText },
    { id: 'rosSdk', name: t('rosSdk'), icon: Code },
    { id: 'softwareTools', name: t('softwareTools'), icon: Settings },
    { id: 'chipManual', name: t('chipManual'), icon: Cpu },
    { id: 'mechanicalModels', name: t('mechanicalModels'), icon: Box },
    { id: 'examples', name: t('examples'), icon: Code },
    { id: 'updateLog', name: t('updateLog'), icon: RotateCcw },
    { id: 'contactUs', name: t('contactUs'), icon: Phone },
  ];

  return (
    <aside className="w-64 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 fixed left-0 top-16 bottom-0 overflow-y-auto">
      <nav className="p-4">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
          Categories
        </h2>
        <ul className="space-y-1">
          {categories.map((category) => {
            const Icon = category.icon;
            return (
              <li key={category.id}>
                <button
                  onClick={() => onCategoryChange(category.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md transition-colors text-left ${
                    selectedCategory === category.id
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-700 hover:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-800'
                  }`}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span className="truncate">{category.name}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="absolute bottom-4 left-4 right-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <div className="flex items-start space-x-2">
          <HelpCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-gray-800 dark:text-white mb-1">
              Need Help?
            </h3>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Check our Q&A section for common questions and answers.
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
