// 原生WebSocket实现（与FastAPI的WebSocket端点兼容）
export const connectWebSocket = (conversationId, handlers) => {
  if (!conversationId) {
    console.error('未提供对话ID，无法建立WebSocket连接');
    return null;
  }

  // 创建WebSocket连接 - 使用环境变量
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:2025';
  const wsBaseUrl = apiBaseUrl.replace('https://', 'wss://').replace('http://', 'ws://');
  const socketUrl = `${wsBaseUrl}/api/ws/${conversationId}`;
  const socket = new WebSocket(socketUrl);

  // 连接打开
  socket.onopen = () => {
    console.log('WebSocket连接已建立');
    if (handlers.onConnect) handlers.onConnect();
  };

  // 接收消息
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('收到WebSocket消息:', data);

      // 根据消息类型分发处理
      switch (data.type) {
        case 'processing_start':
          if (handlers.onProcessingStart) handlers.onProcessingStart(data);
          break;
        case 'thinking_step':
          if (handlers.onThinkingStep) handlers.onThinkingStep(data);
          break;
        case 'state_update':
          if (handlers.onStateUpdate) handlers.onStateUpdate(data);
          break;
        case 'processing_complete':
          if (handlers.onProcessingComplete) handlers.onProcessingComplete(data);
          break;
        case 'error':
          if (handlers.onError) handlers.onError(data);
          break;
        default:
          console.log('未知WebSocket消息类型:', data.type);
      }
    } catch (error) {
      console.error('解析WebSocket消息出错:', error);
    }
  };

  // 连接关闭
  socket.onclose = () => {
    console.log('WebSocket连接已关闭');
    if (handlers.onDisconnect) handlers.onDisconnect();
  };

  // 连接错误
  socket.onerror = (error) => {
    console.error('WebSocket连接出错:', error);
    if (handlers.onError) handlers.onError({ error: '连接出错' });
  };

  // 发送消息
  const sendMessage = (message) => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ message }));
    } else {
      console.error('WebSocket未连接，无法发送消息');
    }
  };

  // 关闭连接
  const disconnect = () => {
    if (socket) {
      socket.close();
    }
  };

  return {
    sendMessage,
    disconnect
  };
};

export default connectWebSocket;