import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
  en: {
    translation: {
      // Header
      title: "WHEELTEC H30 INS Knowledge Base",
      searchPlaceholder: "Search documents, code, or ask a question...",
      search: "Search",
      favorites: "Favorites",
      history: "History",
      language: "Language",
      theme: "Theme",
      
      // Categories
      userManual: "User Manual",
      rosSdk: "ROS SDK",
      softwareTools: "Software Tools",
      chipManual: "Chip Manual & Schematics",
      mechanicalModels: "Mechanical Models",
      examples: "Code Examples",
      updateLog: "Update Log",
      contactUs: "Contact Us",
      
      // Document Types
      pdfDocument: "PDF Document",
      codeFile: "Code File",
      zipFile: "Zip File",
      
      // Actions
      download: "Download",
      viewCode: "View Code",
      viewPdf: "View PDF",
      addToFavorites: "Add to Favorites",
      removeFromFavorites: "Remove from Favorites",
      
      // Sections
      searchResults: "Search Results",
      noResults: "No results found",
      recentSearches: "Recent Searches",
      clearHistory: "Clear History",
      
      // Q&A
      askQuestion: "Ask a question about H30 INS module",
      submit: "Submit",
      answer: "Answer",
      
      // Footer
      copyright: "© 2025 WHEELTEC. All rights reserved.",
      version: "Version 1.0.0"
    }
  },
  zh: {
    translation: {
      // Header
      title: "WHEELTEC H30 惯导知识库",
      searchPlaceholder: "搜索文档、代码或提问...",
      search: "搜索",
      favorites: "收藏夹",
      history: "搜索历史",
      language: "语言",
      theme: "主题",
      
      // Categories
      userManual: "用户手册",
      rosSdk: "ROS SDK",
      softwareTools: "软件工具",
      chipManual: "芯片手册与原理图",
      mechanicalModels: "机械模型",
      examples: "代码例程",
      updateLog: "更新日志",
      contactUs: "联系我们",
      
      // Document Types
      pdfDocument: "PDF文档",
      codeFile: "代码文件",
      zipFile: "压缩文件",
      
      // Actions
      download: "下载",
      viewCode: "查看代码",
      viewPdf: "查看PDF",
      addToFavorites: "添加到收藏",
      removeFromFavorites: "从收藏移除",
      
      // Sections
      searchResults: "搜索结果",
      noResults: "未找到结果",
      recentSearches: "最近搜索",
      clearHistory: "清除历史",
      
      // Q&A
      askQuestion: "提问关于H30惯导模块的问题",
      submit: "提交",
      answer: "回答",
      
      // Footer
      copyright: "© 2025 轮趣科技. 保留所有权利.",
      version: "版本 1.0.0"
    }
  }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'zh',
    lng: 'zh',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
