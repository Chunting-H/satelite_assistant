// api.js
import axios from 'axios';

// 后端API地址 - 使用环境变量，如果没有则使用默认值
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:2025';

// 创建axios实例
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60秒超时
});

// 添加请求拦截器 - 记录请求
api.interceptors.request.use(
  (config) => {
    console.log(`API请求: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API请求配置错误:', error);
    return Promise.reject(error);
  }
);

// 添加响应拦截器 - 处理undefined响应和记录响应
api.interceptors.response.use(
  (response) => {
    console.log(`API响应成功: ${response.config.url}`, response.status);
    
    // 检查是否收到ngrok警告页面
    if (typeof response.data === 'string' && response.data.includes('<!DOCTYPE html>')) {
      console.warn('收到ngrok警告页面，需要手动确认访问');
      return {
        ...response,
        data: {
          conversations: [],
          total: 0,
          error: 'ngrok_warning',
          message: '请先在浏览器中访问后端API地址确认访问权限'
        }
      };
    }
    
    return response;
  },
  (error) => {
    // 如果后端返回 undefined，构造一个有效的响应
    if (error.message === 'Network Error' || error.code === 'ERR_NETWORK') {
      console.error('网络错误，无法连接到服务器');
      // 构造默认响应对象
      return Promise.resolve({
        data: {
          conversations: [],
          total: 0,
          error: 'network_error'
        }
      });
    }

    // 处理超时错误
    if (error.code === 'ECONNABORTED') {
      console.error('请求超时，服务器响应时间过长');
      return Promise.resolve({
        data: {
          conversations: [],
          total: 0,
          error: 'timeout_error'
        }
      });
    }

    // 处理其他错误
    console.error(`API响应错误: ${error.config?.url}`, error.message);
    return Promise.reject(error);
  }
);

// 发送消息
export const sendMessage = async (message, conversationId = null, location = null) => {
  try {
    const payload = {
      message,
      conversation_id: conversationId,
      location: location // 🆕 添加位置信息
    };
    const response = await api.post('/api/conversation', payload);

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    return response.data;
  } catch (error) {
    console.error('发送消息错误:', error);
    return {
      error: true,
      message: error.message || '发送消息失败',
      conversation_id: conversationId
    };
  }
};
export const renameConversation = async (conversationId, newTitle) => {
  try {
    // 修复1：使用 API_URL 而不是 API_BASE_URL
    const response = await api.patch(`/api/conversation/${conversationId}/rename`, {
      title: newTitle
    });

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    return response.data;
  } catch (error) {
    console.error('重命名对话失败:', error);
    throw error;
  }
};
// 获取对话详情
export const getConversation = async (conversationId) => {
  if (!conversationId) {
    console.error('获取对话详情错误: 未提供conversationId');
    return null;
  }

  try {
    const response = await api.get(`/api/conversation/${conversationId}`);

    if (!response.data) {
      console.warn(`对话 ${conversationId} 返回了空数据`);
      return {
        conversation_id: conversationId,
        message: "",
        metadata: { messages: [] }
      };
    }

    return response.data;
  } catch (error) {
    console.error(`获取对话 ${conversationId} 详情错误:`, error);
    return {
      conversation_id: conversationId,
      message: "无法加载对话内容",
      metadata: { messages: [] }
    };
  }
};

// 获取对话列表
export const listConversations = async () => {
  try {
    const response = await api.get('/api/conversations');

    // 检查是否收到ngrok警告页面
    if (typeof response.data === 'string' && response.data.includes('<!DOCTYPE html>')) {
      console.warn('收到ngrok警告页面，需要手动确认访问');
      return { 
        conversations: [], 
        total: 0,
        error: 'ngrok_warning',
        message: '请先在浏览器中访问后端API地址确认访问权限'
      };
    }

    if (response.data === undefined || response.data === null) {
      console.warn('API返回了undefined或null数据');
      return { conversations: [], total: 0 };
    }

    if (!response.data.conversations) {
      console.warn('API返回数据中没有conversations字段');
      response.data.conversations = [];
    }

    if (typeof response.data.total !== 'number') {
      console.warn('API返回数据中没有有效的total字段');
      response.data.total = response.data.conversations?.length || 0;
    }

    return response.data;
  } catch (error) {
    console.error('获取对话列表错误:', error);
    return { conversations: [], total: 0 };
  }
};

// 删除对话
export const deleteConversation = async (conversationId) => {
  if (!conversationId) {
    console.error('删除对话失败: 未提供会话ID');
    throw new Error('未提供会话ID');
  }

  try {
    console.log(`删除对话: ${conversationId}`);
    const response = await api.delete(`/api/conversation/${conversationId}`);
    console.log('删除对话响应:', response.data);
    return response.data;
  } catch (error) {
    console.error('删除对话失败:', error);
    throw error;
  }
};

// 新增：创建新对话
export const createConversation = async (conversationId, title = '新对话') => {
  if (!conversationId) {
    console.error('创建对话失败: 未提供会话ID');
    throw new Error('未提供会话ID');
  }

  try {
    console.log(`创建新对话: ${conversationId}, 标题: ${title}`);
    
    // 使用新的API端点创建空对话
    const response = await api.post('/api/conversation/create', conversationId);

    console.log('创建对话响应:', response.data);
    
    // 构造对话列表项格式
    const conversationItem = {
      conversation_id: conversationId,
      title: title,
      created_at: Date.now() / 1000,
      updated_at: Date.now() / 1000,
      message_count: 0 // 空对话，没有消息
    };
    
    return conversationItem;
  } catch (error) {
    console.error('创建对话失败:', error);
    throw error;
  }
};

// 上传文件
export const uploadFile = async (file, conversationId = null) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }

    const response = await api.post('/api/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  } catch (error) {
    console.error('上传文件出错:', error);
    throw error;
  }
};

// 获取星座方案详情
export const getPlan = async (planId) => {
  try {
    const response = await api.get(`/api/plans/${planId}`);
    return response.data;
  } catch (error) {
    console.error(`获取方案 ${planId} 详情出错:`, error);
    throw error;
  }
};

// 获取系统健康状态
export const getHealth = async () => {
  try {
    const response = await api.get('/api/health');
    return response.data;
  } catch (error) {
    console.error('获取健康状态出错:', error);
    return { status: 'error', error: error.message };
  }
};


// 智能卫星查询
export const querySatellites = async (query, model = 'chatgpt', satellitesContext = '') => {
  try {
    const payload = {
      query: query,
      model: model,
      satellites_context: satellitesContext
    };
    
    console.log('🤖 发送卫星查询请求:', { query: query.substring(0, 50), model });
    
    const response = await api.post('/api/satellite/query', payload);

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    console.log('✅ 卫星查询成功:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ 卫星查询失败:', error);
    return {
      success: false,
      answer: `查询失败: ${error.message || '未知错误'}`,
      filters: {},
      search_query: '',
      model_used: model,
      error_message: error.message || '未知错误'
    };
  }
};

// ===== 爬虫智能体API =====

// 启动爬取任务
export const startCrawlJob = async (targetSites = ["Gunter's Space Page"], keywords = [], maxSatellites = 10) => {
  try {
    const payload = {
      target_sites: targetSites,
      keywords: keywords,
      max_satellites: maxSatellites
    };
    
    console.log('🚀 启动爬取任务:', payload);
    
    const response = await api.post('/api/crawl/start', payload);

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    console.log('✅ 爬取任务启动成功:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ 启动爬取任务失败:', error);
    return {
      success: false,
      error: error.message || '启动爬取任务失败'
    };
  }
};

// 获取爬取任务状态
export const getCrawlJobStatus = async (jobId) => {
  try {
    const response = await api.get(`/api/crawl/status/${jobId}`);

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    return response.data;
  } catch (error) {
    console.error(`获取爬取任务状态失败 ${jobId}:`, error);
    return {
      error: error.message || '获取任务状态失败'
    };
  }
};

// 获取爬取任务列表
export const getCrawlJobs = async (status = null, limit = 20) => {
  try {
    const params = { limit };
    if (status) {
      params.status = status;
    }
    
    const response = await api.get('/api/crawl/jobs', { params });

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    return response.data;
  } catch (error) {
    console.error('获取爬取任务列表失败:', error);
    return {
      jobs: [],
      total: 0,
      error: error.message || '获取任务列表失败'
    };
  }
};

// 获取爬取日志
export const getCrawlLogs = async (limit = 50) => {
  try {
    const response = await api.get('/api/crawl/logs', {
      params: { limit }
    });

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    return response.data;
  } catch (error) {
    console.error('获取爬取日志失败:', error);
    return {
      logs: [],
      total: 0,
      error: error.message || '获取爬取日志失败'
    };
  }
};

// 获取爬取统计信息
export const getCrawlStatistics = async (days = 30) => {
  try {
    const response = await api.get('/api/crawl/statistics', {
      params: { days }
    });

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    return response.data;
  } catch (error) {
    console.error('获取爬取统计失败:', error);
    return {
      total_crawls: 0,
      total_new_satellites: 0,
      total_failed: 0,
      daily_stats: [],
      site_stats: [],
      recent_logs: [],
      error: error.message || '获取爬取统计失败'
    };
  }
};

// 手动触发爬取
export const manualCrawl = async (targetSites = ["Gunter's Space Page"], keywords = [], maxSatellites = 10) => {
  try {
    const payload = {
      target_sites: targetSites,
      keywords: keywords,
      max_satellites: maxSatellites
    };
    
    console.log('🔧 手动爬取请求:', payload);
    
    const response = await api.post('/api/crawl/manual', payload);

    if (!response.data) {
      throw new Error('API返回了空响应');
    }

    console.log('✅ 手动爬取启动成功:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ 手动爬取失败:', error);
    return {
      success: false,
      error: error.message || '手动爬取失败'
    };
  }
};

export default api;