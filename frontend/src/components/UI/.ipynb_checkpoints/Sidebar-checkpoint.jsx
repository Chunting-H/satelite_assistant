// Sidebar.jsx - 适配可调整宽度功能
import React, { useState } from 'react';

const Sidebar = ({
  isOpen,
  setIsOpen,
  conversations,
  currentConversation,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
  loading,
  refreshConversations,
  customWidth = 256  // 🆕 新增：接收自定义宽度
}) => {
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // 重命名相关状态
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);

  // 新增：导出相关状态
  const [isExporting, setIsExporting] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);

  // 新增：点击外部关闭导出菜单
  React.useEffect(() => {
    const handleClickOutside = (event) => {
      if (showExportMenu && !event.target.closest('.export-menu-container')) {
        setShowExportMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showExportMenu]);

  // 处理函数保持不变
  const handleNewConversation = () => {
    console.log("创建新对话");
    onNewConversation();
    if (window.innerWidth < 768) {
      setIsOpen(false);
    }
  };

  const handleSelectConversation = (conversationId) => {
    if (conversationId === currentConversation) {
      console.log(`当前已经选择了对话 ${conversationId}，跳过`);
      return;
    }
    console.log(`选择对话: ${conversationId}`);
    onSelectConversation(conversationId);
    if (window.innerWidth < 768) {
      setIsOpen(false);
    }
  };

  const handleDeleteConversation = (conversationId, event) => {
    event.stopPropagation();
    console.log(`准备删除对话: ${conversationId}`);
    onDeleteConversation(conversationId);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    console.log("手动刷新对话列表");
    try {
      await refreshConversations(true);
    } catch (error) {
      console.error("刷新对话列表失败:", error);
      setError(error.message || "刷新失败，请重试");
    } finally {
      setRefreshing(false);
    }
  };

  // 重命名相关函数
  const startEditing = (conversationId, currentTitle, event) => {
    event.stopPropagation();
    setEditingId(conversationId);
    setEditingTitle(currentTitle);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditingTitle('');
    setIsRenaming(false);
  };

  const confirmRename = async (event) => {
    if (event) {
      event.stopPropagation();
    }

    if (!editingTitle.trim() || isRenaming) return;

    setIsRenaming(true);
    try {
      await onRenameConversation(editingId, editingTitle.trim());
      setEditingId(null);
      setEditingTitle('');
    } catch (error) {
      console.error('重命名失败:', error);
      alert('重命名失败: ' + error.message);
    } finally {
      setIsRenaming(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.stopPropagation();
      confirmRename();
    } else if (e.key === 'Escape') {
      cancelEditing();
    }
  };

  // 新增：导出单个对话
  const handleExportConversation = async (conversationId, format = 'txt') => {
    setIsExporting(true);
    try {
      console.log(`开始导出对话: ${conversationId}, 格式: ${format}`);
      
      // 获取对话详情
      const response = await fetch(`/api/conversation/${conversationId}`);
      if (!response.ok) {
        throw new Error(`获取对话失败: ${response.status} ${response.statusText}`);
      }
      
      const conversation = await response.json();
      console.log('API响应:', conversation);
      
      // 验证响应数据结构
      if (!conversation.metadata || !conversation.metadata.messages) {
        throw new Error('对话数据格式不正确，缺少消息信息');
      }
      
      // 格式化对话内容
      const formattedContent = formatConversationContent(conversation, format);
      console.log(`格式化完成，内容长度: ${formattedContent.length}`);
      
      // 获取对话标题
      const title = conversation.metadata?.custom_title || 
                   conversation.metadata?.messages?.[0]?.content?.substring(0, 30) || 
                   '对话';
      
      // 下载文件
      downloadFile(formattedContent, title, format);
      
    } catch (error) {
      console.error('导出对话失败:', error);
      alert('导出失败: ' + error.message);
    } finally {
      setIsExporting(false);
    }
  };

  // 新增：批量导出所有对话
  const handleExportAllConversations = async (format = 'txt') => {
    setIsExporting(true);
    try {
      console.log(`开始批量导出，格式: ${format}, 对话数量: ${validConversations.length}`);
      
      const allConversations = [];
      
      // 获取所有对话的详细信息
      for (const conversation of validConversations) {
        try {
          console.log(`获取对话详情: ${conversation.conversation_id}`);
          const response = await fetch(`/api/conversation/${conversation.conversation_id}`);
          if (response.ok) {
            const conv = await response.json();
            
            // 验证响应数据结构
            if (conv.metadata && conv.metadata.messages) {
              allConversations.push(conv);
              console.log(`成功获取对话: ${conversation.conversation_id}, 消息数量: ${conv.metadata.messages.length}`);
            } else {
              console.warn(`对话 ${conversation.conversation_id} 数据格式不正确，跳过`);
            }
          } else {
            console.warn(`获取对话 ${conversation.conversation_id} 失败: ${response.status}`);
          }
        } catch (error) {
          console.error(`获取对话 ${conversation.conversation_id} 失败:`, error);
        }
      }
      
      console.log(`成功获取 ${allConversations.length} 个对话的详细信息`);
      
      if (allConversations.length === 0) {
        throw new Error('没有可导出的对话');
      }
      
      // 格式化所有对话内容
      const formattedContent = formatAllConversationsContent(allConversations, format);
      console.log(`批量格式化完成，内容长度: ${formattedContent.length}`);
      
      // 下载文件
      downloadFile(formattedContent, '所有对话', format);
      
    } catch (error) {
      console.error('批量导出失败:', error);
      alert('批量导出失败: ' + error.message);
    } finally {
      setIsExporting(false);
    }
  };

  // 新增：格式化对话内容
  const formatConversationContent = (conversation, format) => {
    // 从API响应中正确提取数据
    const messages = conversation.metadata?.messages || [];
    const title = conversation.metadata?.custom_title || '对话';
    const conversation_id = conversation.conversation_id;
    
    // 从消息中提取时间戳，并确保时间戳是有效的
    const created_at = messages.length > 0 ? messages[0].timestamp : Date.now();
    const updated_at = messages.length > 0 ? messages[messages.length - 1].timestamp : Date.now();
    
    // 验证时间戳格式并转换为正确的时间
    const formatTimestamp = (timestamp) => {
      try {
        // 检查时间戳是否为数字
        if (typeof timestamp !== 'number') {
          console.warn('时间戳不是数字:', timestamp);
          return new Date().toLocaleString('zh-CN');
        }
        
        // 检查时间戳是否合理（1970年到2100年之间）
        const date = new Date(timestamp * 1000); // 转换为毫秒
        const year = date.getFullYear();
        
        if (year < 1970 || year > 2100) {
          console.warn('时间戳超出合理范围:', timestamp, '年份:', year);
          return new Date().toLocaleString('zh-CN');
        }
        
        return date.toLocaleString('zh-CN');
      } catch (error) {
        console.error('时间戳格式化失败:', error, '时间戳:', timestamp);
        return new Date().toLocaleString('zh-CN');
      }
    };
    
    console.log('对话时间戳信息:', {
      conversation_id,
      message_count: messages.length,
      created_at: formatTimestamp(created_at),
      updated_at: formatTimestamp(updated_at),
      first_message_timestamp: messages.length > 0 ? messages[0].timestamp : 'N/A',
      last_message_timestamp: messages.length > 0 ? messages[messages.length - 1].timestamp : 'N/A'
    });
    
    if (format === 'json') {
      return JSON.stringify(conversation, null, 2);
    }
    
    if (format === 'markdown') {
      let content = `# ${title}\n\n`;
      content += `**对话ID**: ${conversation_id}\n`;
      content += `**创建时间**: ${formatTimestamp(created_at)}\n`;
      content += `**更新时间**: ${formatTimestamp(updated_at)}\n`;
      content += `**消息数量**: ${messages.length}\n\n`;
      content += `---\n\n`;
      
      messages.forEach((msg, index) => {
        content += `## ${msg.role === 'user' ? '用户' : '助手'} (${formatTimestamp(msg.timestamp)})\n\n`;
        content += `${msg.content}\n\n`;
        content += `---\n\n`;
      });
      
      return content;
    }
    
    // 默认TXT格式
    let content = `对话标题: ${title}\n`;
    content += `对话ID: ${conversation_id}\n`;
    content += `创建时间: ${formatTimestamp(created_at)}\n`;
    content += `更新时间: ${formatTimestamp(updated_at)}\n`;
    content += `消息数量: ${messages.length}\n`;
    content += `${'='.repeat(50)}\n\n`;
    
    messages.forEach((msg, index) => {
      content += `${msg.role === 'user' ? '用户' : '助手'} (${formatTimestamp(msg.timestamp)}):\n`;
      content += `${msg.content}\n\n`;
      content += `${'-'.repeat(30)}\n\n`;
    });
    
    return content;
  };

  // 新增：格式化所有对话内容
  const formatAllConversationsContent = (conversations, format) => {
    if (format === 'json') {
      return JSON.stringify(conversations, null, 2);
    }
    
    if (format === 'markdown') {
      let content = `# 所有对话记录\n\n`;
      content += `**导出时间**: ${new Date().toLocaleString('zh-CN')}\n`;
      content += `**对话数量**: ${conversations.length}\n\n`;
      content += `---\n\n`;
      
      conversations.forEach((conversation, index) => {
        content += formatConversationContent(conversation, 'markdown');
        if (index < conversations.length - 1) {
          content += `\n\n${'='.repeat(50)}\n\n`;
        }
      });
      
      return content;
    }
    
    // 默认TXT格式
    let content = `所有对话记录\n`;
    content += `导出时间: ${new Date().toLocaleString('zh-CN')}\n`;
    content += `对话数量: ${conversations.length}\n`;
    content += `${'='.repeat(50)}\n\n`;
    
    conversations.forEach((conversation, index) => {
      content += formatConversationContent(conversation, 'txt');
      if (index < conversations.length - 1) {
        content += `\n\n${'='.repeat(80)}\n\n`;
      }
    });
    
    return content;
  };

  // 新增：下载文件
  const downloadFile = (content, filename, format) => {
    try {
      const mimeTypes = {
        'txt': 'text/plain;charset=utf-8',
        'json': 'application/json;charset=utf-8',
        'markdown': 'text/markdown;charset=utf-8'
      };
      
      const extensions = {
        'txt': 'txt',
        'json': 'json',
        'markdown': 'md'
      };
      
      // 清理文件名，移除特殊字符
      const cleanFilename = filename.replace(/[<>:"/\\|?*]/g, '_').trim();
      
      const blob = new Blob([content], { type: mimeTypes[format] });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${cleanFilename}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${extensions[format]}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      console.log(`文件下载成功: ${a.download}`);
    } catch (error) {
      console.error('文件下载失败:', error);
      alert('文件下载失败: ' + error.message);
    }
  };

  // 确保conversations是数组
  const validConversations = Array.isArray(conversations) ? conversations : [];

  // 🆕 计算收起状态的最小宽度
  const collapsedWidth = 64;
  const isCollapsed = !isOpen || customWidth <= collapsedWidth;

  // 侧边栏收起时的样式
  if (isCollapsed) {
    return (
      <div 
        className="h-full bg-gray-50 text-gray-700 flex flex-col items-center py-4 fixed left-0 top-0 bottom-0 z-20 border-r border-gray-200"
        style={{ width: `${collapsedWidth}px` }} // 🆕 使用固定的收起宽度
      >
        <div className="mb-6 w-10 h-10 flex items-center justify-center">
          <button
            className="w-8 h-8 text-gray-700 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors"
            title="展开侧边栏"
            onClick={() => setIsOpen(true)}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        <button
          className="w-10 h-10 bg-white text-gray-800 rounded-full flex items-center justify-center mb-8 hover:bg-gray-100 transition-colors shadow-sm border border-gray-200"
          onClick={handleNewConversation}
          title="新建对话"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </button>

        <button
          className="w-8 h-8 text-gray-700 mb-4 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors"
          title="对话历史"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </button>

        <button
          className="w-8 h-8 text-gray-700 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors mt-4"
          title="文件管理"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div 
      className="h-screen flex flex-col bg-gray-50 text-gray-800 fixed left-0 top-0 z-20 border-r border-gray-200"
      style={{ width: `${customWidth}px` }} // 🆕 使用传入的自定义宽度
    >
      {/* 头部 - 带有系统名称和关闭按钮 */}
      <div className="flex-none p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3 min-w-0"> {/* 🆕 添加 min-w-0 防止文字溢出 */}
          <button
            className="text-gray-500 hover:bg-gray-200 rounded p-1 flex-shrink-0" // 🆕 添加 flex-shrink-0
            onClick={() => setIsOpen(false)}
            title="收起侧边栏"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          {/* 🆕 文字根据宽度自适应显示 */}
          <h2 className={`text-base font-medium text-gray-800 truncate ${
            customWidth < 200 ? 'text-xs' : 'text-base'
          }`}>
            {customWidth < 220 ? '星座助手' : '智慧虚拟星座'}
          </h2>
        </div>
      </div>

      {/* 新建对话按钮 */}
      <div className="flex-none px-4 py-3">
        <button
          className="w-full bg-white text-gray-800 py-2 px-4 rounded-md flex items-center justify-center transition-colors hover:bg-gray-100 border border-gray-200 shadow-sm"
          onClick={handleNewConversation}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          {/* 🆕 根据宽度决定是否显示文字 */}
          {customWidth >= 180 && <span>新建对话</span>}
        </button>
      </div>

      {/* 对话历史标题 */}
      <div className="flex-none px-4 py-2 flex items-center justify-between">
        <h3 className={`font-medium text-gray-600 truncate ${
          customWidth < 200 ? 'text-xs' : 'text-sm'
        }`}>
          {customWidth < 220 ? '历史' : '对话历史'}
        </h3>
        <div className="flex items-center gap-1">
          {/* 导出按钮 */}
          <div className="relative export-menu-container">
            <button
              className="text-gray-500 hover:text-gray-700 p-1 rounded flex-shrink-0"
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={isExporting || validConversations.length === 0}
              title="导出对话"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
            
            {/* 导出菜单 */}
            {showExportMenu && (
              <div className="absolute right-0 top-8 w-48 bg-white border border-gray-200 rounded-md shadow-lg z-50">
                <div className="py-1">
                  <div className="px-3 py-2 text-xs font-medium text-gray-500 border-b border-gray-100">
                    导出当前对话
                  </div>
                  <button
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    onClick={() => {
                      handleExportConversation(currentConversation, 'txt');
                      setShowExportMenu(false);
                    }}
                    disabled={!currentConversation || isExporting}
                  >
                    📄 文本文件 (.txt)
                  </button>
                  <button
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    onClick={() => {
                      handleExportConversation(currentConversation, 'markdown');
                      setShowExportMenu(false);
                    }}
                    disabled={!currentConversation || isExporting}
                  >
                    📝 Markdown (.md)
                  </button>
                  <button
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    onClick={() => {
                      handleExportConversation(currentConversation, 'json');
                      setShowExportMenu(false);
                    }}
                    disabled={!currentConversation || isExporting}
                  >
                    🔧 JSON (.json)
                  </button>
                  
                  <div className="px-3 py-2 text-xs font-medium text-gray-500 border-b border-gray-100 mt-2">
                    批量导出
                  </div>
                  <button
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    onClick={() => {
                      handleExportAllConversations('txt');
                      setShowExportMenu(false);
                    }}
                    disabled={isExporting || validConversations.length === 0}
                  >
                    📚 所有对话 (.txt)
                  </button>
                  <button
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    onClick={() => {
                      handleExportAllConversations('markdown');
                      setShowExportMenu(false);
                    }}
                    disabled={isExporting || validConversations.length === 0}
                  >
                    📚 所有对话 (.md)
                  </button>
                  <button
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    onClick={() => {
                      handleExportAllConversations('json');
                      setShowExportMenu(false);
                    }}
                    disabled={isExporting || validConversations.length === 0}
                  >
                    📚 所有对话 (.json)
                  </button>
                </div>
              </div>
            )}
          </div>
          
          {/* 刷新按钮 */}
          <button
            className="text-gray-500 hover:text-gray-700 p-1 rounded flex-shrink-0"
            onClick={handleRefresh}
            disabled={refreshing}
            title="刷新列表"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="flex-none mx-4 mb-2 px-3 py-2 text-xs bg-red-100 text-red-800 rounded-md flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1 text-red-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="truncate">{error}</span>
        </div>
      )}

      {/* 对话列表 - 可滚动区域 */}
      <div className="flex-1 overflow-y-auto">
        {validConversations.length > 0 ? (
          <div className="space-y-0.5 px-2">
            {validConversations.map((conversation) => (
              <div
                key={conversation.conversation_id}
                className={`flex items-center group cursor-pointer px-3 py-3 rounded-md ${
                  currentConversation === conversation.conversation_id 
                    ? 'bg-gray-200 text-gray-900' 
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                {editingId === conversation.conversation_id ? (
                  // 编辑模式
                  <div className="flex items-center w-full gap-2" onClick={(e) => e.stopPropagation()}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                    <input
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={handleKeyPress}
                      className="flex-1 bg-white text-gray-800 px-2 py-1 rounded text-sm border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-0"
                      autoFocus
                      disabled={isRenaming}
                    />
                    <button
                      onClick={confirmRename}
                      disabled={isRenaming || !editingTitle.trim()}
                      className="text-green-600 hover:text-green-700 disabled:text-gray-400 flex-shrink-0"
                      title="确认"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </button>
                    <button
                      onClick={cancelEditing}
                      disabled={isRenaming}
                      className="text-red-600 hover:text-red-700 disabled:text-gray-400 flex-shrink-0"
                      title="取消"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ) : (
                  // 正常显示模式
                  <>
                    <div
                      className="flex items-center flex-1 min-w-0"
                      onClick={() => handleSelectConversation(conversation.conversation_id)}
                    >
                      {/* 对话图标 */}
                      <div className="mr-3 flex-shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                      </div>

                      {/* 对话标题 */}
                      <div className="flex-1 min-w-0 text-sm">
                        <div className="truncate">
                          {conversation.title || '新对话'}
                        </div>
                      </div>
                    </div>

                    {/* 操作按钮组 - 鼠标悬停时显示 */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {/* 重命名按钮 */}
                      <button
                        className="p-1 rounded text-gray-500 hover:bg-gray-200 hover:text-gray-700 flex-shrink-0"
                        onClick={(e) => startEditing(conversation.conversation_id, conversation.title || '新对话', e)}
                        title="重命名"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>

                      {/* 删除按钮 */}
                      <button
                        className="p-1 rounded text-gray-500 hover:bg-gray-200 hover:text-red-600 flex-shrink-0"
                        onClick={(e) => handleDeleteConversation(conversation.conversation_id, e)}
                        title="删除对话"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-32 p-4 text-gray-500">
            {loading ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                加载中...
              </div>
            ) : (
              <>
                <p className="text-center mb-2 text-sm">还没有对话记录</p>
                <p className="text-center text-xs opacity-75">点击"新建对话"开始聊天</p>
              </>
            )}
          </div>
        )}
      </div>

      {/* 底部信息 */}
      <div className="flex-none px-4 py-3 border-t border-gray-200 flex justify-between items-center">
        <div className="min-w-0 flex-1">
          <div className={`text-gray-600 truncate ${
            customWidth < 200 ? 'text-xs' : 'text-xs'
          }`}>
            {customWidth < 220 ? '星座助手' : '智慧化虚拟星座助手'}
          </div>
          <div className="text-xs text-gray-500">版本 1.0.0</div>
        </div>
        <button className="text-gray-500 hover:text-gray-700 flex-shrink-0">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;