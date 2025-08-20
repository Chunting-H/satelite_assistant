// components/Satellite/SatelliteChat.jsx - 修复版本：确保过滤器对象结构完整
import React, { useState, useRef, useEffect } from 'react';

import { querySatellites } from '../../services/api';

const SatelliteChat = ({ satellites, onFiltersChange, onSearchChange }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: '您好！我是卫星查询助手。您可以向我询问关于卫星的任何问题，比如：\n\n• "查找所有中国的卫星"\n• "显示2020年后发射的卫星"\n• "找到所有正在运行的气象卫星"\n• "筛选太阳同步轨道的卫星"\n\n请告诉我您想要查找什么样的卫星？',
      timestamp: Date.now()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedModel, setSelectedModel] = useState('deepseek'); // 默认使用ChatGPT
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 🔧 修复：创建默认过滤器模板
  const createDefaultFilters = () => ({
    launchDateRange: { start: '', end: '' },
    status: [],
    owner: [],
    orbitType: [],
    orbitPeriodRange: { min: '', max: '' },
    revisitRange: { min: '', max: '' },
    crossingTimeRange: { start: '', end: '' },
    orbitLongitudeRange: { min: '', max: '' },
    launchSite: [],
    endDateRange: { start: '', end: '' }
  });

  // 🔧 修复：安全创建过滤器函数
  const createSafeFilters = (partialFilters) => {
    const defaultFilters = createDefaultFilters();
    const safeFilters = { ...defaultFilters };

    // 安全地合并部分过滤器
    if (partialFilters && typeof partialFilters === 'object') {
      Object.keys(partialFilters).forEach(key => {
        if (key in defaultFilters) {
          const value = partialFilters[key];

          // 检查数组字段
          if (Array.isArray(defaultFilters[key])) {
            safeFilters[key] = Array.isArray(value) ? value : [];
          }
          // 检查对象字段
          else if (typeof defaultFilters[key] === 'object' && defaultFilters[key] !== null) {
            safeFilters[key] = (value && typeof value === 'object') ? { ...defaultFilters[key], ...value } : defaultFilters[key];
          }
          // 其他字段
          else {
            safeFilters[key] = value;
          }
        }
      });
    }

    return safeFilters;
  };

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 处理用户输入
  const handleSendMessage = async (message) => {
    if (!message.trim() || isProcessing) return;

    // 🔧 新增：特殊处理清除命令
    if (message.includes('清除') && message.includes('筛选')) {
      onFiltersChange(createDefaultFilters());
      onSearchChange('');

      const clearMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '✅ 已清除所有筛选条件和搜索关键词',
        timestamp: Date.now()
      };

      setMessages(prev => [...prev,
      {
        id: Date.now(),
        role: 'user',
        content: message,
        timestamp: Date.now()
      },
        clearMessage
      ]);

      return;
    }

    // 添加用户消息
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsProcessing(true);

    try {
      // 分析用户意图并执行相应操作
      const response = await processUserQuery(message, satellites);

      // 添加助手回复
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.message,
        timestamp: Date.now()
      };

      setMessages(prev => [...prev, assistantMessage]);

      // 🔧 修复：安全应用过滤器并等待应用完成
      if (response.filters && Object.keys(response.filters).length > 0) {
        const safeFilters = createSafeFilters(response.filters);
        console.log('📋 应用安全过滤器:', safeFilters);
        // 先清空搜索，避免冲突
        if (response.searchQuery === '') {
          onSearchChange('');
        }
        onFiltersChange(safeFilters);
      }

      if (response.searchQuery) {
        console.log('🔍 应用搜索查询:', response.searchQuery);
        // 清空筛选器，避免冲突
        onFiltersChange(createDefaultFilters());
        onSearchChange(response.searchQuery);
      }

    } catch (error) {
      console.error('处理查询失败:', error);

      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '抱歉，处理您的请求时出现了问题。请尝试重新描述您的需求。',
        timestamp: Date.now()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
    }
  };

  // 🔧 修复：处理用户查询，调用AI模型API
  const processUserQuery = async (query, satelliteList) => {
    try {

      // 准备卫星数据上下文，包含当前筛选状态
      const currentFilteredCount = satellites.length; // 使用props中的satellites
      const satellitesContext = {
        totalInDatabase: satelliteList.length,
        currentFiltered: currentFilteredCount,
        samples: satellites.slice(0, 10).map(s => ({
          name: s.fullName,
          status: s.status,
          owner: s.owner,
          country: s.country
        }))
      };

      console.log('🤖 调用AI模型:', selectedModel);

      // 调用API
      const response = await querySatellites(
        query,
        selectedModel,
        JSON.stringify(satellitesContext)
      );

      let message = '';
      let partialFilters = {};
      let searchQuery = '';

      if (response.success) {
        message = response.answer;
        partialFilters = response.filters || {};
        searchQuery = response.search_query || '';

        console.log('🎯 AI返回结果:', { message: message.substring(0, 100), partialFilters, searchQuery });
      } else {
        // API调用失败，回退到原有逻辑
        console.warn('⚠️ API调用失败，使用备用逻辑');
        const fallbackResult = await processUserQueryFallback(query, satelliteList);
        message = fallbackResult.message;
        partialFilters = fallbackResult.filters;
        searchQuery = fallbackResult.searchQuery;
      }

      return {
        message,
        filters: Object.keys(partialFilters).length > 0 ? partialFilters : null,
        searchQuery: searchQuery || null
      };

    } catch (error) {
      console.error('❌ 处理查询时出错:', error);

      // 出错时回退到原有逻辑
      return await processUserQueryFallback(query, satelliteList);
    }
  };

  // 🔧 备用处理逻辑（保留原有的关键词匹配逻辑）
  const processUserQueryFallback = async (query, satelliteList) => {
    const queryLower = query.toLowerCase();
    let partialFilters = {};
    let searchQuery = '';
    let message = '';

    try {
      // 分析查询意图（保留原有逻辑）
      if (queryLower.includes('中国') || queryLower.includes('china')) {
        partialFilters.owner = ['China', '中国'];
        const count = satelliteList.filter(s =>
          s.country === '中国' || s.owner === 'China' ||
          (s.country && s.country.includes('中国')) ||
          (s.owner && s.owner.includes('China'))
        ).length;
        message = `已为您筛选出中国的卫星，共找到 ${count} 颗。`;

      } else if (queryLower.includes('美国') || queryLower.includes('usa') || queryLower.includes('united states')) {
        partialFilters.owner = ['United States', '美国'];
        const count = satelliteList.filter(s =>
          s.country === '美国' || s.owner === 'United States' ||
          (s.country && s.country.includes('美国')) ||
          (s.owner && s.owner.includes('United States'))
        ).length;
        message = `已为您筛选出美国的卫星，共找到 ${count} 颗。`;

      } else if (queryLower.includes('正在运行') || queryLower.includes('operational') || queryLower.includes('在轨运行')) {
        partialFilters.status = ['Operational'];
        const count = satelliteList.filter(s => s.status === 'Operational').length;
        message = `已为您筛选出正在运行的卫星，共 ${count} 颗。`;

      } else if (queryLower.includes('高分') || queryLower.includes('gf')) {
        searchQuery = '高分';
        message = `已为您搜索高分系列卫星。`;

      } else if (queryLower.includes('风云')) {
        searchQuery = '风云';
        message = `已为您搜索气象卫星，主要包括风云系列卫星。`;

      } else {
        // 通用搜索
        searchQuery = query;
        message = `已为您搜索包含"${query}"的卫星。如果没有找到结果，请尝试使用其他关键词。`;
      }

      return {
        message,
        filters: Object.keys(partialFilters).length > 0 ? partialFilters : null,
        searchQuery: searchQuery !== query ? searchQuery : null
      };

    } catch (error) {
      console.error('备用处理查询时出错:', error);
      return {
        message: '处理您的查询时出现问题，请重试。',
        filters: null,
        searchQuery: null
      };
    }
  };

  // 生成统计信息
  const generateStatistics = (satelliteList) => {
    try {
      const stats = {
        total: satelliteList.length,
        operational: satelliteList.filter(s => s.status === 'Operational').length,
        decayed: satelliteList.filter(s => s.status === 'Decayed').length,
        nonoperational: satelliteList.filter(s => s.status === 'Nonoperational').length,
        usa: satelliteList.filter(s =>
          s.country === '美国' || s.owner === 'United States' ||
          (s.country && s.country.includes('美国')) ||
          (s.owner && s.owner.includes('United States'))
        ).length,
        china: satelliteList.filter(s =>
          s.country === '中国' || s.owner === 'China' ||
          (s.country && s.country.includes('中国')) ||
          (s.owner && s.owner.includes('China'))
        ).length,
        europe: satelliteList.filter(s =>
          s.owner === 'European Space Agency' ||
          (s.owner && s.owner.includes('Europe'))
        ).length
      };
      return stats;
    } catch (error) {
      console.error('生成统计信息时出错:', error);
      return { total: 0, operational: 0, decayed: 0, nonoperational: 0, usa: 0, china: 0, europe: 0 };
    }
  };

  // 快速操作按钮
  const quickActions = [
    { label: '中国卫星', query: '中国卫星' },
    { label: '美国卫星', query: '美国卫星' },
    { label: '正在运行', query: '正在运行的卫星' },
    { label: '高分系列', query: '高分卫星' },
    { label: '风云系列', query: '风云气象卫星' },
    { label: '清除筛选', query: '清除所有筛选条件' },
    { label: '统计信息', query: '显示卫星统计信息' }
  ];

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(inputValue);
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // 🤖 机器人图标组件
  const RobotIcon = () => (
    <div className="relative">
      <svg
        className="w-6 h-6 text-blue-500 animate-pulse"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* 机器人头部 */}
        <rect x="6" y="6" width="12" height="10" rx="2" strokeWidth="2" fill="currentColor" fillOpacity="0.1" />
        {/* 机器人眼睛 */}
        <circle cx="9" cy="9" r="1" fill="currentColor" />
        <circle cx="15" cy="9" r="1" fill="currentColor" />
        {/* 机器人嘴巴 */}
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 13h4" />
        {/* 机器人天线 */}
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4" />
        <circle cx="12" cy="3" r="1" fill="currentColor" />
        {/* 机器人身体 */}
        <rect x="8" y="16" width="8" height="6" rx="1" strokeWidth="2" fill="currentColor" fillOpacity="0.05" />
        {/* 机器人手臂 */}
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18h2m8 0h2" />
      </svg>

      {/* 🔥 在线状态指示器 */}
      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white animate-ping"></div>
      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white"></div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 🎨 优化后的头部 - 简洁设计 */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center space-x-3">
          <RobotIcon />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              智能查询助手
              <span className="ml-2 text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full font-medium">
                AI 助手
              </span>
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              告诉我您想查找什么样的卫星
            </p>
          </div>

          {/* 状态指示器 */}
          <div className="flex items-center space-x-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span>在线</span>
          </div>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className="flex items-start space-x-2 max-w-full" style={{ maxWidth: '280px' }}>
              {/* 为助手消息添加头像 */}
              {message.role === 'assistant' && (
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                  </svg>
                </div>
              )}

              <div
                className={`px-4 py-2 rounded-lg ${message.role === 'user'
                  ? 'bg-blue-500 text-white ml-auto'
                  : 'bg-gray-100 text-gray-800'
                  }`}
              >
                <div className="text-sm break-words" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {message.content}
                </div>
                <div
                  className={`text-xs mt-1 ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}
                >
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="flex justify-start">
            <div className="flex items-start space-x-2">
              <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-blue-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <div className="bg-gray-100 text-gray-800 px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
                  </div>
                  <span className="text-sm">正在处理...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 🎨 优化后的操作区域 - 模型选择器移到这里 */}
      <div className="border-t border-gray-200 bg-gray-50">
        {/* 模型选择区域 */}
        <div className="px-4 py-3 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <span className="text-sm font-medium text-gray-700">AI模型:</span>
              </div>

              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="text-sm bg-white border border-gray-300 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm"
                disabled={isProcessing}
              >
                <option value="deepseek">🔍 DeepSeek</option>
                <option value="chatgpt">🤖 ChatGPT</option>
                <option value="qwen">🧠 通义千问</option>
              </select>
            </div>

          </div>
        </div>

        {/* 快速操作区域 */}
        <div className="p-4">
          <div className="mb-3">
            <div className="flex items-center space-x-2 mb-2">
              <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <p className="text-xs text-gray-500 font-medium">快速操作：</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  onClick={() => handleSendMessage(action.query)}
                  disabled={isProcessing}
                  className="text-xs bg-white hover:bg-blue-50 border border-gray-200 hover:border-blue-200 text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>

          {/* 输入框区域 */}
          <div className="flex space-x-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="描述您要查找的卫星..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none bg-white"
              rows={2}
              disabled={isProcessing}
            />
            <button
              onClick={() => handleSendMessage(inputValue)}
              disabled={!inputValue.trim() || isProcessing}
              className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg flex items-center justify-center min-w-[44px]"
            >
              {isProcessing ? (
                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SatelliteChat;