// components/Chat/EnhancedStreamingMessage.jsx - 修复图表显示位置和数据获取时机
import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SatelliteCharts from './SatelliteCharts';
import MessageActions from './MessageActions';

const EnhancedStreamingMessage = ({
  message,
  isUser,
  timestamp,
  isStreaming = false,
  accumulatedContent = "",
  satellites = [],
  isClarification,
  isClarificationResponse,
  isParameterConfirmation = false,
  onPlanOutputComplete
}) => {
  const [displayContent, setDisplayContent] = useState(message || "");
  const [showVisualization, setShowVisualization] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [extractedSatellites, setExtractedSatellites] = useState([]);
  const [finalSatellites, setFinalSatellites] = useState([]); // 🆕 最终确定的卫星列表
  const mountedRef = useRef(true);
  const lastContentRef = useRef("");
  const hasExtractedRef = useRef(false); // 🆕 是否已经提取过
  const extractionTimeoutRef = useRef(null);
  const lastSatellitesRef = useRef([]);
  const [chartReady, setChartReady] = useState(false);
  const chartCheckTimeoutRef = useRef(null);
  const [forceShowChart, setForceShowChart] = useState(false);
  const firstExtractionDoneRef = useRef(false); // 🆕 第一次提取是否完成
  const secondExtractionDoneRef = useRef(false); // 🆕 第二次提取是否完成
  const [containerWidth, setContainerWidth] = useState(0);
  const messageContainerRef = useRef(null);
  const hasNotifiedPlanCompleteRef = useRef(false); // 🆕 是否已通知方案输出完成

  // 格式化时间
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // 生成消息ID
  const messageId = timestamp ? new Date(timestamp).getTime().toString() : Date.now().toString();

  // 🔧 新增：内容预处理函数，统一换行符和格式
  // 检测是否是方案生成内容
  const isPlanContent = displayContent.includes('# ') ||
                       displayContent.includes('## ') ||
                       displayContent.includes('### ') ||
                       displayContent.includes('卫星组成') ||
                       displayContent.includes('| 卫星名称 |');

  // 🆕 从内容中提取卫星（增强版）
  const extractSatellitesFromContent = async (content) => {
    if (!content || content.length < 50) return [];

    console.log('🔍 开始从内容中提取卫星...');

    const foundSatellites = new Set();

    // 方法1：专门匹配"推荐卫星："这一行
    const recommendPattern = /推荐卫星[：:]\s*([^\n]+)/i;
    const recommendMatch = content.match(recommendPattern);

    if (recommendMatch && recommendMatch[1]) {
        console.log('✅ 找到推荐卫星行:', recommendMatch[1]);

        // 使用 extractSatelliteNamesWithCache 进行提取
        const { extractSatelliteNamesWithCache } = await import('../../services/satelliteExtractor');
        const extracted = await extractSatelliteNamesWithCache(recommendMatch[1]);
        extracted.forEach(sat => foundSatellites.add(sat));

        // 如果成功提取到卫星，直接返回
        if (foundSatellites.size > 0) {
            return Array.from(foundSatellites);
        }
    }

    const satellites = Array.from(foundSatellites);
    console.log('✅ 最终提取到的卫星列表:', satellites);
    return satellites;
};

  // 更新显示内容
  useEffect(() => {
    let newContent = "";

    if (isStreaming && accumulatedContent) {
      newContent = accumulatedContent;
    } else if (!isStreaming && message) {
      newContent = message;
    } else if (message) {
      newContent = message;
    }

    // 🔧 新增：应用内容预处理

    if (newContent && newContent !== lastContentRef.current) {
      console.log('📝 更新消息内容:', newContent.length, '字符');
      setDisplayContent(newContent);
      lastContentRef.current = newContent;

    }
  }, [isStreaming, accumulatedContent, message]);
  // 🆕 当“输出结果”完成渲染后通知上层（仅一次）
  useEffect(() => {
    if (
      !isUser &&
      !isStreaming &&
      isPlanContent &&
      displayContent &&
      displayContent.length > 50 &&
      !hasNotifiedPlanCompleteRef.current
    ) {
      hasNotifiedPlanCompleteRef.current = true;
      // 轻微延迟，确保DOM渲染完成
      setTimeout(() => {
        if (typeof onPlanOutputComplete === 'function') {
          onPlanOutputComplete({ messageId, content: displayContent });
        }
      }, 300);
    }
  }, [isUser, isStreaming, isPlanContent, displayContent, messageId, onPlanOutputComplete]);


  useEffect(() => {
    if (!messageContainerRef.current) return;

    const resizeObserver = new ResizeObserver(entries => {
      for (let entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    resizeObserver.observe(messageContainerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);
  // 准备图表数据
  const prepareChartData = (satelliteList) => {
    if (!satelliteList || satelliteList.length === 0) {
      console.log('❌ 准备图表数据失败：卫星列表为空');
      return null;
    }

    console.log('📊 准备图表数据，卫星列表:', satelliteList);

    // 生成模拟的协同关系
    const collaborations = [];
    for (let i = 0; i < satelliteList.length; i++) {
      for (let j = i + 1; j < satelliteList.length; j++) {
        if (Math.random() > 0.4) {
          collaborations.push({
            satellite1: satelliteList[i],
            satellite2: satelliteList[j],
            frequency: Math.floor(Math.random() * 20) + 5,
            type: getCollaborationType(satelliteList[i], satelliteList[j]),
            effectiveness: 0.7 + Math.random() * 0.2
          });
        }
      }
    }

    const chartData = {
      satellites: satelliteList.map(name => ({
        name,
        country: getCountryFromSatelliteName(name),
        launchDate: getLaunchDate(name),
        importance: Math.floor(Math.random() * 5) + 5,
        capabilities: generateCapabilities(name)
      })),
      collaborations,
      summary_stats: {
        total_satellites: satelliteList.length,
        total_collaborations: collaborations.length,
        avg_collaboration_frequency: collaborations.length > 0 ?
          collaborations.reduce((sum, c) => sum + c.frequency, 0) / collaborations.length : 0,
        network_density: satelliteList.length > 1 ?
          collaborations.length / (satelliteList.length * (satelliteList.length - 1) / 2) : 0
      },
      recommendations: generateRecommendations(satelliteList, collaborations)
    };

    console.log('✅ 图表数据准备完成:', chartData);
    return chartData;
  };

  useEffect(() => {
    // 当消息完成且包含方案内容时，自动提取并显示
    if (!isStreaming && displayContent && isPlanContent) {
      const extractAndShowVisualization = async () => {
        try {
          // 从内容中提取卫星
          // console.log(displayContent);
          const satellites = await extractSatellitesFromContent(displayContent);
          if (satellites && satellites.length > 0) {
            console.log('✅ 自动提取到卫星:', satellites);
            setFinalSatellites(satellites);

            // 准备并显示图表
            const chartData = prepareChartData(satellites);
            if (chartData) {
              setChartData(chartData);
              setChartReady(true);
              setShowVisualization(true);
            }
          }
        } catch (error) {
          console.error('提取卫星失败:', error);
        }
      };

      // 延迟执行以确保内容渲染完成
      setTimeout(extractAndShowVisualization, 500);
    }
  }, [isStreaming, displayContent, isPlanContent]);


  // 监听props中的卫星数据变化
  useEffect(() => {
    // 🔧 添加条件：只有当消息应该显示图表时才处理卫星数据
    if (satellites && satellites.length > 0 && !hasExtractedRef.current) {
      // 🆕 检查是否是方案消息
      const isPlanContent = displayContent.includes('# ') ||
                           displayContent.includes('## ') ||
                           displayContent.includes('### ') ||
                           displayContent.includes('卫星组成') ||
                           displayContent.includes('| 卫星名称 |');

      // 只有方案消息才处理卫星数据
      if (isPlanContent) {
        console.log('📊 收到卫星数据 props:', satellites);
        hasExtractedRef.current = true;
        setExtractedSatellites(satellites);
        setFinalSatellites(satellites);
        console.log('📊 '+inalSatellites.length)
        // 准备图表数据
        const chartData = prepareChartData(satellites);
        if (chartData) {
          setChartData(chartData);
          setChartReady(true);
          setShowVisualization(true);
        }
      }
    }
  }, [satellites, displayContent]);  // 🔧 添加 displayContent 依赖

  // 🆕 确保图表在适当时机显示
  useEffect(() => {
    if (!isUser && !isStreaming && chartReady && finalSatellites.length > 0 && !showVisualization) {
      // 确保图表在内容完全渲染后显示
      const showTimeout = setTimeout(() => {
        setShowVisualization(true);
        console.log('📊 显示图表（在内容下方）');
      }, 500);

      return () => clearTimeout(showTimeout);
    }
  }, [isStreaming, chartReady, finalSatellites, isUser, showVisualization]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (extractionTimeoutRef.current) {
        clearTimeout(extractionTimeoutRef.current);
      }
      if (chartCheckTimeoutRef.current) {
        clearTimeout(chartCheckTimeoutRef.current);
      }
    };
  }, []);

  // 渲染内容
  const renderContent = (content) => {
    if (!content) return null;
    if (isUser) {
      return <p className="whitespace-pre-wrap break-words">{content}</p>;
    }

    try {
      return (
        <div className="prose prose-gray prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({node, ...props}) => <h1 className="text-xl font-bold mb-3 text-gray-900" {...props} />,
              h2: ({node, ...props}) => <h2 className="text-lg font-semibold mb-2 text-gray-800" {...props} />,
              h3: ({node, ...props}) => <h3 className="text-md font-medium mb-2 text-gray-700" {...props} />,
              p: ({node, ...props}) => <p className="mb-2 text-gray-700 leading-relaxed" {...props} />,
              ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-2 text-gray-700" {...props} />,
              ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-2 text-gray-700" {...props} />,
              li: ({node, ...props}) => <li className="mb-1" {...props} />,
              strong: ({node, ...props}) => <strong className="font-semibold text-gray-800" {...props} />,

              table: ({node, ...props}) => (
                <div className="overflow-x-auto my-4">
                  <table className="min-w-full border-collapse border border-gray-300" {...props} />
                </div>
              ),

              thead: ({node, ...props}) => (
                <thead className="bg-gradient-to-r from-blue-50 to-indigo-50" {...props} />
              ),

              th: ({node, ...props}) => (
                <th
                  className="border-b-2 border-gray-300 px-4 py-3 text-left text-xs font-bold text-gray-800 uppercase tracking-wider bg-gradient-to-r from-blue-50 to-indigo-50 whitespace-nowrap"
                  {...props}
                />
              ),

              td: ({node, children, ...props}) => {
                const isScore = /^\d+$/.test(children) &&
                                parseInt(children) >= 0 &&
                                parseInt(children) <= 100 &&
                                children.length <= 3;

                return (
                  <td
                    className={`border-b border-gray-200 px-4 py-3 text-sm whitespace-nowrap ${
                      isScore 
                        ? 'text-center font-semibold text-blue-600' 
                        : 'text-gray-700'
                    }`}
                    {...props}
                  >
                    {children}
                  </td>
                );
              },

              tbody: ({node, ...props}) => (
                <tbody className="divide-y divide-gray-200" {...props} />
              ),

              code: ({node, inline, ...props}) =>
                inline ?
                  <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-gray-800" {...props} /> :
                  <code className="block bg-gray-100 p-2 rounded text-sm font-mono text-gray-800 overflow-x-auto" {...props} />
            }}
          >
            {displayContent}
          </ReactMarkdown>
        </div>
      );
    } catch (error) {
      console.error('Markdown渲染出错:', error);
    }
  };


  // 手动切换可视化显示
  const toggleVisualization = () => {
    const satelliteData = finalSatellites.length > 0 ? finalSatellites : extractedSatellites;

    if (!showVisualization && satelliteData && satelliteData.length > 0) {
      // 如果还没有准备图表数据，现在准备
      if (!chartData) {
        const preparedData = prepareChartData(satelliteData);
        if (preparedData) {
          setChartData(preparedData);
          setChartReady(true);
        }
      }
      setShowVisualization(true);
      console.log('📊 手动显示图表');
    } else {
      setShowVisualization(false);
      console.log('📊 手动隐藏图表');
    }
  };

  const getCurrentSatelliteData = () => {
    return finalSatellites.length > 0 ? finalSatellites : extractedSatellites;
  };

  const currentSatellites = getCurrentSatelliteData();

  return (
    <div className="mb-6 group" data-message-id={messageId} ref={messageContainerRef}>
      {/* 用户信息和时间戳 */}
      <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium">
            {isUser ? '您' : '智慧虚拟星座助手'}
          </span>

          {isStreaming && !isUser && displayContent && displayContent.length > 0 && (
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce delay-100"></div>
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce delay-200"></div>
              </div>
              <span className="text-blue-600 text-xs font-medium">
                {isPlanContent ? '正在回复中...' : '正在回复中...'}
              </span>
            </div>
          )}

          {!isStreaming && !isUser && displayContent && displayContent.length > 10 && (
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-green-600 text-xs">
                {isPlanContent ? '回复完成' : '回复完成'}
              </span>
              {currentSatellites.length > 0 && (
                <span className="text-blue-600 text-xs ml-2">
                  📊 包含 {currentSatellites.length} 颗卫星数据
                  {chartReady && !showVisualization && ' (图表准备完毕)'}
                </span>
              )}
            </div>
          )}
        </div>
        <span>{formatTime(timestamp)}</span>
      </div>

      {/* 消息气泡 */}
      <div className={`rounded-lg transition-all duration-200 ${
          isUser 
            ? 'bg-gray-100 text-gray-800 border border-gray-200 px-4 py-3' 
            : isPlanContent
              ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 text-gray-800 shadow-sm px-5 py-4'
              : 'bg-white border border-gray-200 text-gray-800 shadow-sm px-4 py-3'
        }`}>

        {/* 方案标题指示器 */}
        {!isUser && isPlanContent && displayContent.length > 50 && (
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-blue-200">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span className="text-sm font-medium text-blue-700">输出结果</span>
            {isStreaming && (
              <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
                实时生成中...
              </span>
            )}

            {/*/!* 图表控制按钮 - 只在消息完成后显示 *!/*/}
            {/*{!isStreaming && currentSatellites.length > 0 && (*/}
            {/*  <button*/}
            {/*    onClick={toggleVisualization}*/}
            {/*    className="ml-auto text-xs bg-blue-500 text-white px-3 py-1 rounded-full hover:bg-blue-600 transition-colors flex items-center gap-1"*/}
            {/*  >*/}
            {/*    <span>📊</span>*/}
            {/*    <span>{showVisualization ? '隐藏' : '显示'}图表</span>*/}
            {/*  </button>*/}
            {/*)}*/}
          </div>
        )}

        <div className="whitespace-pre-wrap break-words">
          {displayContent && displayContent.length > 0 ? (
            <>
              {renderContent(displayContent)}

              {/* 流式输入光标 */}
              {isStreaming && !isUser && displayContent.length > 10 && (
                <span className="inline-block w-2 h-5 bg-blue-400 ml-1 animate-pulse"></span>
              )}
            </>
          ) : (
            isStreaming && !isUser && (
              <div className="flex items-center gap-2 text-gray-500">
                <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                <span className="text-sm">准备回复中...</span>
              </div>
            )
          )}
        </div>

        {/* 消息操作按钮区域 - 在内容之后 */}
        {!isStreaming && displayContent && displayContent.length > 10 && (
          <MessageActions
            message={displayContent}
            messageId={messageId}
            isAssistant={!isUser}
            timestamp={timestamp}
            className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 mt-3"
          />
        )}

        {/* 流式生成统计信息 - 在内容之后 */}
        {isStreaming && !isUser && displayContent && displayContent.length > 20 && (
          <div className="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-200 flex items-center justify-between">
            <span>已生成 {displayContent.length} 字符</span>
            <div className="flex items-center gap-2">
              {isPlanContent && (
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></span>
                  <span>方案内容</span>
                </div>
              )}
              {currentSatellites.length > 0 && (
                <div className="flex items-center gap-1">
                  <span>🛰️</span>
                  <span>{currentSatellites.length} 颗卫星</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 🆕 可视化图表 - 确保在消息气泡外部的下方 */}
      {showVisualization && chartData && !isStreaming && (
        <div className="mt-6 animate-fadeIn">
          <div className="bg-white rounded-lg border shadow-sm p-4">
            <div className="mb-4 flex items-center justify-between">
              <h4 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <span>📊</span>
                <span>数据可视化分析</span>
                <span className="text-sm text-gray-500">
                  ({currentSatellites.length} 颗卫星)
                </span>
              </h4>
              {/*<button*/}
              {/*  onClick={toggleVisualization}*/}
              {/*  className="text-sm text-gray-500 hover:text-gray-700 transition-colors"*/}
              {/*>*/}
              {/*  收起图表 ▲*/}
              {/*</button>*/}
            </div>

            {/* 图表组件 - 传递容器宽度 */}
            <SatelliteCharts
              data={chartData}
              height={400}
              containerWidth={containerWidth}
            />
          </div>
        </div>
      )}

      {/* 🆕 图表提示 - 也在消息气泡外部 */}
      {!showVisualization && !isStreaming && !isUser && currentSatellites.length > 0 && chartReady && (
        <div className="mt-4">
          <div className="flex items-center justify-between bg-blue-50 p-3 rounded-lg animate-fadeIn border-2 border-blue-200">
            <div className="flex items-center gap-2">
              <span className="text-2xl">📊</span>
              <div>
                <div className="text-sm font-medium text-gray-800">
                  检测到 {currentSatellites.length} 颗卫星数据，可生成可视化图表
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  包含卫星能力分析、协同关系图表等
                </div>
              </div>
            </div>
            <button
              onClick={toggleVisualization}
              className="text-sm bg-blue-500 text-white px-4 py-2 rounded-full hover:bg-blue-600 transition-colors animate-pulse font-medium shadow-md"
            >
              📈 显示图表
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// 添加淡入动画样式（如果还没有）
const animationStyles = `
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fadeIn {
  animation: fadeIn 0.3s ease-out;
}
`;

// 如果您的项目中还没有这个样式，可以将其添加到全局CSS文件中
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = animationStyles;
  document.head.appendChild(style);
}

// 辅助函数保持不变...
function getCollaborationType(sat1, sat2) {
  if ((sat1.includes('高分') && sat2.includes('高分')) ||
      (sat1.includes('Sentinel') && sat2.includes('Sentinel'))) {
    return '同系列协同';
  }
  if ((sat1.includes('Landsat') && sat2.includes('Sentinel')) ||
      (sat1.includes('Sentinel') && sat2.includes('Landsat'))) {
    return '经典组合';
  }
  if (sat1.includes('雷达') || sat2.includes('雷达') ||
      sat1.includes('三号') || sat2.includes('三号')) {
    return '雷达协同';
  }
  return '跨系列协同';
}

function generateCapabilities(satelliteName) {
  const baseCapabilities = {
    spatialResolution: 75,
    temporalResolution: 70,
    spectralResolution: 70,
    coverage: 75,
    dataQuality: 80,
    realtime: 65
  };

  if (satelliteName.includes('高分')) {
    baseCapabilities.spatialResolution = 85 + Math.floor(Math.random() * 10);
    baseCapabilities.dataQuality = 85 + Math.floor(Math.random() * 5);
  } else if (satelliteName.includes('WorldView') || satelliteName.includes('Pleiades')) {
    baseCapabilities.spatialResolution = 90 + Math.floor(Math.random() * 8);
    baseCapabilities.dataQuality = 90 + Math.floor(Math.random() * 5);
  } else if (satelliteName.includes('Sentinel') || satelliteName.includes('哨兵')) {
    baseCapabilities.temporalResolution = 85 + Math.floor(Math.random() * 10);
    baseCapabilities.spectralResolution = 85 + Math.floor(Math.random() * 10);
  } else if (satelliteName.includes('Landsat')) {
    baseCapabilities.spectralResolution = 80 + Math.floor(Math.random() * 10);
    baseCapabilities.coverage = 85 + Math.floor(Math.random() * 10);
  }

  return baseCapabilities;
}

function generateRecommendations(satellites, collaborations) {
  const recommendations = [];

  if (satellites.length >= 3) {
    recommendations.push(`🌐 您的方案包含 ${satellites.length} 颗卫星，形成了互补的观测能力`);
  }

  if (collaborations.length > 0) {
    const avgFreq = collaborations.reduce((sum, c) => sum + c.frequency, 0) / collaborations.length;
    recommendations.push(`🤝 卫星间平均协同频率为 ${avgFreq.toFixed(1)} 次/月`);
  }

  if (satellites.some(s => s.includes('高分'))) {
    recommendations.push('🎯 高分系列卫星提供高空间分辨率，适合精细目标识别');
  }

  if (satellites.some(s => s.includes('Sentinel') || s.includes('哨兵'))) {
    recommendations.push('⏱️ 哨兵系列卫星重访周期短，适合高频监测需求');
  }

  return recommendations;
}

// 辅助函数：获取发射日期
function getLaunchDate(satelliteName) {
  const launchDates = {
    "高分一号": "2013-04-26",
    "高分二号": "2014-08-19",
    "高分三号": "2016-08-10",
    "高分六号": "2018-06-02",
    "Sentinel-2": "2015-06-23",
    "哨兵-2号": "2015-06-23",
    "Landsat-8": "2013-02-11",
    "Landsat-9": "2021-09-27",
    "WorldView-3": "2014-08-13",
    "Pleiades": "2011-12-17",
    "PlanetScope": "2016-02-14",
    "珠海一号": "2017-06-15",
    "EOS PM-1(Aqua)": "2002-05-04"
  };
  return launchDates[satelliteName] || "2020-01-01";
}

// 辅助函数：从卫星名称推断国家
function getCountryFromSatelliteName(name) {
  if (name.includes('高分') || name.includes('风云') || name.includes('海洋') || name.includes('资源') || name.includes('环境')) {
    return '中国';
  } else if (name.includes('Sentinel') || name.includes('哨兵')) {
    return '欧洲';
  } else if (name.includes('Landsat') || name.includes('MODIS') || name.includes('WorldView') || name.includes('EOS') || name.includes('Aqua')) {
    return '美国';
  } else if (name.includes('葵花') || name.includes('Himawari')) {
    return '日本';
  }
  return '其他';
}

export default EnhancedStreamingMessage;