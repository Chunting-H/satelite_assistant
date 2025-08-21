// App.jsx - 修复WebSocket和可视化数据传递问题，集成卫星管理功能
import { useState, useEffect, useRef, useCallback } from 'react';
import { uploadFile, listConversations, deleteConversation, getConversation, createConversation } from './services/api';
import { extractLocation } from './services/location';
import { extractSatelliteNames, extractSatelliteNamesFromMessages, normalizeSatelliteName } from './services/satelliteExtractor';
import { ConversationProvider } from './contexts/ConversationContext';
import Header from './components/UI/Header';
import Sidebar from './components/UI/Sidebar';
import ChatInput from './components/Chat/ChatInput';
import RealTimeStreamingMessage from './components/Chat/RealTimeStreamingMessage';
import FixedThinkingProcess from './components/Chat/FixedThinkingProcess';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import EnhancedCesiumMap from './components/Map/EnhancedCesiumMap';
import ClarificationDialog from './components/Chat/ClarificationDialog';
import EnhancedStreamingMessage from './components/Chat/EnhancedStreamingMessage';
import { renameConversation } from './services/api';
// 🆕 新增：导入卫星管理组件
import SatelliteManagement from './components/Satellite/SatelliteManagement';
// 🆕 新增：导入数据处理组件
import DataProcessingDialog from './components/Chat/DataProcessingDialog';
import ProcessingProgressBar from './components/UI/ProcessingProgressBar';
import ProcessingResultViewer from './components/Chat/ProcessingResultViewer';

// 🆕 新增：可拖拽分隔条组件
const ResizableHandle = ({ onDrag, isVisible }) => {
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);

    const handleMouseMove = (e) => {
      onDrag(e.clientX);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [onDrag]);

  if (!isVisible) return null;

  return (
    <div
      className={`
        absolute top-0 bottom-0 w-1 bg-gray-300 hover:bg-blue-400 cursor-col-resize 
        transition-colors duration-200 z-10 right-0
        ${isDragging ? 'bg-blue-500' : ''}
      `}
      onMouseDown={handleMouseDown}
      style={{
        right: '-2px',
        width: '4px'
      }}
    >
      {/* 拖拽提示 */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
        <div className="w-1 h-8 bg-white opacity-70 rounded-full"></div>
      </div>
    </div>
  );
};

function App() {
  // ... 所有原有状态定义保持不变 ...
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentThinkingSteps, setCurrentThinkingSteps] = useState([]);
  const [currentThinkingId, setCurrentThinkingId] = useState(null);
  const streamingContentRef = useRef('');
  const streamingMessageIdRef = useRef(null);
  const lastUpdateTimeRef = useRef(0);
  const updateTimeoutRef = useRef(null);
  const wsRef = useRef(null);
  const [wsConnected, setWsConnected] = useState(false);
  const reconnectTimeoutRef = useRef(null);
  const isInitializedRef = useRef(false);
  const isConnectingRef = useRef(false);
  const lastConversationIdRef = useRef(null);
  const isDesktop = useRef(window.innerWidth >= 768);
  const [sidebarOpen, setSidebarOpen] = useState(isDesktop.current);
  const [location, setLocation] = useState(null);
  const [mapVisible, setMapVisible] = useState(false);
  const [fullscreenMap, setFullscreenMap] = useState(false);
  const messagesEndRef = useRef(null);
  const [extractedSatellites, setExtractedSatellites] = useState([]);
  const [isExtractingSatellites, setIsExtractingSatellites] = useState(false);
  const extractionTimeoutRef = useRef(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deletingConversationId, setDeletingConversationId] = useState(null);
  const [clarificationQuestions, setClarificationQuestions] = useState([]);
  const [showClarificationDialog, setShowClarificationDialog] = useState(false);
  const [isAwaitingClarification, setIsAwaitingClarification] = useState(false);
  const [parametersUncertainty, setParametersUncertainty] = useState({});
  // 🔧 新增：后端连接状态检查
  const [backendReady, setBackendReady] = useState(false);
  const backendCheckRef = useRef(null);
  const [existingParams, setExistingParams] = useState({});
  // 🔧 新增：可视化数据缓存
  const [currentVisualizationData, setCurrentVisualizationData] = useState(null);
  const [currentClarificationStage, setCurrentClarificationStage] = useState(null);
  const [stageName, setStageName] = useState('');
  const [stageRetryCount, setStageRetryCount] = useState(0);

  // 🆕 新增：对话区域宽度控制状态
  const [chatAreaWidth, setChatAreaWidth] = useState(50); // 百分比，默认50%
  const [isResizing, setIsResizing] = useState(false);
  const chatContainerRef = useRef(null);

  // 🆕 智能滚动状态管理
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const lastScrollTopRef = useRef(0);
  const isUserScrollingRef = useRef(false);
  const messagesContainerRef = useRef(null);

  // 🆕 新增：卫星管理页面状态
  const [showSatelliteManagement, setShowSatelliteManagement] = useState(false);

  // 🆕 新增：数据处理相关状态
  const [showDataProcessingDialog, setShowDataProcessingDialog] = useState(false);
  const [currentSatellites, setCurrentSatellites] = useState([]);
  const [processingId, setProcessingId] = useState(null);
  const [showProgressBar, setShowProgressBar] = useState(false);
  const [hasShownDataProcessingDialog, setHasShownDataProcessingDialog] = useState(false);
  const [preferPlanCallback, setPreferPlanCallback] = useState(true); // 优先由子组件回调触发
  // 🆕 结果对比视图状态
  const [showResultViewer, setShowResultViewer] = useState(false);
  const [resultOriginalUrl, setResultOriginalUrl] = useState(null);
  const [resultProcessedUrl, setResultProcessedUrl] = useState(null);

  // 🆕 新增：处理拖拽调整宽度
  const handleResize = useCallback((clientX) => {
    if (!chatContainerRef.current || !mapVisible) return;

    const containerRect = chatContainerRef.current.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const newWidthPercentage = ((clientX - containerRect.left) / containerWidth) * 100;

    // 限制宽度在20%到80%之间
    const clampedWidth = Math.max(20, Math.min(80, newWidthPercentage));
    setChatAreaWidth(clampedWidth);
  }, [mapVisible]);

  // 🆕 新增：响应式处理
  useEffect(() => {
    const handleResize = () => {
      // 在移动端时，重置为默认宽度
      if (window.innerWidth < 768) {
        setChatAreaWidth(50);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 🆕 新增：卫星管理页面处理函数
  const handleSatelliteManagement = () => {
    setShowSatelliteManagement(true);
  };

  const handleBackFromSatelliteManagement = () => {
    setShowSatelliteManagement(false);
  };

  // 🆕 智能滚动到底部
  const scrollToBottom = (force = false) => {
    if (!messagesContainerRef.current) return;
    // 如果用户主动向上滚动且不是强制滚动，则不自动滚动
    if (userScrolledUp && !force) {
      setShowScrollToBottom(true);
      return;
    }
    const container = messagesContainerRef.current;
    container.scrollTop = container.scrollHeight;
    setUserScrolledUp(false);
    setShowScrollToBottom(false);
  };

  // 🆕 处理滚动事件
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    const container = messagesContainerRef.current;
    const { scrollTop, scrollHeight, clientHeight } = container;
    // 只要不在底部就 userScrolledUp=true，误差提高到100避免误判
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
    setUserScrolledUp(!isAtBottom);
    setShowScrollToBottom(!isAtBottom);
    lastScrollTopRef.current = scrollTop;
  }, []);

  // 🆕 监听滚动事件
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll, { passive: true });
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  // ... 保持所有原有的函数和useEffect钩子不变 ...

  // 🔧 修复：检查后端服务状态
  const checkBackendStatus = async () => {
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:2025';
      const response = await fetch(`${apiBaseUrl}/api/health`, {
        method: 'GET',
        timeout: 3000
      });

      if (response.ok) {
        setBackendReady(true);
        console.log('✅ 后端服务已就绪');
        return true;
      }
    } catch (error) {
      console.log('⏳ 后端服务尚未就绪，等待中...');
      setBackendReady(false);
      return false;
    }
    return false;
  };

  // 启动后端状态检查
  useEffect(() => {
    const startBackendCheck = async () => {
      const isReady = await checkBackendStatus();

      if (!isReady) {
        backendCheckRef.current = setInterval(async () => {
          const ready = await checkBackendStatus();
          if (ready && backendCheckRef.current) {
            clearInterval(backendCheckRef.current);
            backendCheckRef.current = null;
          }
        }, 2000);
      }
    };

    startBackendCheck();

    return () => {
      if (backendCheckRef.current) {
        clearInterval(backendCheckRef.current);
        backendCheckRef.current = null;
      }
    };
  }, []);

  const handleRenameConversation = async (conversationId, newTitle) => {
    try {
      await renameConversation(conversationId, newTitle);
      setConversations(prev => prev.map(conv =>
        conv.conversation_id === conversationId
          ? { ...conv, title: newTitle }
          : conv
      ));
      console.log('对话重命名成功');
    } catch (error) {
      console.error('重命名对话失败:', error);
      throw error;
    }
  };

  // 🆕 防抖更新流式消息 - 优化滚动行为
  const updateStreamingMessage = useCallback((content) => {
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }

    updateTimeoutRef.current = setTimeout(() => {
      if (streamingMessageIdRef.current) {
        setMessages(prev => prev.map(msg => {
          if (msg.id === streamingMessageIdRef.current) {
            return {
              ...msg,
              content,
              accumulatedContent: content,
              timestamp: Date.now()
            };
          }
          return msg;
        }));

        // 智能滚动逻辑保持不变
        if (!userScrolledUp && messagesContainerRef.current) {
          const container = messagesContainerRef.current;
          const { scrollTop, scrollHeight, clientHeight } = container;
          const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
          if (isAtBottom) {
            setTimeout(() => scrollToBottom(), 50);
          }
        }
      }
    }, 50);
  }, [userScrolledUp]);

  // WebSocket连接管理
  const connectWebSocket = useCallback((convId) => {
    if (!convId || !backendReady) {
      console.log('🚫 无法连接：缺少会话ID或后端未就绪');
      return;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && wsRef.current.conversationId === convId) {
      console.log('🔌 已连接到会话:', convId);
      return;
    }

    if (wsRef.current) {
      console.log('🔌 关闭现有连接');
      wsRef.current.close(1000, 'Switching conversations');
      wsRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:2025';
    const wsBaseUrl = apiBaseUrl.replace('https://', 'wss://').replace('http://', 'ws://');
    const wsUrl = `${wsBaseUrl}/api/ws/${convId}`;
    console.log('🔌 建立新连接:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      ws.conversationId = convId;
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket连接成功');
        setWsConnected(true);
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 收到消息:', data.type);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('❌ 解析消息出错:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('🔌 连接关闭:', event.code, event.reason);
        setWsConnected(false);
        wsRef.current = null;

        if (event.code !== 1000 && event.code !== 1001 && convId === conversationId && backendReady) {
          console.log('🔄 将在2秒后重连...');
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket(convId);
          }, 2000);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket错误:', error);
        setWsConnected(false);
      };
    } catch (error) {
      console.error('❌ 创建WebSocket失败:', error);
      setWsConnected(false);
    }
  }, [backendReady, conversationId]);

  useEffect(() => {
    if (!backendReady || !conversationId) {
      return;
    }

    if (wsRef.current?.conversationId !== conversationId) {
      console.log('🔄 会话ID变化，重新连接:', conversationId);
      connectWebSocket(conversationId);
    }

    return () => {
      // 组件卸载时不关闭连接，除非整个应用关闭
    };
  }, [backendReady, conversationId, connectWebSocket]);

  useEffect(() => {
    return () => {
      console.log('🧹 应用关闭，清理WebSocket连接');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'App unmounting');
      }
    };
  }, []);

  // 重置流式状态
  const resetStreamingState = () => {
    console.log('🔄 重置流式状态');
    streamingContentRef.current = '';
    streamingMessageIdRef.current = null;
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
      updateTimeoutRef.current = null;
    }
  };

  // 🔧 重点修复：处理WebSocket消息
  const handleWebSocketMessage = (data) => {
    const { type } = data;

    switch (type) {
      case 'connected':
        console.log('✅ 连接确认');
        break;

      case 'processing_start':
        console.log('🚀 开始处理');
        setIsProcessing(true);
        setCurrentThinkingSteps([]);
        setCurrentThinkingId(`thinking_${Date.now()}`);
        resetStreamingState();
        setCurrentVisualizationData(null);
        setMessages(prev => prev.map(msg =>
          msg.isStreaming ? { ...msg, isStreaming: false } : msg
        ));
        break;

      case 'clarification_start':
        console.log('🎯 开始参数澄清');
        break;

      case 'clarification_questions':
        console.log('❓ 收到澄清问题:', data.questions);
        setClarificationQuestions(data.questions || []);
        setIsAwaitingClarification(true);

        if (data.stage) {
          setCurrentClarificationStage(data.stage);
          setStageName(data.stage_name);
          setStageRetryCount(data.retry_count || 0);
        }

        if (data.existing_params) {
          setExistingParams(data.existing_params);
        }
        if (data.uncertainty_results) {
          setParametersUncertainty(data.uncertainty_results);
        }

        if (data.questions && data.questions.length > 0) {
          setShowClarificationDialog(true);
        }
        break;

      case 'clarification_complete':
        console.log('✅ 参数澄清完成');
        setIsAwaitingClarification(false);
        setShowClarificationDialog(false);
        setClarificationQuestions([]);

        setCurrentClarificationStage(null);
        setStageName('');
        setStageRetryCount(0);

        if (data.message) {
          const confirmMessageId = Date.now() + Math.random();
          setMessages(prev => [...prev, {
            id: confirmMessageId,
            role: 'assistant',
            content: data.message,
            timestamp: Date.now(),
            isStreaming: false
          }]);
        }
        break;

      case 'stage_complete':
        console.log('✅ 阶段完成:', data.stage_name);
        break;

      case 'thinking_step':
        console.log('🧠 思考:', data.step);
        setCurrentThinkingSteps(prev => {
          const exists = prev.some(s => s.step === data.step && s.message === data.message);
          if (exists) return prev;

          return [...prev, {
            step: data.step,
            message: data.message,
            timestamp: Date.now(),
            id: `${data.step}_${Date.now()}`
          }];
        });
        break;

      case 'data_processing_ready':
        console.log('🛰️ 数据处理准备就绪:', data.message);
        // 显示数据处理对话框
        if (data.satellites && data.satellites.length > 0) {
          // 确保卫星数据格式正确
          const formattedSatellites = data.satellites.map(sat => 
            typeof sat === 'string' ? { name: sat, type: 'optical' } : sat
          );
          setCurrentSatellites(formattedSatellites);
          setShowDataProcessingDialog(true);
        }
        break;

      case 'response_chunk':
      case 'plan_content_chunk':
        const newContent = data.accumulated_content || data.content || '';
        if (!newContent) return;

        console.log('📦 内容块:', newContent.length, '字符');
        streamingContentRef.current = newContent;

        if (!streamingMessageIdRef.current) {
          const newMessageId = Date.now() + Math.random();
          streamingMessageIdRef.current = newMessageId;

          console.log('🆕 创建新流式消息');
          setMessages(prev => [...prev, {
            id: newMessageId,
            role: 'assistant',
            content: newContent,
            timestamp: Date.now(),
            isStreaming: true,
            accumulatedContent: newContent,
          }]);

          if (!userScrolledUp && messagesContainerRef.current) {
            const container = messagesContainerRef.current;
            const { scrollTop, scrollHeight, clientHeight } = container;
            const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
            if (isAtBottom) {
              setTimeout(() => scrollToBottom(), 100);
            }
          }
        } else {
          updateStreamingMessage(newContent);
        }
        break;

      case 'processing_complete':
        console.log('🏁 处理完成');
        setIsProcessing(false);

        if (data.awaiting_confirmation) {
          console.log('⏳ 等待用户确认意图');
          return;
        }

        if (data.clarification_pending) {
          console.log('⏳ 等待参数澄清回复');
          return;
        }

        const currentIntent = data.intent || 'unknown';
        const shouldShowMap = data.show_map === true;

        console.log('🎯 当前意图:', currentIntent, '是否显示地图:', shouldShowMap);

        const handleSatelliteExtraction = async (responseContent) => {
          if (!responseContent || !shouldShowMap) {
            console.log('🚫 不显示地图，跳过卫星提取');
            return;
          }

          console.log('🛰️ 开始提取卫星信息...');

          const isNewPlan = responseContent.includes('卫星组成') ||
                           responseContent.includes('虚拟星座方案') ||
                           responseContent.includes('## 2.') ||
                           responseContent.includes('| 卫星名称 |');

          if (isNewPlan) {
            console.log('🆕 检测到新方案，先清空旧卫星');
            setExtractedSatellites([]);

            setTimeout(async () => {
              try {
                console.log('🔍 从新方案内容提取卫星...');
                const newSatellites = await extractSatelliteNames(responseContent);
                if (newSatellites && newSatellites.length > 0) {
                  console.log('✅ 提取到新卫星:', newSatellites);
                  setExtractedSatellites(newSatellites);

                  if (shouldShowMap && !mapVisible) {
                    setMapVisible(true);
                    console.log('🗺️ 显示地图（意图允许）');
                  }
                } else {
                  console.log('❌ 未从方案内容中提取到卫星');
                }
              } catch (error) {
                console.error('❌ 提取卫星时出错:', error);
              }
            }, 200);
          }
        };

        if (streamingMessageIdRef.current && streamingContentRef.current) {
          if (updateTimeoutRef.current) {
            clearTimeout(updateTimeoutRef.current);
            updateTimeoutRef.current = null;
          }

          setMessages(prev => {
            const newMessages = prev.map(msg => {
              if (msg.id === streamingMessageIdRef.current) {
                console.log('✅ 最终更新流式消息');

                const isPlanMessage = streamingContentRef.current.includes('卫星组成') ||
                       streamingContentRef.current.includes('虚拟星座方案') ||
                       streamingContentRef.current.includes('## 2.') ||
                       streamingContentRef.current.includes('| 卫星名称 |');
                
                const updatedMessage = {
                  ...msg,
                  isStreaming: false,
                  content: streamingContentRef.current,
                  accumulatedContent: streamingContentRef.current,
                  thinkingSteps: [...currentThinkingSteps],
                  thinkingId: currentThinkingId,
                  satellites: isPlanMessage ? extractedSatellites : undefined,
                  showVisualization: isPlanMessage
                };

                // 🆕 新增：检查是否包含虚拟星座方案
                checkForConstellationPlan(updatedMessage);

                return updatedMessage;
              }
              return msg;
            });

            handleSatelliteExtraction(streamingContentRef.current);
            return newMessages;
          });

        } else if (data.response) {
          console.log('📝 添加非流式响应:', data.response.slice(0, 50));
          const newMessageId = Date.now() + Math.random();

          setMessages(prev => [...prev, {
            id: newMessageId,
            role: 'assistant',
            content: data.response,
            timestamp: Date.now(),
            isStreaming: false,
            thinkingSteps: [...currentThinkingSteps],
            thinkingId: currentThinkingId,
            satellites: extractedSatellites
          }]);

          handleSatelliteExtraction(data.response);

          // 🆕 新增：检查是否包含虚拟星座方案
          const newMessage = {
            id: newMessageId,
            role: 'assistant',
            content: data.response,
            timestamp: Date.now(),
            isStreaming: false,
            thinkingSteps: [...currentThinkingSteps],
            thinkingId: currentThinkingId,
            satellites: extractedSatellites
          };
          checkForConstellationPlan(newMessage);

          if (!userScrolledUp && messagesContainerRef.current) {
            const container = messagesContainerRef.current;
            const { scrollTop, scrollHeight, clientHeight } = container;
            const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
            if (isAtBottom) {
              setTimeout(() => scrollToBottom(), 100);
            }
          }
        }

        setTimeout(() => {
          setCurrentThinkingSteps([]);
          setCurrentThinkingId(null);
          resetStreamingState();

          if (!userScrolledUp) {
            setShowScrollToBottom(false);
          }
        }, 100);

        setTimeout(() => {
          fetchConversations();
        }, 500);
        break;

      case 'error':
        console.error('❌ 错误:', data.message);
        setIsProcessing(false);
        resetStreamingState();
        setCurrentThinkingSteps([]);
        setCurrentThinkingId(null);

        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'assistant',
          content: `处理出错: ${data.message}`,
          timestamp: Date.now(),
          isError: true
        }]);
        break;
    }
  };

  // 其余函数保持不变...
  const fetchConversations = async () => {
    try {
      setLoading(true);
      const data = await listConversations();
      if (data && Array.isArray(data.conversations)) {
        setConversations(data.conversations);
      }
    } catch (error) {
      console.error('获取对话列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (backendReady) {
      fetchConversations();
    }
  }, [backendReady]);

  const handleNewConversation = () => {
    console.log('🆕 重置为新建对话状态');

    setConversationId(null);
    setParametersUncertainty({});
    setExistingParams({});
    setMessages([]);
    setCurrentThinkingSteps([]);
    setCurrentThinkingId(null);
    setIsProcessing(false);
    resetStreamingState();
    setExtractedSatellites([]);
    setLocation(null);
    setCurrentVisualizationData(null);
    setShowClarificationDialog(false);
    setClarificationQuestions([]);
    setIsAwaitingClarification(false);
    setCurrentClarificationStage(null);
    setStageName('');
    setStageRetryCount(0);
    setChatAreaWidth(50);
    resetDataProcessingState(); // 重置数据处理对话框状态

    if (wsRef.current) {
      wsRef.current.close();
      setWsConnected(false);
    }

    console.log('✅ 已重置为新建对话状态');
  };

  const handleSelectConversation = async (convId) => {
    if (convId === conversationId) return;

    console.log('🔄 切换对话:', convId);
    setLoadingConversation(true);
    setParametersUncertainty({});
    setExistingParams({});
    setConversationId(convId);
    setMessages([]);
    setCurrentThinkingSteps([]);
    setCurrentThinkingId(null);
    setIsProcessing(false);
    resetStreamingState();
    setExtractedSatellites([]);
    setLocation(null);
    setCurrentVisualizationData(null);
    setShowClarificationDialog(false);
    setClarificationQuestions([]);
    setIsAwaitingClarification(false);
    setCurrentClarificationStage(null);
    setStageName('');
    setStageRetryCount(0);
    setChatAreaWidth(50);
    resetDataProcessingState(); // 重置数据处理对话框状态

    try {
      const conversationData = await getConversation(convId);

      if (conversationData && conversationData.metadata && conversationData.metadata.messages) {
        console.log(`📥 加载对话历史: ${conversationData.metadata.messages.length} 条消息`);

        const loadedMessages = conversationData.metadata.messages.map((msg, index) => ({
          id: `loaded_${index}_${Date.now()}`,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp * 1000,
          isStreaming: false,
          visualizationData: null
        }));

        setMessages(loadedMessages);

        if (conversationData.location) {
          console.log('📍 使用保存的位置信息:', conversationData.location);
          setLocation(conversationData.location);
          setMapVisible(true);
        } else {
          let extractedLocation = null;
          for (const msg of loadedMessages) {
            if (msg.role === 'user' && msg.content) {
              try {
                const location = await extractLocation(msg.content);
                if (location && location.length > 1) {
                  extractedLocation = location;
                  console.log('📍 从历史消息中提取到位置:', location);
                  break;
                }
              } catch (error) {
                console.error('提取位置失败:', error);
              }
            }
          }

          if (extractedLocation) {
            setLocation(extractedLocation);
            setMapVisible(true);
          }
        }

        const loadSatellites = async () => {
          let satellitesToDisplay = [];

          if (conversationData.extracted_satellites && conversationData.extracted_satellites.length > 0) {
            console.log('🛰️ 使用保存的卫星信息:', conversationData.extracted_satellites);
            satellitesToDisplay = conversationData.extracted_satellites;
          } else {
            console.log('🛰️ 从消息中提取卫星信息...');
            satellitesToDisplay = await extractSatelliteNamesFromMessages(loadedMessages);
          }

          const uniqueSatellites = Array.from(new Set(satellitesToDisplay));

          if (uniqueSatellites.length > 0) {
            console.log('🛰️ 设置卫星显示:', uniqueSatellites);

            if (!mapVisible) {
              setMapVisible(true);
            }

            const setSatellitesWithRetry = (satellites, retryCount = 0) => {
              setExtractedSatellites(satellites);

              if (retryCount < 3) {
                setTimeout(() => {
                  console.log(`🔁 第 ${retryCount + 2} 次设置卫星数据`);
                  setExtractedSatellites(prevSatellites => {
                    if (prevSatellites.length === 0 && satellites.length > 0) {
                      return satellites;
                    }
                    return prevSatellites;
                  });
                }, 500 * (retryCount + 1));
              }
            };

            setSatellitesWithRetry(uniqueSatellites);
          }
        };

        await loadSatellites();

      } else {
        console.log('📭 对话历史为空');
      }
    } catch (error) {
      console.error('加载对话历史失败:', error);
      setMessages([{
        id: Date.now(),
        role: 'assistant',
        content: '加载对话历史失败，请重试',
        timestamp: Date.now(),
        isError: true
      }]);
    } finally {
      setLoadingConversation(false);
    }

    setTimeout(() => {
      if (backendReady) {
        connectWebSocket(convId);
      }
    }, 300);
  };

  // 其余函数保持不变...
  const handleSendMessage = async (text) => {
    console.log('📤 发送消息:', text.slice(0, 50));

    const isNewPlanRequest = text.includes('监测') || text.includes('方案') ||
                            text.includes('规划') || text.includes('设计') ||
                            text.includes('观测') || text.includes('卫星');

    const hasExistingPlan = messages.some(msg =>
        msg.role === 'assistant' &&
        (msg.content.includes('虚拟星座方案') || msg.content.includes('卫星组成'))
    );

    const messageData = {
        message: text,
        extracted_satellites: extractedSatellites,
        location: location
    };

    if (isNewPlanRequest && hasExistingPlan) {
        console.log('🔄 检测到新方案请求，将重置参数澄清流程');
        messageData.reset_clarification = true;
    }

    const isLocationChangeRequest = text.includes('改成') || text.includes('换成') ||
                                   text.includes('改为') || text.includes('变成') ||
                                   text.includes('如果') || text.includes('换到') ||
                                   text.includes('改到') || text.includes('移到') ||
                                   /地点.*?改|地点.*?换|地点.*?变|位置.*?改|位置.*?换|位置.*?变/.test(text);

    const isEconomicOptimization = text.includes('经济') || text.includes('便宜') ||
                                  text.includes('成本') || text.includes('省钱') ||
                                  text.includes('低成本') || text.includes('更便宜');

    const isOptimizationRequest = text.includes('优化') || text.includes('改进') ||
                                 text.includes('调整') || text.includes('修改') ||
                                 text.includes('提升') || text.includes('改善') ||
                                 isEconomicOptimization || isLocationChangeRequest;

    if (isNewPlanRequest || isOptimizationRequest) {
      console.log('🧹 检测到新方案请求或优化请求，准备清除现有数据');

      setExtractedSatellites([]);

      if (isLocationChangeRequest) {
        console.log('🌍 检测到地点变更请求，清空位置信息');
        setLocation(null);
      }

      setCurrentVisualizationData(null);
      setChatAreaWidth(50);
      resetDataProcessingState(); // 重置数据处理对话框状态
    }

    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }

    if (!conversationId) {
      const newConvId = `conv_${Date.now()}`;
      setConversationId(newConvId);

      const waitForConnection = async (convId, maxRetries = 10) => {
        let retries = 0;

        if (backendReady) {
          connectWebSocket(convId);
        }

        while (retries < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, 200));

          if (wsRef.current &&
              wsRef.current.readyState === WebSocket.OPEN &&
              wsRef.current.conversationId === convId) {
            console.log('✅ WebSocket已连接，可以发送消息');
            return true;
          }

          retries++;
          console.log(`⏳ 等待WebSocket连接... (${retries}/${maxRetries})`);
        }

        console.error('❌ WebSocket连接超时');
        return false;
      };

      const newConversation = {
        conversation_id: newConvId,
        title: text.slice(0, 50) + (text.length > 50 ? '...' : ''),
        created_at: Date.now() / 1000,
        updated_at: Date.now() / 1000,
        message_count: 1
      };

      setConversations(prev => [newConversation, ...prev]);

      const connected = await waitForConnection(newConvId);
      if (connected) {
        sendMessageViaWebSocket(text);
      } else {
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'assistant',
          content: '连接失败，请刷新页面重试',
          timestamp: Date.now(),
          isError: true
        }]);
        return;
      }
    } else {
      sendMessageViaWebSocket(text);

      if (messages.length === 0) {
        setConversations(prev => prev.map(conv => {
          if (conv.conversation_id === conversationId) {
            return {
              ...conv,
              title: text.slice(0, 50) + (text.length > 50 ? '...' : ''),
              updated_at: Date.now() / 1000,
              message_count: conv.message_count + 1
            };
          }
          return conv;
        }));
      }
    }

    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: Date.now()
    }]);

    setUserScrolledUp(false);
    setShowScrollToBottom(false);
    setTimeout(() => scrollToBottom(), 100);

    try {
      const extractedLocation = await extractLocation(text);
      if (extractedLocation && extractedLocation.length > 1) {
        console.log('📍 提取到新地点:', extractedLocation);
        setLocation(extractedLocation);
        setMapVisible(true);
      }
    } catch (error) {
      console.error("地点提取失败:", error);
    }
  };

  const sendMessageViaWebSocket = (text) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket未连接');

      if (conversationId && backendReady) {
        connectWebSocket(conversationId);

        setTimeout(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            const messageData = {
              message: text,
              extracted_satellites: extractedSatellites,
              location: location
            };
            wsRef.current.send(JSON.stringify(messageData));
            console.log('📤 消息已发送（重试）');
          } else {
            setMessages(prev => [...prev, {
              id: Date.now(),
              role: 'assistant',
              content: '连接失败，请刷新页面重试',
              timestamp: Date.now(),
              isError: true
            }]);
          }
        }, 1000);
      }
      return;
    }

    const messageData = {
      message: text,
      extracted_satellites: extractedSatellites,
      location: location
    };
    wsRef.current.send(JSON.stringify(messageData));
    console.log('📤 消息已发送');
  };

  // 其余函数保持不变...
  const handleFileUpload = async (file) => {
    try {
      const response = await uploadFile(file, conversationId);
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: `文件上传成功: ${file.name}\n\n您可以继续提问，我将结合这个文件回答您的问题。`,
        timestamp: Date.now()
      }]);
    } catch (error) {
      console.error('文件上传失败:', error);
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: `文件上传失败: ${error.message}`,
        timestamp: Date.now(),
        isError: true
      }]);
    }
  };

  const handleDeleteConversation = (id) => {
    setDeletingConversationId(id);
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = async () => {
    try {
      if (!deletingConversationId) return;
      setLoading(true);
      await deleteConversation(deletingConversationId);

      if (deletingConversationId === conversationId) {
        setConversationId(null);
        setMessages([]);
        setCurrentThinkingSteps([]);
        setCurrentThinkingId(null);
        setIsProcessing(false);
        resetStreamingState();
        setExtractedSatellites([]);
        setCurrentVisualizationData(null);
        setChatAreaWidth(50);
        resetDataProcessingState(); // 重置数据处理对话框状态

        if (wsRef.current) {
          wsRef.current.close();
        }
      }

      await fetchConversations();
      setDeleteConfirmOpen(false);
      setDeletingConversationId(null);
    } catch (error) {
      console.error('删除对话失败:', error);
      alert('删除对话失败: ' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const cancelDelete = () => {
    setDeleteConfirmOpen(false);
    setDeletingConversationId(null);
  };

  const handleExampleClick = (question) => {
    handleSendMessage(question);
  };

  const handleSatelliteClick = (satelliteName) => {
    console.log('🛰️ 点击卫星:', satelliteName);
  };

  const formatClarificationResponse = (answers) => {
    const formattedAnswers = {};

    Object.entries(answers).forEach(([key, value]) => {
      const question = clarificationQuestions.find(q => q.parameter_key === key);
      if (question && question.options) {
        const isCustom = !question.options.some(opt =>
          (opt.value || opt) === value
        );

        if (isCustom) {
          formattedAnswers[key] = value.trim();
        } else {
          formattedAnswers[key] = value;
        }
      } else {
        formattedAnswers[key] = value.trim();
      }
    });

    return formattedAnswers;
  };

  const handleClarificationSubmit = (answerText) => {
    console.log('📝 提交澄清答案:', answerText);

    const clarificationMessage = {
      id: Date.now(),
      role: 'user',
      content: answerText,
      timestamp: Date.now(),
      isClarificationResponse: true
    };

    setMessages(prev => [...prev, clarificationMessage]);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const messageData = {
        message: answerText,
        extracted_satellites: extractedSatellites,
        location: location,
        isClarificationResponse: true
      };
      wsRef.current.send(JSON.stringify(messageData));
      console.log('📤 澄清回复已发送');
    }

    setShowClarificationDialog(false);
    setIsAwaitingClarification(false);
  };

  const handleClarificationSkip = () => {
    console.log('⏭️ 跳过参数澄清');

    const skipMessage = "直接生成方案";

    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      content: skipMessage,
      timestamp: Date.now()
    }]);

    sendMessageViaWebSocket(skipMessage);

    setShowClarificationDialog(false);
    setIsAwaitingClarification(false);
  };

  // 🆕 新增：数据处理相关处理函数
  const handleDataProcessingConfirm = async (data) => {
    try {
      console.log('🚀 启动数据处理(回调数据):', data);
      // 立即显示全局进度条，提升响应感
      setShowProgressBar(true);
      setShowDataProcessingDialog(false);

      // 请求后端启动任务
      const response = await fetch('/api/process-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          selected_satellites: data.selectedSatellites,
          processing_options: data.processingOptions
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setProcessingId(result.processing_id);
        console.log('✅ 数据处理任务已启动:', result.processing_id);
      } else {
        throw new Error('启动数据处理失败');
      }
    } catch (error) {
      console.error('❌ 启动数据处理失败:', error);
      alert('启动数据处理失败: ' + error.message);
      setShowProgressBar(false);
    }
  };

  const handleDataProcessingCancel = () => {
    setShowDataProcessingDialog(false);
  };

  const handleDataProcessingComplete = (data) => {
    console.log('✅ 数据处理完成:', data);
    setShowProgressBar(false);
    
    // 显示成功提示
    const successMessage = {
      id: Date.now() + Math.random(),
      role: 'assistant',
      content: `🎉 数据处理完成！\n\n相关数据已处理并准备就绪。\n\n已为您下载：\n• 原始数据文件\n• 处理后的结果图像\n\n处理步骤：${data.processing_steps?.join('、') || '匀光匀色、辐射校正'}`,
      timestamp: Date.now(),
      isStreaming: false
    };
    
    setMessages(prev => [...prev, successMessage]);

    // 🆕 构建对比显示所需的 URL（若浏览器强制下载，可后续改为 fetch blob 再 createObjectURL）
    if (data && data.download_urls) {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:2025';
      // 使用预览模式，后端将图像转换为PNG返回，确保<img>可显示
      const originalHref = data.download_urls.original ? `${API_BASE}${data.download_urls.original}?preview=true` : null;
      const processedHref = data.download_urls.processed ? `${API_BASE}${data.download_urls.processed}?preview=true` : null;
      setResultOriginalUrl(originalHref);
      setResultProcessedUrl(processedHref);
      setShowResultViewer(true);
    }
    
    // 更新工作流状态
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'data_processing_complete',
        conversation_id: conversationId,
        processing_id: processingId,
        results: data
      }));
    }
  };

  const handleDataProcessingError = (error) => {
    console.error('❌ 数据处理失败:', error);
    setShowProgressBar(false);
    alert('数据处理失败: ' + error.message);
  };

  // 🆕 由消息组件回调触发：输出结果完成
  const handlePlanOutputComplete = useCallback(({ messageId, content }) => {
    if (isAwaitingClarification || showClarificationDialog) return;
    if (hasShownDataProcessingDialog) return;

    console.log('🛰️ 子组件回调：输出结果完成，准备显示数据处理对话框', messageId);
    setTimeout(() => {
      setCurrentSatellites(Array.isArray(extractedSatellites) ? extractedSatellites : []);
      setShowDataProcessingDialog(true);
      setHasShownDataProcessingDialog(true);
    }, 300);
  }, [isAwaitingClarification, showClarificationDialog, hasShownDataProcessingDialog, extractedSatellites]);

  // 🆕 新增：检查消息中是否包含星座方案，如果是则显示数据处理对话框
  const checkForConstellationPlan = (message) => {
    // 未完成澄清阶段时不触发
    if (isAwaitingClarification || showClarificationDialog) return;

    // 如果优先由回调触发，则这里不再主动弹出，避免重复/过早
    if (preferPlanCallback) return;

    // 仅在助手的最终方案消息触发（更严格条件）
    const isConstellationPlan = message.showVisualization === true || (
      (message.content.includes('虚拟星座方案') ||
       message.content.includes('卫星组成') ||
       message.content.includes('## 2.') ||
       message.content.includes('| 卫星名称 |'))
    );

    if (isConstellationPlan && message.role === 'assistant' && !hasShownDataProcessingDialog) {
      console.log('🛰️ 检测到虚拟星座方案（澄清完成），准备显示数据处理对话框');

      // 延迟显示对话框，让用户先看到方案内容
      setTimeout(() => {
        setCurrentSatellites(Array.isArray(extractedSatellites) ? extractedSatellites : []);
        setShowDataProcessingDialog(true);
        setHasShownDataProcessingDialog(true);
      }, 1200); // 1.2秒后显示
    }
  };

  // 🆕 新增：重置数据处理对话框状态（当开始新对话时）
  const resetDataProcessingState = () => {
    setShowDataProcessingDialog(false);
    setHasShownDataProcessingDialog(false);
    setShowProgressBar(false);
    setProcessingId(null);
  };

  // 🆕 新增：监听消息变化，检查是否包含星座方案
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage && lastMessage.role === 'assistant' && !lastMessage.isError) {
        checkForConstellationPlan(lastMessage);
      }
    }
  }, [messages]);

  const toggleSidebar = () => setSidebarOpen(prev => !prev);
  const toggleMap = () => {
    setMapVisible(!mapVisible);
    if (mapVisible) setFullscreenMap(false);
    if (mapVisible) {
      setChatAreaWidth(100);
    } else {
      setChatAreaWidth(50);
    }
  };
  const toggleFullscreenMap = () => setFullscreenMap(!fullscreenMap);

  const exampleQuestions = [
    "什么是虚拟星座？",
    "卫星监测水质的优势是什么？",
    "常用的遥感数据有哪些？"
  ];

  const exampleRequirements = [
    "我需要监测青海湖的水质变化，请规划方案",
    "我想了解城市热岛效应的监测方案",
    "我需要关注武汉市的城市扩张情况"
  ];

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
      if (extractionTimeoutRef.current) {
        clearTimeout(extractionTimeoutRef.current);
      }
      if (backendCheckRef.current) {
        clearInterval(backendCheckRef.current);
      }
    };
  }, []);

  // 🆕 如果显示卫星管理页面，直接返回卫星管理组件
  if (showSatelliteManagement) {
    return (
      <SatelliteManagement onBack={handleBackFromSatelliteManagement} />
    );
  }

  return (
    <ConversationProvider>
      <div className="flex h-screen overflow-hidden bg-gray-50">
        {!backendReady && (
          <div className="fixed top-0 left-0 right-0 bg-yellow-500 text-white text-center py-2 z-50">
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>正在连接后端服务...</span>
            </div>
          </div>
        )}

        {!fullscreenMap && (
          <div className={`${sidebarOpen ? 'w-64' : 'w-16'} flex-none transition-width duration-300 ease-in-out`}>
            <Sidebar
              isOpen={sidebarOpen}
              setIsOpen={setSidebarOpen}
              conversations={conversations}
              currentConversation={conversationId}
              onSelectConversation={handleSelectConversation}
              onNewConversation={handleNewConversation}
              onDeleteConversation={handleDeleteConversation}
              onRenameConversation={handleRenameConversation}
              loading={loading}
              refreshConversations={fetchConversations}
            />
          </div>
        )}

        <div className="flex-1 flex flex-col overflow-hidden">
          <Header
            toggleMap={toggleMap}
            mapVisible={mapVisible}
            fullscreenMap={fullscreenMap}
            toggleFullscreenMap={toggleFullscreenMap}
            onSatelliteManagement={handleSatelliteManagement}
          />

          <div className="flex-1 flex overflow-hidden" ref={chatContainerRef}>
            {(!mapVisible || (mapVisible && !fullscreenMap)) && (
              <div
                className="flex flex-col relative h-full"
                style={{
                  width: mapVisible && !fullscreenMap
                    ? `${chatAreaWidth}%`
                    : '100%'
                }}
              >
                <ResizableHandle
                  onDrag={handleResize}
                  isVisible={mapVisible && !fullscreenMap}
                />
                {messages.length === 0 && !loadingConversation ? (
                  <div className="flex flex-col items-center justify-center h-full p-4">
                    <div className="max-w-4xl w-full mx-auto text-center mb-8 mt-[-80px]">
                      <h2 className="text-2xl font-bold mb-6 text-gray-800">欢迎使用智慧虚拟星座集成管理系统</h2>

                      <div className="flex items-center justify-center mb-4 space-x-4">
                        <div className="flex items-center">
                          <div className={`w-2 h-2 rounded-full mr-2 ${backendReady ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
                          <span className="text-sm text-gray-600">
                            {backendReady ? '后端服务已连接' : '后端服务连接中...'}
                          </span>
                        </div>
                        <div className="flex items-center">
                          <div className={`w-2 h-2 rounded-full mr-2 ${wsConnected ? 'bg-green-500' : backendReady ? 'bg-yellow-500' : 'bg-gray-400'}`}></div>
                          <span className="text-sm text-gray-600">
                            {wsConnected ? '实时连接已建立' : backendReady ? '等待对话开始' : '等待后端就绪'}
                          </span>
                        </div>
                      </div>

                      <p className="text-gray-600 mb-8 max-w-2xl mx-auto">
                        您可以询问关于虚拟星座的问题，或描述您的观测需求，我将为您生成最适合的虚拟星座方案。
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto mb-8">
                        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                          <h3 className="font-bold text-lg mb-4 text-gray-700">示例问题</h3>
                          <ul className="space-y-3">
                            {exampleQuestions.map((question, index) => (
                              <li key={index}
                                  className="flex items-center text-gray-700 hover:text-gray-800 cursor-pointer"
                                  onClick={() => handleExampleClick(question)}>
                                <span className="text-gray-500 mr-2">•</span>
                                <span className="hover:underline">{question}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                          <h3 className="font-bold text-lg mb-4 text-gray-700">示例需求</h3>
                          <ul className="space-y-3">
                            {exampleRequirements.map((requirement, index) => (
                              <li key={index}
                                  className="flex items-center text-gray-700 hover:text-gray-800 cursor-pointer"
                                  onClick={() => handleExampleClick(requirement)}>
                                <span className="text-gray-500 mr-2">•</span>
                                <span className="hover:underline">{requirement}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div className="w-full">
                        <ChatInput
                          onSendMessage={handleSendMessage}
                          onFileUpload={handleFileUpload}
                          disabled={
                            (isProcessing && !isAwaitingClarification) ||
                            !backendReady ||
                            (conversationId && !wsConnected)
                          }
                          placeholder={isAwaitingClarification ? "请回答上述问题，或输入「跳过」使用默认参数..." : undefined}
                        />
                      </div>
                    </div>
                  </div>
                ) : loadingConversation ? (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-12 h-12 border-4 border-gray-300 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
                      <p className="text-gray-600">正在加载对话历史...</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <main ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 relative">
                      {showScrollToBottom && (
                        <button
                          onClick={() => scrollToBottom(true)}
                          className="fixed bottom-24 right-4 md:right-8 z-50 bg-blue-500 hover:bg-blue-600 text-white p-2 md:p-3 rounded-full shadow-lg transition-all duration-200 flex items-center gap-1 md:gap-2"
                          title="回到最新消息"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 md:h-5 md:w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                          </svg>
                          <span className="text-xs md:text-sm font-medium hidden md:inline">最新</span>
                        </button>
                      )}

                      <div className="w-full space-y-6">
                        {messages.map((msg, index) => (
                          <div key={msg.id} className="flex justify-center">
                            <div className="w-full space-y-4">
                              {msg.role === 'assistant' &&
                               !msg.isStreaming &&
                               msg.thinkingSteps &&
                               msg.thinkingSteps.length > 0 && (
                                <FixedThinkingProcess
                                  steps={msg.thinkingSteps}
                                  visible={true}
                                  isProcessing={false}
                                  title="思考过程"
                                />
                              )}

                              <EnhancedStreamingMessage
                                message={msg.content}
                                isUser={msg.role === 'user'}
                                timestamp={msg.timestamp}
                                isStreaming={msg.isStreaming}
                                accumulatedContent={msg.accumulatedContent || msg.content}
                                visualizationData={msg.visualizationData || currentVisualizationData}
                                satellites={msg.satellites}
                                isClarification={msg.isClarification}
                                isClarificationResponse={msg.isClarificationResponse}
                                onPlanOutputComplete={handlePlanOutputComplete}
                              />
                            </div>
                          </div>
                        ))}

                        {showClarificationDialog && clarificationQuestions.length > 0 && (
                          <div className="flex justify-center mb-4">
                            <div className="w-full max-w-2xl">
                              <ClarificationDialog
                                questions={clarificationQuestions}
                                onSubmit={handleClarificationSubmit}
                                onSkip={handleClarificationSkip}
                                isVisible={showClarificationDialog}
                                existingParams={existingParams}
                                parametersUncertainty={parametersUncertainty}
                                currentStage={currentClarificationStage}
                                stageName={stageName}
                                retryCount={stageRetryCount}
                              />
                            </div>
                          </div>
                        )}

                        {/* 🆕 新增：数据处理对话框 */}
                        {showDataProcessingDialog && (
                          <div className="flex justify-center mb-4">
                            <div className="w-full max-w-2xl">
                              <DataProcessingDialog
                                isVisible={showDataProcessingDialog}
                                satellites={currentSatellites}
                                conversationId={conversationId}
                                onConfirm={handleDataProcessingConfirm}
                                onCancel={handleDataProcessingCancel}
                                onClose={handleDataProcessingCancel}
                              />
                            </div>
                          </div>
                        )}

                        {/* 🆕 新增：处理结果对比视图 */}
                        {showResultViewer && (
                          <div className="flex justify-center mb-4">
                            <div className="w-full max-w-4xl">
                              <ProcessingResultViewer
                                isVisible={showResultViewer}
                                originalUrl={resultOriginalUrl}
                                processedUrl={resultProcessedUrl}
                                processingId={processingId}
                                onClose={() => setShowResultViewer(false)}
                              />
                            </div>
                          </div>
                        )}

                        {isProcessing &&
                         currentThinkingSteps.length > 0 &&
                         !streamingMessageIdRef.current && (
                          <div className="flex justify-center">
                            <div className="w-full">
                              <FixedThinkingProcess
                                steps={currentThinkingSteps}
                                visible={true}
                                isProcessing={true}
                                title="正在思考中..."
                              />
                            </div>
                          </div>
                        )}

                        <div ref={messagesEndRef} />
                      </div>
                    </main>

                    <div className="border-t border-gray-200">
                      <div className="max-w-4xl mx-auto">
                        <ChatInput
                          onSendMessage={handleSendMessage}
                          onFileUpload={handleFileUpload}
                          disabled={
                            (isProcessing && !isAwaitingClarification) ||
                            !backendReady ||
                            (conversationId && !wsConnected)
                          }
                          placeholder={isAwaitingClarification ? "请回答上述问题，或输入「跳过」使用默认参数..." : undefined}
                        />
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {mapVisible && (
              <div
                className="border-l border-gray-200 relative"
                style={{
                  width: fullscreenMap
                    ? '100%'
                    : `${100 - chatAreaWidth}%`
                }}
              >
                <button
                  className="absolute top-4 right-4 z-10 bg-white bg-opacity-75 p-2 rounded-full shadow-md hover:bg-opacity-100 transition-all"
                  onClick={toggleFullscreenMap}
                  title={fullscreenMap ? "退出全屏" : "全屏显示"}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {fullscreenMap ? (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5M15 15l5.25 5.25" />
                    ) : (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
                    )}
                  </svg>
                </button>

                <EnhancedCesiumMap
                  location={location}
                  visible={mapVisible}
                  satelliteNames={extractedSatellites}
                  onSatelliteClick={handleSatelliteClick}
                />

                <div className="absolute top-2 left-2 space-y-2">
                  {location && (
                    <div className="bg-white bg-opacity-75 p-2 rounded-md shadow-md">
                      <span className="text-sm font-medium">当前位置: {location}</span>
                    </div>
                  )}

                  {extractedSatellites.length > 0 && (
                    <div className="bg-white bg-opacity-75 p-2 rounded-md shadow-md">
                      <span className="text-sm font-medium">
                        🛰️ 已显示 {extractedSatellites.length} 颗卫星
                        {isExtractingSatellites && <span className="ml-2 animate-pulse">...</span>}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {deleteConfirmOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-sm mx-auto">
              <h3 className="text-lg font-medium text-gray-900 mb-4">确认删除</h3>
              <p className="text-sm text-gray-500 mb-4">
                您确定要删除这个对话吗？此操作无法撤销。
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={cancelDelete}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={confirmDelete}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 🆕 新增：数据处理进度条 */}
      <ProcessingProgressBar
        processingId={processingId}
        isVisible={showProgressBar}
        onComplete={handleDataProcessingComplete}
        onError={handleDataProcessingError}
      />
    </ConversationProvider>
  );
}

export default App;