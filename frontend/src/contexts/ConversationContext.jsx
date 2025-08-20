// ConversationContext.jsx 修复版
import { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import { listConversations, getConversation } from '../services/api';

// 创建上下文
const ConversationContext = createContext();

// 自定义Hook，方便使用上下文
export const useConversation = () => useContext(ConversationContext);

// 上下文提供者组件
export const ConversationProvider = ({ children }) => {
  const [currentConversation, setCurrentConversation] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastFetchTime, setLastFetchTime] = useState(0);
  const isInitialMount = useRef(true);

  // 使用useCallback包装fetchConversations以避免重复创建
  const fetchConversations = useCallback(async (force = false) => {
    // 添加截流，避免频繁调用
    const now = Date.now();
    if (!force && now - lastFetchTime < 5000) {
      console.log("截流：5秒内已经获取过会话列表，跳过请求");
      return;
    }

    try {
      // 避免重复设置loading状态
      if (!loading) {
        setLoading(true);
      }

      console.log("正在获取会话列表...", force ? "(强制更新)" : "");
      const data = await listConversations();
      console.log("获取到的会话列表:", data);

      if (data && Array.isArray(data.conversations)) {
        setConversations(data.conversations);
        console.log(`成功获取 ${data.conversations.length} 个会话`);
      } else {
        console.error('获取对话列表失败: 响应格式不正确', data);
        setConversations([]);
      }

      setLastFetchTime(now);
    } catch (error) {
      console.error('获取对话列表失败:', error);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  }, [lastFetchTime, loading]);

  // 获取特定对话的消息历史
  const fetchConversationMessages = useCallback(async (conversationId) => {
    if (!conversationId) {
      console.log('没有提供对话ID，跳过获取消息');
      return;
    }

    try {
      setLoading(true);
      console.log(`获取对话 ${conversationId} 的消息历史...`);

      const response = await getConversation(conversationId);
      console.log('获取到对话详情响应:', response);

      // 调试响应数据
      if (response) {
        console.log('metadata:', response.metadata);
        if (response.metadata && response.metadata.messages) {
          console.log('metadata.messages:', response.metadata.messages.length);
        }
      }

      // 首先尝试从metadata.messages获取消息数组
      if (response && response.metadata && Array.isArray(response.metadata.messages)) {
        const formattedMessages = response.metadata.messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp * 1000 // 确保时间戳是毫秒格式
        }));

        console.log(`成功获取 ${formattedMessages.length} 条消息(从metadata)`, formattedMessages);
        setMessages(formattedMessages);
        return formattedMessages;
      }
      // 尝试直接结构化响应创建消息
      else if (response) {
        // 如果有消息且不是用户的第一条消息，创建对话记录
        if (response.message) {
          // 创建包含用户消息和助手回复的数组
          const userMessage = {
            role: 'user',
            content: '用户问题', // 这里可能需要从后端获取真实的用户问题
            timestamp: Date.now() - 1000 // 比助手回复早一秒
          };

          const assistantMessage = {
            role: 'assistant',
            content: response.message,
            timestamp: Date.now()
          };

          const newMessages = [userMessage, assistantMessage];
          console.log('创建对话消息:', newMessages);
          setMessages(newMessages);
          return newMessages;
        } else {
          console.warn('响应中没有消息内容');
          setMessages([]);
          return [];
        }
      }
      // 如果都没有找到，清空消息列表并记录错误
      else {
        console.error('获取对话消息失败: 响应中没有找到messages字段', response);
        setMessages([]);
        return [];
      }
    } catch (error) {
      console.error('获取对话消息失败:', error);
      setMessages([]);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始化时获取对话列表，确保只执行一次
  useEffect(() => {
    if (isInitialMount.current) {
      console.log("ConversationContext首次挂载，获取会话列表");
      fetchConversations(true);
      isInitialMount.current = false;
    }
  }, [fetchConversations]);

  // 提供的上下文值
  const value = {
    currentConversation,
    setCurrentConversation,
    conversations,
    setConversations,
    messages,
    setMessages,
    fetchConversations,
    fetchConversationMessages,
    loading
  };

  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
};

export default ConversationContext;