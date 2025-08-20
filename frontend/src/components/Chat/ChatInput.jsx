// ChatInput.jsx - 更强制的边框修复方案
import React, { useState } from 'react';

const ChatInput = ({ onSendMessage, onFileUpload, disabled }) => {
  const [message, setMessage] = useState('');
  const [fileSelected, setFileSelected] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFileSelected(file);
    }
  };

  const handleFileUpload = () => {
    if (fileSelected) {
      onFileUpload(fileSelected);
      setFileSelected(null);
    }
  };

  const handleKeyDown = (e) => {
    // 按下Enter键且没有按Shift键时发送消息
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (message.trim()) {
        onSendMessage(message);
        setMessage('');
      }
    }
  };

  return (
    <div className="py-4 w-full px-4 sm:px-10">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2 w-full">
        {fileSelected && (
          <div className="flex items-center gap-2 bg-gray-50 p-3 rounded-lg border border-gray-200 w-full mx-auto">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="truncate flex-1 text-gray-700">{fileSelected.name}</span>
            <button
              type="button"
              className="px-3 py-1 bg-gray-700 text-white text-sm rounded-md hover:bg-gray-800 transition-colors"
              onClick={handleFileUpload}
            >
              上传
            </button>
            <button
              type="button"
              className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded-md hover:bg-gray-300 transition-colors"
              onClick={() => setFileSelected(null)}
            >
              取消
            </button>
          </div>
        )}

        {/* 使用更强制的边框样式 */}
        <div
          className="flex items-center gap-2 bg-white rounded-lg shadow border border-gray-300 px-4 py-2 w-full mx-auto"
          style={{ borderWidth: '1px', borderStyle: 'solid' }}
        >
          <label className="cursor-pointer text-gray-500 hover:text-gray-700 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
            </svg>
            <input
              type="file"
              className="hidden"
              onChange={handleFileChange}
              disabled={disabled}
            />
          </label>

          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息或提问..."
            className="flex-1 outline-none py-2 bg-transparent"
            disabled={disabled}
          />

          <button
            type="submit"
            className={`rounded-full p-2 transition-all ${
              message.trim() && !disabled 
                ? 'bg-gray-700 text-white hover:bg-gray-800 shadow-sm' 
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
            disabled={!message.trim() || disabled}
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>

        <div className="text-xs text-center text-gray-500 mt-1 w-full">
          按下Enter发送，Shift+Enter换行
        </div>
      </form>
    </div>
  );
};

export default ChatInput;