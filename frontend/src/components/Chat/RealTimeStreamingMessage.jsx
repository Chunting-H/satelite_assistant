// components/Chat/RealTimeStreamingMessage.jsx - 优化流式消息显示
import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const RealTimeStreamingMessage = ({
  message,
  isUser,
  timestamp,
  isStreaming = false,
  accumulatedContent = ""
}) => {
  const [displayContent, setDisplayContent] = useState(message || "");
  const mountedRef = useRef(true);
  const lastContentRef = useRef("");

  // 格式化时间
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // 🔧 新增：内容预处理函数，统一换行符和格式
  const preprocessContent = (content) => {
    if (!content) return content;
    // 合并“数字. + 多余空行 + 标题”
    content = content.replace(/(^|\n)(\d+)\.\s*\n{1,3}\s*([^\n]+)/g, '$1$2. $3');
    content = content.replace(/(^|\n)(#+)\s*(\d+)\.\s*\n{1,3}\s*([^\n]+)/g, '$1$2 $3. $4');
    // 合并“数字、/)/- + 多余空行 + 标题”
    content = content.replace(/(^|\n)(\d+)[、\)\-]\s*\n{1,3}\s*([^\n]+)/g, '$1$2. $3');
    content = content.replace(/(^|\n)(#+)\s*(\d+)[、\)\-]\s*\n{1,3}\s*([^\n]+)/g, '$1$2 $3. $4');
    // 归一化所有2个及以上空行为1个
    content = content.replace(/\n{2,}/g, '\n\n');
    // 统一换行符
    content = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    // 去除段落前后多余空格
    content = content.replace(/[ \t]+\n/g, '\n').replace(/\n[ \t]+/g, '\n');
    return content.trim();
  };

  // 🔥 关键修复：立即响应内容变化，无防抖
  useEffect(() => {
    let newContent = "";

    if (isStreaming && accumulatedContent) {
      // 流式状态优先使用累积内容
      newContent = accumulatedContent;
    } else if (!isStreaming && message) {
      // 非流式状态使用最终消息
      newContent = message;
    } else if (message) {
      // 回退到message
      newContent = message;
    }

    // 🔧 新增：应用内容预处理
    newContent = preprocessContent(newContent);

    // 🎯 关键：只要内容有变化就立即更新，不做任何延迟
    if (newContent && newContent !== lastContentRef.current) {
      console.log('🔄 消息组件立即更新:', {
        oldLength: lastContentRef.current.length,
        newLength: newContent.length,
        isStreaming,
        messageId: timestamp, // 用timestamp作为消息标识
        preview: newContent.slice(-50) + (newContent.length > 50 ? '...' : '')
      });

      setDisplayContent(newContent);
      lastContentRef.current = newContent;
    }
  }, [isStreaming, accumulatedContent, message]); // 监听所有可能的内容变化

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      mountedRef.current = false;
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
              h1: ({node, ...props}) => <h1 className="text-xl font-bold mb-4 text-gray-900" {...props} />,
              h2: ({node, ...props}) => <h2 className="text-lg font-semibold mb-3 text-gray-800" {...props} />,
              h3: ({node, ...props}) => <h3 className="text-md font-medium mb-3 text-gray-700" {...props} />,
              // 🔧 修改：统一段落间距为 mb-3 (0.75rem)
              p: ({node, ...props}) => <p className="mb-3 text-gray-700 leading-relaxed" {...props} />,
              // 🔧 修改：统一列表间距
              ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-3 text-gray-700" {...props} />,
              ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-3 text-gray-700" {...props} />,
              li: ({node, ...props}) => <li className="mb-1" {...props} />,
              strong: ({node, ...props}) => <strong className="font-semibold text-gray-800" {...props} />,
              table: ({node, ...props}) => (
                <div className="overflow-x-auto my-4">
                  <table className="min-w-full border-collapse border border-gray-300" {...props} />
                </div>
              ),
              thead: ({node, ...props}) => <thead className="bg-gray-50" {...props} />,
              th: ({node, ...props}) => <th className="border border-gray-300 px-3 py-2 text-left font-medium text-gray-700" {...props} />,
              td: ({node, ...props}) => <td className="border border-gray-300 px-3 py-2 text-gray-700" {...props} />,
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
      return <p className="whitespace-pre-wrap break-words text-gray-700">{displayContent}</p>;
    }
  };

  // 检测是否是方案生成内容
  const isPlanContent = displayContent.includes('# ') || displayContent.includes('## ') || displayContent.includes('### ');

  return (
    <div className="mb-6">
      {/* 用户信息和时间戳 */}
    <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
      <div className="flex items-center gap-2">
        <span className="font-medium">
          {isUser ? '您' : '智慧虚拟星座助手'}
        </span>

        {/* 🔧 优化流式状态指示器 - 确保只在流式进行中显示 */}
        {isStreaming && !isUser && displayContent && displayContent.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce delay-100"></div>
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce delay-200"></div>
            </div>
            <span className="text-blue-600 text-xs font-medium">
              {isPlanContent ? '正在生成方案...' : '正在回复中...'}
            </span>
          </div>
        )}

        {/* 🔧 确保完成指示器只在非流式状态显示 */}
        {!isStreaming && !isUser && displayContent && displayContent.length > 10 && (
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-green-600 text-xs">
              {isPlanContent ? '方案生成完成' : '回复完成'}
            </span>
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

        {/* 🔧 优化方案标题指示器 */}
        {!isUser && isPlanContent && displayContent.length > 50 && (
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-blue-200">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span className="text-sm font-medium text-blue-700">虚拟星座方案</span>
            {isStreaming && (
              <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
                实时生成中...
              </span>
            )}
          </div>
        )}

        <div className="whitespace-pre-wrap break-words">
          {/* 🔧 只在有实质内容时渲染 */}
          {displayContent && displayContent.length > 0 ? (
            <>
              {renderContent(displayContent)}

              {/* 🔧 优化流式输入光标 - 只在真正流式且有内容时显示 */}
              {isStreaming && !isUser && displayContent.length > 10 && (
                <span className="inline-block w-2 h-5 bg-blue-400 ml-1 animate-pulse"></span>
              )}
            </>
          ) : (
            /* 🔧 优化空内容占位符 */
            isStreaming && !isUser && (
              <div className="flex items-center gap-2 text-gray-500">
                <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                <span className="text-sm">准备回复中...</span>
              </div>
            )
          )}
        </div>

        {/* 🔧 优化流式生成统计信息 */}
        {isStreaming && !isUser && displayContent && displayContent.length > 20 && (
          <div className="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-200 flex items-center justify-between">
            <span>已生成 {displayContent.length} 字符</span>
            {isPlanContent && (
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></span>
                <span>方案内容</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RealTimeStreamingMessage;