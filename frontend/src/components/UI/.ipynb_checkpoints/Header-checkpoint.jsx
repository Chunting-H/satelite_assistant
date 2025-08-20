// Header.jsx - 修改导航栏，添加卫星管理按钮
import React from 'react';

const Header = ({
  toggleMap,
  mapVisible,
  fullscreenMap,
  toggleFullscreenMap,
  onSatelliteManagement // 新增回调函数
}) => {
  return (
    <header className="bg-[#f7f7f8] text-gray-700 border-b border-gray-200">
      <div className="w-full px-4 py-3 flex justify-between items-center">
        {/* 左侧内容 - 只保留Logo */}
        <div className="flex items-center">
          {/* Logo图标 */}
          <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>

        {/* 右侧导航 */}
        <nav className="flex space-x-2">
          {/* 🆕 新增：卫星管理按钮 */}
          <button
            className="flex items-center px-3 py-1 rounded transition-colors hover:bg-gray-100 text-gray-700"
            onClick={onSatelliteManagement}
            title="卫星管理"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            </svg>
            <span className="hidden md:inline">卫星管理</span>
          </button>

          <button
            className={`flex items-center px-3 py-1 rounded transition-colors ${
              mapVisible ? 'bg-gray-200 text-gray-800' : 'hover:bg-gray-100 text-gray-700'
            }`}
            onClick={toggleMap}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <span className="hidden md:inline">{mapVisible ? '隐藏地图' : '显示地图'}</span>
          </button>

          {/* 全屏切换按钮 - 只在地图可见时显示 */}
          {mapVisible && (
            <button
              className={`flex items-center px-3 py-1 rounded transition-colors ${
                fullscreenMap ? 'bg-gray-200 text-gray-800' : 'hover:bg-gray-100 text-gray-700'
              }`}
              onClick={toggleFullscreenMap}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {fullscreenMap ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5M15 15l5.25 5.25" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
                )}
              </svg>
              <span className="hidden md:inline">{fullscreenMap ? '退出全屏' : '全屏显示'}</span>
            </button>
          )}

          <button className="hidden md:flex items-center px-3 py-1 rounded hover:bg-gray-100 transition-colors">
            <span>帮助</span>
          </button>

          <button className="hidden md:flex items-center px-3 py-1 rounded hover:bg-gray-100 transition-colors">
            <span>方案库</span>
          </button>
        </nav>
      </div>
    </header>
  );
};

export default Header;