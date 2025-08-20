// App.jsx - 完整代码（包含所有修改）
import { useState, useEffect, useRef } from 'react';
import { sendMessage, uploadFile, getConversation, listConversations, deleteConversation } from './services/api';
import { extractLocation } from './services/location';
import { ConversationProvider } from './contexts/ConversationContext';
import Header from './components/UI/Header';
import Sidebar from './components/UI/Sidebar';
import ChatInput from './components/Chat/ChatInput';
import ChatMessage from './components/Chat/ChatMessage';
import ThinkingProcess from './components/Chat/ThinkingProcess';
import 'cesium/Build/Cesium/Widgets/widgets.css';
// 导入SimpleCesiumMap组件，不再使用内联定义
import SimpleCesiumMap from './components/Map/SimpleCesiumMap';

function App() {
  // 消息和对话状态
  const [messages, setMessages] = useState([]);
  const [thinking, setThinking] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);

  // 删除确认状态
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deletingConversationId, setDeletingConversationId] = useState(null);

  // UI 状态
  const isDesktop = useRef(window.innerWidth >= 768);
  const [sidebarOpen, setSidebarOpen] = useState(isDesktop.current);
  const [location, setLocation] = useState(null);
  const [mapVisible, setMapVisible] = useState(false);
  const [fullscreenMap, setFullscreenMap] = useState(false);
  const messagesEndRef = useRef(null);

  // 添加自定义样式到document.head
  useEffect(() => {
    const style = document.createElement('style');
    style.innerHTML = `
      .transition-width {
        transition-property: width;
        transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
        transition-duration: 300ms;
      }
      
      .group:hover .group-hover\\:opacity-100 {
        opacity: 1 !important;
      }
    `;
    document.head.appendChild(style);
    return () => document.head.removeChild(style);
  }, []);

  // 监听窗口大小变化，自动调整侧边栏状态
  useEffect(() => {
    const handleResize = () => {
      const desktop = window.innerWidth >= 768;
      // 只在设备类型变化时才自动更新侧边栏状态
      if (desktop !== isDesktop.current) {
        isDesktop.current = desktop;
        setSidebarOpen(desktop);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 滚动到最新消息
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinking]);

  // 获取对话列表
  const fetchConversations = async (force = false) => {
    try {
      setLoading(true);
      console.log("正在获取对话列表...");
      const data = await listConversations();
      console.log("获取到的对话列表:", data);

      if (data && Array.isArray(data.conversations)) {
        setConversations(data.conversations);
        console.log(`成功获取 ${data.conversations.length} 个对话`);
      } else {
        console.warn('获取对话列表返回格式不正确', data);
        setConversations([]);
      }
    } catch (error) {
      console.error('获取对话列表失败:', error);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  // 获取特定对话的消息
  const fetchConversationMessages = async (convId) => {
    if (!convId) {
      console.log('没有提供对话ID，跳过获取消息');
      return;
    }

    try {
      setLoading(true);
      console.log(`获取对话 ${convId} 的消息历史...`);

      const response = await getConversation(convId);
      console.log('获取到对话详情响应:', response);

      // 尝试从metadata.messages获取消息数组
      if (response && response.metadata && Array.isArray(response.metadata.messages)) {
        const formattedMessages = response.metadata.messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp * 1000
        }));

        console.log(`成功获取 ${formattedMessages.length} 条消息`, formattedMessages);
        setMessages(formattedMessages);
      } else {
        // 回退方案：创建一个基本的消息列表
        if (response && response.message) {
          const assistantMessage = {
            role: 'assistant',
            content: response.message,
            timestamp: new Date().getTime()
          };

          setMessages([assistantMessage]);
          console.log('创建单条消息');
        } else {
          console.warn('响应中没有消息内容');
          setMessages([]);
        }
      }
    } catch (error) {
      console.error('获取对话消息失败:', error);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  // 在组件加载时获取对话列表
  useEffect(() => {
    console.log("App组件加载，获取对话列表");
    fetchConversations();

    // 设置定时刷新
    const intervalId = setInterval(() => {
      console.log("定时刷新对话列表");
      fetchConversations();
    }, 30000);

    return () => clearInterval(intervalId);
  }, []);

  // 处理创建新对话
  const handleNewConversation = () => {
    console.log("创建新对话");
    setConversationId(null);
    setMessages([]);
  };

  // 处理选择对话
  const handleSelectConversation = (convId) => {
    if (convId === conversationId) {
      console.log(`当前已选择对话 ${convId}，跳过`);
      return;
    }

    console.log(`选择对话: ${convId}`);
    setConversationId(convId);
    fetchConversationMessages(convId);
  };

  // 处理删除对话
  const handleDeleteConversation = (id) => {
    console.log(`准备删除对话: ${id}`);
    setDeletingConversationId(id);
    setDeleteConfirmOpen(true);
  };

  // 确认删除对话
  const confirmDelete = async () => {
    try {
      if (!deletingConversationId) return;

      console.log(`正在删除对话: ${deletingConversationId}`);
      setLoading(true);

      // 调用删除API
      await deleteConversation(deletingConversationId);

      // 如果删除的是当前对话，重置当前对话
      if (deletingConversationId === conversationId) {
        setConversationId(null);
        setMessages([]);
      }

      // 重新获取对话列表
      await fetchConversations(true);

      // 关闭确认对话框
      setDeleteConfirmOpen(false);
      setDeletingConversationId(null);
    } catch (error) {
      console.error('删除对话失败:', error);
      alert('删除对话失败: ' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  // 取消删除
  const cancelDelete = () => {
    setDeleteConfirmOpen(false);
    setDeletingConversationId(null);
  };

  // 添加示例问题处理函数
  const handleExampleClick = (question) => {
    handleSendMessage(question);
  };

  // 发送消息处理
  const handleSendMessage = async (text) => {
    // 在小屏幕上发送消息时自动关闭侧边栏
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }

    // 添加用户消息到UI
    const newMessages = [...messages, {
      role: 'user',
      content: text,
      timestamp: new Date().getTime()
    }];
    setMessages(newMessages);

    setThinking(true);
    setThinkingSteps([]);

    try {
      // 尝试提取地点信息
      try {
        const extractedLocation = await extractLocation(text);
        if (extractedLocation && extractedLocation.length > 1) {
          console.log("提取到地点:", extractedLocation);
          setLocation(extractedLocation);
          setMapVisible(true);
        }
      } catch (locError) {
        console.error("地点提取失败:", locError);
      }

      // 调用API发送消息
      const response = await sendMessage(text, conversationId);

      // 更新会话ID
      if (response && response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id);
      }

      // 添加思考步骤（如果有）
      if (response && response.thinking_steps && Array.isArray(response.thinking_steps)) {
        setThinkingSteps(response.thinking_steps);
      }

      // 添加助手回复
      setMessages([...newMessages, {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().getTime()
      }]);

    } catch (error) {
      console.error('发送消息失败:', error);
      setMessages([...newMessages, {
        role: 'assistant',
        content: '抱歉，处理您的请求时出错，请稍后重试。',
        timestamp: new Date().getTime()
      }]);
    } finally {
      setThinking(false);
    }
  };

  // 文件上传处理
  const handleFileUpload = async (file) => {
    try {
      const response = await uploadFile(file, conversationId);

      // 添加系统消息，显示文件上传成功
      setMessages([...messages, {
        role: 'assistant',
        content: `文件上传成功: ${file.name}\n\n您可以继续提问，我将结合这个文件回答您的问题。`,
        timestamp: new Date().getTime()
      }]);

    } catch (error) {
      console.error('文件上传失败:', error);
      setMessages([...messages, {
        role: 'assistant',
        content: `文件上传失败: ${error.message}`,
        timestamp: new Date().getTime()
      }]);
    }
  };

  // 切换侧边栏
  const toggleSidebar = () => {
    console.log('侧边栏切换，当前状态:', sidebarOpen);
    setSidebarOpen(prev => !prev);
  };

  // 切换地图显示
  const toggleMap = () => {
    setMapVisible(!mapVisible);
    // 如果关闭地图，同时确保退出全屏模式
    if (mapVisible) {
      setFullscreenMap(false);
    }
  };

  // 切换地图全屏
  const toggleFullscreenMap = () => {
    setFullscreenMap(!fullscreenMap);
  };

  // 示例问题列表
  const exampleQuestions = [
    "什么是虚拟星座？",
    "卫星监测水质的优势是什么？",
    "常用的遥感数据有哪些？"
  ];

  // 示例需求列表
  const exampleRequirements = [
    "我需要监测青海湖的水质变化，请规划方案",
    "我想了解城市热岛效应的监测方案",
    "我需要关注武汉市的城市扩张情况"
  ];

  return (
    <ConversationProvider>
      <div className="flex h-screen overflow-hidden bg-gray-50">
        {/* 侧边栏 - 在地图全屏时隐藏 */}
        {!fullscreenMap && (
          <div
            className={`${sidebarOpen ? 'w-64' : 'w-16'} flex-none transition-width duration-300 ease-in-out`}
          >
            <Sidebar
              isOpen={sidebarOpen}
              setIsOpen={setSidebarOpen}
              conversations={conversations}
              currentConversation={conversationId}
              onSelectConversation={handleSelectConversation}
              onNewConversation={handleNewConversation}
              onDeleteConversation={handleDeleteConversation}
              loading={loading}
              refreshConversations={fetchConversations}
            />
          </div>
        )}

        {/* 主内容区 */}
        <div className={`flex-1 flex flex-col overflow-hidden transition-all duration-300`}>
          {/* Header - 移除了toggleSidebar */}
          <Header
            toggleMap={toggleMap}
            mapVisible={mapVisible}
            fullscreenMap={fullscreenMap}
            toggleFullscreenMap={toggleFullscreenMap}
          />

          <div className="flex-1 flex overflow-hidden">
            {/* 聊天区域 - 在地图全屏时隐藏 */}
            {(!mapVisible || (mapVisible && !fullscreenMap)) && (
              <div
                className={`${mapVisible && !fullscreenMap ? 'w-1/2' : 'w-full'} flex flex-col overflow-hidden transition-all duration-300`}
              >
                {messages.length === 0 ? (
                  // 初始状态 - 欢迎页面和输入框在中间位置 - 添加了mt-[-80px]使内容上移居中
                  <div className="flex flex-col items-center justify-center h-full p-4">
                    <div className="max-w-4xl w-full mx-auto text-center mb-8 mt-[-80px]">
                      <h2 className="text-2xl font-bold mb-6 text-gray-800">欢迎使用智慧虚拟星座助手</h2>
                      <p className="text-gray-600 mb-8 max-w-2xl mx-auto">
                        您可以询问关于虚拟星座的问题，或描述您的观测需求，我将为您生成最适合的虚拟星座方案。
                        <br />
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

                      {/* 输入框在中间 */}
                      <div className="w-full">
                        <ChatInput
                          onSendMessage={handleSendMessage}
                          onFileUpload={handleFileUpload}
                          disabled={thinking}
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  // 有消息时的布局 - 聊天区域在上方，输入框在底部
                  <>
                    <main className="flex-1 overflow-y-auto p-4">
                      <div className="w-full">
                        <div className="space-y-6">
                          {messages.map((msg, index) => (
                            <div key={index} className="flex justify-center">
                              <div className="w-full">
                                <ChatMessage
                                  message={msg.content}
                                  isUser={msg.role === 'user'}
                                  timestamp={msg.timestamp}
                                />
                              </div>
                            </div>
                          ))}

                          {thinking && (
                            <div className="flex justify-center">
                              <div className="w-full max-w-3xl">
                                <ThinkingProcess
                                  steps={thinkingSteps}
                                  visible={thinking}
                                />
                              </div>
                            </div>
                          )}
                        </div>
                        <div ref={messagesEndRef} />
                      </div>
                    </main>

                    <div className="border-t border-gray-200">
                      <div className="max-w-4xl mx-auto">
                        <ChatInput
                          onSendMessage={handleSendMessage}
                          onFileUpload={handleFileUpload}
                          disabled={thinking}
                        />
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* 地图区域 */}
            {mapVisible && (
              <div className={`${fullscreenMap ? 'w-full' : 'w-1/2'} border-l border-gray-200 relative transition-all duration-300`}>
                {/* 添加全屏/退出全屏按钮 */}
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

                <SimpleCesiumMap location={location} visible={mapVisible} />
                {location && (
                  <div className="absolute top-2 left-2 bg-white bg-opacity-75 p-2 rounded-md shadow-md">
                    <span className="text-sm font-medium">当前位置: {location}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 删除确认对话框 */}
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
    </ConversationProvider>
  );
}

export default App;