// src/components/Chat/ProcessingResultViewer.jsx
import React, { useState, useRef, useCallback, useEffect } from 'react';

const ProcessingResultViewer = ({
  isVisible = false,
  originalUrl,
  processedUrl,
  onClose,
  processingId
}) => {
  const [selectedImage, setSelectedImage] = useState(null);
  const [imageScale, setImageScale] = useState(1);
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [initialScale, setInitialScale] = useState(1);

  if (!isVisible) return null;

  const handleImageClick = (imageUrl, imageType) => {
    setSelectedImage({ url: imageUrl, type: imageType });
    // 重置状态，等待图像加载后计算初始缩放
    setImageScale(1);
    setImagePosition({ x: 0, y: 0 });
    setImageDimensions({ width: 0, height: 0 });
    setInitialScale(1);
  };

  const closeFullscreen = () => {
    setSelectedImage(null);
    setImageScale(1);
    setImagePosition({ x: 0, y: 0 });
    setImageDimensions({ width: 0, height: 0 });
    setInitialScale(1);
  };

  // 计算图像初始缩放比例，确保完整显示
  const calculateInitialScale = useCallback((imgWidth, imgHeight) => {
    const screenWidth = window.innerWidth - 80; // 减去左右边距
    const screenHeight = window.innerHeight - 200; // 减去上下边距和控制栏
    
    const scaleX = screenWidth / imgWidth;
    const scaleY = screenHeight / imgHeight;
    
    // 选择较小的缩放比例，确保图像完全可见
    const initialScale = Math.min(scaleX, scaleY, 1);
    
    // 如果图像比屏幕小，则显示100%，否则按比例缩小
    return Math.max(initialScale, 0.1); // 最小缩放10%
  }, []);

  // 图像加载完成后计算初始缩放
  const handleImageLoad = useCallback((event) => {
    const img = event.target;
    const { naturalWidth, naturalHeight } = img;
    
    setImageDimensions({ width: naturalWidth, height: naturalHeight });
    
    const calculatedScale = calculateInitialScale(naturalWidth, naturalHeight);
    setInitialScale(calculatedScale);
    setImageScale(calculatedScale);
  }, [calculateInitialScale]);

  // 处理鼠标滚轮缩放
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    
    setImageScale(prev => {
      const newScale = prev * delta;
      // 限制缩放范围：10% - 1000%
      return Math.min(Math.max(newScale, 0.1), 10);
    });
  }, []);

  // 处理鼠标按下开始拖拽
  const handleMouseDown = useCallback((e) => {
    setIsDragging(true);
    setDragStart({
      x: e.clientX - imagePosition.x,
      y: e.clientY - imagePosition.y
    });
  }, [imagePosition]);

  // 处理鼠标移动拖拽
  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    const newX = e.clientX - dragStart.x;
    const newY = e.clientY - dragStart.y;
    setImagePosition({ x: newX, y: newY });
  }, [isDragging, dragStart]);

  // 处理鼠标松开结束拖拽
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // 重置图像到初始状态
  const resetImage = () => {
    setImageScale(initialScale);
    setImagePosition({ x: 0, y: 0 });
  };

  // 适应屏幕大小
  const fitToScreen = () => {
    if (imageDimensions.width && imageDimensions.height) {
      const calculatedScale = calculateInitialScale(imageDimensions.width, imageDimensions.height);
      setImageScale(calculatedScale);
      setImagePosition({ x: 0, y: 0 });
    }
  };

  // 适应图像宽度
  const fitToWidth = () => {
    if (imageDimensions.width) {
      const screenWidth = window.innerWidth - 80;
      const scale = screenWidth / imageDimensions.width;
      setImageScale(Math.max(scale, 0.1));
      setImagePosition({ x: 0, y: 0 });
    }
  };

  // 适应图像高度
  const fitToHeight = () => {
    if (imageDimensions.height) {
      const screenHeight = window.innerHeight - 200;
      const scale = screenHeight / imageDimensions.height;
      setImageScale(Math.max(scale, 0.1));
      setImagePosition({ x: 0, y: 0 });
    }
  };

  return (
    <>
      <div className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 rounded-xl p-6 mb-4 border border-blue-200 shadow-lg">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex-1">
            <h3 className="text-xl font-bold text-gray-800 mb-2">🔍 处理结果对比</h3>
            <p className="text-sm text-gray-600 mb-1">原始图像 vs 处理后图像（任务ID: {processingId?.slice(0,8)}...）</p>
            <p className="text-xs text-gray-500">💡 点击图像查看大图，支持缩放和拖拽</p>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg hover:from-blue-600 hover:to-indigo-700 transition-all duration-200 shadow-md hover:shadow-lg"
          >
            关闭
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 原始图像 */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden hover:shadow-xl transition-all duration-300">
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-4 py-3">
              <span className="text-white font-semibold text-sm">📸 原始图像</span>
            </div>
            <div className="p-4">
              {originalUrl ? (
                <div 
                  className="group cursor-pointer transform hover:scale-105 transition-all duration-300"
                  onClick={() => handleImageClick(originalUrl, '原始图像')}
                >
                  <div className="relative overflow-hidden rounded-lg border-2 border-gray-200 group-hover:border-blue-300 transition-colors duration-200">
                    <img 
                      src={originalUrl} 
                      alt="原始图像" 
                      className="w-full h-auto object-cover transition-transform duration-300"
                      style={{ height: '280px' }}
                    />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all duration-300 flex items-center justify-center">
                      <div className="bg-white bg-opacity-90 rounded-full p-3 transform scale-0 group-hover:scale-100 transition-transform duration-300">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                        </svg>
                      </div>
                    </div>
                  </div>
                  <p className="text-center text-xs text-gray-500 mt-2">点击查看大图</p>
                </div>
              ) : (
                <div className="h-48 flex items-center justify-center text-gray-500 text-sm border-2 border-dashed border-gray-300 rounded-lg">
                  <div className="text-center">
                    <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p>原始图像不可用</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 处理后图像 */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden hover:shadow-xl transition-all duration-300">
            <div className="bg-gradient-to-r from-green-500 to-green-600 px-4 py-3">
              <span className="text-white font-semibold text-sm">✨ 处理后图像</span>
            </div>
            <div className="p-4">
              {processedUrl ? (
                <div 
                  className="group cursor-pointer transform hover:scale-105 transition-all duration-300"
                  onClick={() => handleImageClick(processedUrl, '处理后图像')}
                >
                  <div className="relative overflow-hidden rounded-lg border-2 border-gray-200 group-hover:border-green-300 transition-colors duration-200">
                    <img 
                      src={processedUrl} 
                      alt="处理后图像" 
                      className="w-full h-auto object-cover transition-transform duration-300"
                      style={{ height: '280px' }}
                    />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all duration-300 flex items-center justify-center">
                      <div className="bg-white bg-opacity-90 rounded-full p-3 transform scale-0 group-hover:scale-100 transition-transform duration-300">
                        <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                        </svg>
                      </div>
                    </div>
                  </div>
                  <p className="text-center text-xs text-gray-500 mt-2">点击查看大图</p>
                </div>
              ) : (
                <div className="h-48 flex items-center justify-center text-gray-500 text-sm border-2 border-dashed border-gray-300 rounded-lg">
                  <div className="text-center">
                    <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p>处理后图像不可用</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 全屏图像查看器 */}
      {selectedImage && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-95 z-50 flex items-center justify-center p-4"
          onWheel={handleWheel}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <div className="relative w-full h-full flex items-center justify-center">
            {/* 顶部控制栏 */}
            <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 flex items-center gap-4 bg-black bg-opacity-50 text-white px-6 py-3 rounded-full backdrop-blur-sm">
              <span className="text-sm font-medium">{selectedImage.type}</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setImageScale(prev => Math.max(prev * 0.9, 0.1))}
                  className="w-8 h-8 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full flex items-center justify-center transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                  </svg>
                </button>
                <span className="text-xs min-w-[3rem] text-center">{(imageScale * 100).toFixed(0)}%</span>
                <button
                  onClick={() => setImageScale(prev => Math.min(prev * 1.1, 10))}
                  className="w-8 h-8 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full flex items-center justify-center transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={fitToScreen}
                  className="px-2 py-1 text-xs bg-white bg-opacity-20 hover:bg-opacity-30 rounded transition-all"
                  title="适应屏幕"
                >
                  适应
                </button>
                <button
                  onClick={fitToWidth}
                  className="px-2 py-1 text-xs bg-white bg-opacity-20 hover:bg-opacity-30 rounded transition-all"
                  title="适应宽度"
                >
                  宽度
                </button>
                <button
                  onClick={fitToHeight}
                  className="px-2 py-1 text-xs bg-white bg-opacity-20 hover:bg-opacity-30 rounded transition-all"
                  title="适应高度"
                >
                  高度
                </button>
                <button
                  onClick={resetImage}
                  className="px-2 py-1 text-xs bg-white bg-opacity-20 hover:bg-opacity-30 rounded transition-all"
                  title="重置到初始大小"
                >
                  重置
                </button>
              </div>
            </div>

            {/* 关闭按钮 */}
            <button
              onClick={closeFullscreen}
              className="absolute top-4 right-4 z-10 bg-white bg-opacity-20 hover:bg-opacity-30 text-white rounded-full w-12 h-12 flex items-center justify-center transition-all hover:bg-opacity-40"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            {/* 图像容器 */}
            <div 
              className="cursor-move select-none"
              onMouseDown={handleMouseDown}
            >
              <img 
                src={selectedImage.url} 
                alt={selectedImage.type}
                className="transition-transform duration-100"
                style={{
                  transform: `scale(${imageScale}) translate(${imagePosition.x}px, ${imagePosition.y}px)`,
                  transformOrigin: 'center',
                  cursor: isDragging ? 'grabbing' : 'grab'
                }}
                draggable={false}
                onLoad={handleImageLoad}
              />
            </div>

            {/* 底部提示 */}
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10 bg-black bg-opacity-50 text-white px-4 py-2 rounded-full text-xs backdrop-blur-sm">
              滚轮缩放 • 拖拽移动 • 适应屏幕 • ESC关闭
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ProcessingResultViewer;
