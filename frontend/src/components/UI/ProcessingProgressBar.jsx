// src/components/UI/ProcessingProgressBar.jsx
import React, { useState, useEffect, useRef } from 'react';
import api from '../../services/api';

const ProcessingProgressBar = ({
  processingId,
  isVisible = false,
  onComplete,
  onError
}) => {
  const [progress, setProgress] = useState(0); // 目标进度（来自后端）
  const [displayProgress, setDisplayProgress] = useState(0); // 平滑显示进度
  const [status, setStatus] = useState('preparing');
  const [currentStage, setCurrentStage] = useState('准备中');
  const [message, setMessage] = useState('正在准备数据处理...');
  const [downloadUrls, setDownloadUrls] = useState(null);
  const didCompleteRef = useRef(false);
  const pollTimerRef = useRef(null);

  const statusConfig = {
    preparing: { color: 'bg-blue-500', icon: '🔄', text: '准备中' },
    downloading: { color: 'bg-yellow-500', icon: '⬇️', text: '下载中' },
    processing: { color: 'bg-purple-500', icon: '⚙️', text: '处理中' },
    completed: { color: 'bg-green-500', icon: '✅', text: '完成' },
    failed: { color: 'bg-red-500', icon: '❌', text: '失败' }
  };

  // 轮询后端真实进度
  useEffect(() => {
    if (!isVisible || !processingId) return;

    const poll = async () => {
      try {
        const { data } = await api.get(`/api/processing-progress/${processingId}`);
        if (!data) return;

        setProgress(Number(data.progress) || 0);
        setStatus(data.status || 'preparing');
        setCurrentStage(data.current_stage || '');
        setMessage(data.message || '');
        if (data.download_urls) setDownloadUrls(data.download_urls);

        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
      } catch (err) {
        if (onError) onError(err);
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };

    // 立即拉一次，再每秒轮询
    poll();
    pollTimerRef.current = setInterval(poll, 1000);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [isVisible, processingId, onError]);

  // 完成时自动下载 + 通知父组件（避免在渲染期间setState）
  useEffect(() => {
    if (status !== 'completed' || didCompleteRef.current) return;
    didCompleteRef.current = true;

    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:2025';
    const triggerDownload = (relativeUrl) => {
      if (!relativeUrl) return;
      const a = document.createElement('a');
      a.href = `${API_BASE}${relativeUrl}`;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    };

    if (downloadUrls) {
      // 先下载原始，再延迟下载处理后，避免浏览器一次性触发两次下载而拦截/丢失
      if (downloadUrls.original) {
        triggerDownload(downloadUrls.original);
      }
      if (downloadUrls.processed) {
        setTimeout(() => triggerDownload(downloadUrls.processed), 600);
      }
    }

    if (onComplete) {
      // 延迟到下一帧，避免父组件在本组件渲染过程中setState
      requestAnimationFrame(() => {
        onComplete({ status: 'completed', progress: 100, message: '数据处理已完成！', download_urls: downloadUrls });
      });
    }
  }, [status, downloadUrls, onComplete]);

  // 平滑显示进度：逐步逼近后端给的目标进度，避免突然跳跃
  useEffect(() => {
    if (!isVisible) return;
    if (status === 'completed') {
      setDisplayProgress(100);
      return;
    }
    const tick = setInterval(() => {
      setDisplayProgress(prev => {
        const delta = Math.max(0.5, (progress - prev) * 0.25);
        const next = Math.min(prev + delta, progress);
        return Math.max(0, Math.min(99, next));
      });
    }, 100);
    return () => clearInterval(tick);
  }, [isVisible, progress, status]);

  // 重置完成标志（再次显示时可以重复工作）
  useEffect(() => {
    if (!isVisible) {
      didCompleteRef.current = false;
      setProgress(0);
      setStatus('preparing');
      setCurrentStage('准备中');
      setMessage('正在准备数据处理...');
      setDownloadUrls(null);
    }
  }, [isVisible]);

  if (!isVisible) return null;
  const config = statusConfig[status] || statusConfig.preparing;

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-lg">{config.icon}</span>
          <h3 className="font-medium text-gray-900">数据处理进度</h3>
        </div>
        <div className={`px-2 py-1 text-xs font-medium text-white rounded-full ${config.color}`}>
          {config.text}
        </div>
      </div>

      <div className="p-4">
        <div className="mb-3">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{currentStage}</span>
            <span>{Math.round(status === 'completed' ? 100 : displayProgress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className={`h-2 rounded-full transition-all duration-300 ${config.color}`} style={{ width: `${status === 'completed' ? 100 : displayProgress}%` }} />
          </div>
        </div>

        <p className="text-sm text-gray-700 mb-4">{message}</p>

        {status === 'completed' && (
          <div className="bg-green-50 p-3 rounded-md">
            <p className="text-sm font-medium text-green-800">处理完成！</p>
            <p className="text-sm text-green-700 mt-1">原始与处理后的数据已开始下载。</p>
          </div>
        )}

        {status === 'failed' && (
          <div className="bg-red-50 p-3 rounded-md">
            <p className="text-sm font-medium text-red-800">处理失败</p>
            <p className="text-sm text-red-700 mt-1">请稍后重试。</p>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between p-4 border-t border-gray-200">
        <span className="text-xs text-gray-500">任务ID: {processingId?.slice(0, 8)}...</span>
      </div>
    </div>
  );
};

export default ProcessingProgressBar; 