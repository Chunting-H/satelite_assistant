// components/Satellite/SatelliteChat.jsx - 修复版本：确保过滤器对象结构完整
import React, { useState, useRef, useEffect } from 'react';

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

      // 🔧 修复：安全应用过滤器
      if (response.filters) {
        const safeFilters = createSafeFilters(response.filters);
        console.log('📋 应用安全过滤器:', safeFilters);
        onFiltersChange(safeFilters);
      }

      if (response.searchQuery) {
        console.log('🔍 应用搜索查询:', response.searchQuery);
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

  // 🔧 修复：处理用户查询，确保返回安全的过滤器
  const processUserQuery = async (query, satelliteList) => {
    const queryLower = query.toLowerCase();
    let partialFilters = {};
    let searchQuery = '';
    let message = '';

    try {
      // 分析查询意图
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

      } else if (queryLower.includes('欧洲') || queryLower.includes('europe') || queryLower.includes('esa')) {
        partialFilters.owner = ['European Space Agency', 'Europe'];
        message = `已为您筛选出欧洲的卫星。`;

      } else if (queryLower.includes('正在运行') || queryLower.includes('operational') || queryLower.includes('在轨运行')) {
        partialFilters.status = ['Operational'];
        const count = satelliteList.filter(s => s.status === 'Operational').length;
        message = `已为您筛选出正在运行的卫星，共 ${count} 颗。`;

      } else if (queryLower.includes('失效') || queryLower.includes('decayed')) {
        partialFilters.status = ['Decayed'];
        const count = satelliteList.filter(s => s.status === 'Decayed').length;
        message = `已为您筛选出已失效的卫星，共 ${count} 颗。`;

      } else if (queryLower.includes('太阳同步') || queryLower.includes('sun-sync') || queryLower.includes('太阳同步轨道')) {
        partialFilters.orbitType = ['LLEO_S'];
        const count = satelliteList.filter(s => s.orbitType === 'LLEO_S').length;
        message = `已为您筛选出太阳同步轨道的卫星，共 ${count} 颗。`;

      } else if (queryLower.includes('地球同步') || queryLower.includes('geo') || queryLower.includes('地球静止')) {
        partialFilters.orbitType = ['GEO_S'];
        const count = satelliteList.filter(s => s.orbitType === 'GEO_S').length;
        message = `已为您筛选出地球同步轨道的卫星，共 ${count} 颗。`;

      } else if (queryLower.includes('2020') || queryLower.includes('2021') || queryLower.includes('2022') || queryLower.includes('2023') || queryLower.includes('2024')) {
        const yearMatch = queryLower.match(/20\d{2}/);
        if (yearMatch) {
          const year = yearMatch[0];
          partialFilters.launchDateRange = { start: `${year}-01-01`, end: `${year}-12-31` };
          const count = satelliteList.filter(s =>
            s.launchDate && s.launchDate.includes(year)
          ).length;
          message = `已为您筛选出${year}年发射的卫星，共 ${count} 颗。`;
        }

      } else if (queryLower.includes('气象') || queryLower.includes('weather') || queryLower.includes('风云')) {
        searchQuery = '风云';
        message = `已为您搜索气象卫星，主要包括风云系列卫星。`;

      } else if (queryLower.includes('高分') || queryLower.includes('gf')) {
        searchQuery = '高分';
        message = `已为您搜索高分系列卫星。`;

      } else if (queryLower.includes('landsat')) {
        searchQuery = 'Landsat';
        message = `已为您搜索Landsat系列卫星。`;

      } else if (queryLower.includes('sentinel') || queryLower.includes('哨兵')) {
        searchQuery = 'Sentinel';
        message = `已为您搜索Sentinel（哨兵）系列卫星。`;

      } else if (queryLower.includes('清除') || queryLower.includes('清空') || queryLower.includes('reset')) {
        partialFilters = createDefaultFilters(); // 🔧 使用完整的默认过滤器
        searchQuery = '';
        message = `已清除所有筛选条件，现在显示所有 ${satelliteList.length} 颗卫星。`;

      } else if (queryLower.includes('统计') || queryLower.includes('count') || queryLower.includes('多少')) {
        const stats = generateStatistics(satelliteList);
        message = `当前卫星统计信息：\n\n📊 **总数**: ${stats.total} 颗\n\n🔄 **运行状态**:\n• 正在运行: ${stats.operational} 颗\n• 已失效: ${stats.decayed} 颗\n• 非运行: ${stats.nonoperational} 颗\n\n🌍 **主要国家/地区**:\n• 美国: ${stats.usa} 颗\n• 中国: ${stats.china} 颗\n• 欧洲: ${stats.europe} 颗`;

      } else {
        // 通用搜索
        searchQuery = query;
        message = `已为您搜索包含"${query}"的卫星。如果没有找到结果，请尝试使用其他关键词，如：\n\n• 国家名称（中国、美国、欧洲）\n• 卫星系列（高分、风云、Landsat）\n• 运行状态（正在运行、失效）\n• 轨道类型（太阳同步、地球同步）`;
      }

      return {
        message,
        filters: Object.keys(partialFilters).length > 0 ? partialFilters : null,
        searchQuery: searchQuery !== query ? searchQuery : null
      };

    } catch (error) {
      console.error('处理查询时出错:', error);
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
        <rect x="6" y="6" width="12" height="10" rx="2" strokeWidth="2" fill="currentColor" fillOpacity="0.1"/>
        {/* 机器人眼睛 */}
        <circle cx="9" cy="9" r="1" fill="currentColor"/>
        <circle cx="15" cy="9" r="1" fill="currentColor"/>
        {/* 机器人嘴巴 */}
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 13h4"/>
        {/* 机器人天线 */}
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4"/>
        <circle cx="12" cy="3" r="1" fill="currentColor"/>
        {/* 机器人身体 */}
        <rect x="8" y="16" width="8" height="6" rx="1" strokeWidth="2" fill="currentColor" fillOpacity="0.05"/>
        {/* 机器人手臂 */}
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18h2m8 0h2"/>
      </svg>

      {/* 🔥 在线状态指示器 */}
      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white animate-ping"></div>
      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white"></div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 修改后的头部 - 添加机器人图标 */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <RobotIcon />
            <div>
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
          </div>

          {/* 添加状态指示器 */}
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span>在线</span>
            </div>
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
            <div className="flex items-start space-x-2 max-w-xs lg:max-w-md">
              {/* 为助手消息添加头像 */}
              {message.role === 'assistant' && (
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                  </svg>
                </div>
              )}

              <div
                className={`px-4 py-2 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white ml-auto'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <div className="whitespace-pre-line text-sm">
                  {message.content}
                </div>
                <div
                  className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
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
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
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

      {/* 快速操作 */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="mb-3">
          <div className="flex items-center space-x-2 mb-2">
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
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

        {/* 输入框 */}
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
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
  );
};

export default SatelliteChat;