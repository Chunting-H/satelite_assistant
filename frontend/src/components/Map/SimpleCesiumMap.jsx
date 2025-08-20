// SimpleCesiumMap.jsx - 完整地图组件代码
import React, { useEffect, useRef, useState } from 'react';
import 'cesium/Build/Cesium/Widgets/widgets.css';

const SimpleCesiumMap = ({ location, visible }) => {
  const cesiumContainerRef = useRef(null);
  const viewerRef = useRef(null);
  const cesiumLoadedRef = useRef(false);
  const [isLoading, setIsLoading] = useState(false);

  // 使用useRef存储上一次visible状态，避免不必要的重新初始化
  const prevVisibleRef = useRef(visible);

  // 初始化Cesium
  useEffect(() => {
    // 如果可见状态没有变化，或者不可见，不执行任何操作
    if (prevVisibleRef.current === visible && !visible) return;

    // 更新上一次的可见状态
    prevVisibleRef.current = visible;

    // 如果不可见或容器不存在，不执行初始化
    if (!cesiumContainerRef.current || !visible) return;

    // 如果已经加载过并且viewer存在，不重新初始化
    if (cesiumLoadedRef.current && viewerRef.current) {
      console.log("Cesium已经加载，不重新初始化");
      return;
    }

    // 设置加载状态
    setIsLoading(true);
    console.log("开始加载Cesium...");

    // 添加一个小延迟确保DOM已经完全渲染
    const timer = setTimeout(() => {
      // 动态导入Cesium
      import('cesium').then(Cesium => {
        // 避免重复初始化
        if (viewerRef.current) {
          setIsLoading(false);
          return;
        }

        try {
          console.log("设置Cesium访问令牌...");
          Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJhYTJjNjM4Zi1hOTYxLTQxNTItODFlMS05YTEzMzU4ODk5MzIiLCJpZCI6MjAzNTE1LCJpYXQiOjE3MTEwMTAzMDV9.1zfBCCYAOJdwhmYScXFr8DhndCV2JaNhWwLBT29xZ5A';

          // 确保容器尺寸正确
          if (cesiumContainerRef.current) {
            // 创建Cesium查看器前强制设置容器样式
            cesiumContainerRef.current.style.width = '100%';
            cesiumContainerRef.current.style.height = '100%';
            cesiumContainerRef.current.style.position = 'relative';

            console.log("初始化Cesium查看器...");
            // 创建Cesium查看器
            const viewer = new Cesium.Viewer(cesiumContainerRef.current, {
              geocoder: true,
              homeButton: true,
              sceneModePicker: true,
              baseLayerPicker: true,
              navigationHelpButton: true,
              animation: false,
              timeline: false,
              // 优化性能
              requestRenderMode: true,
              maximumRenderTimeChange: Infinity
            });

            viewerRef.current = viewer;
            cesiumLoadedRef.current = true;
            console.log("Cesium加载成功");

            // 如果有位置，立即定位
            if (location) {
              const geocoder = viewer.geocoder.viewModel;
              if (geocoder) {
                geocoder.searchText = location;
                geocoder.search();
              }
            }
          }
        } catch (error) {
          console.error("Cesium初始化失败:", error);
        } finally {
          setIsLoading(false);
        }
      }).catch(error => {
        console.error("Cesium模块加载失败:", error);
        setIsLoading(false);
      });
    }, 300); // 给DOM渲染一些时间

    // 清理函数
    return () => {
      clearTimeout(timer);
      // 只有在组件卸载或visible变为false时才销毁viewer
      if (!visible && viewerRef.current) {
        console.log("销毁Cesium查看器...");
        viewerRef.current.destroy();
        viewerRef.current = null;
        cesiumLoadedRef.current = false;
      }
    };
  }, [visible]); // 只在visible变化时重新执行

  // 定位到指定地点
  useEffect(() => {
    if (!location || !viewerRef.current) return;

    console.log("在地图上定位到:", location);
    const geocoder = viewerRef.current.geocoder.viewModel;
    if (geocoder) {
      geocoder.searchText = location;
      geocoder.search();
    }
  }, [location]);

  // 如果不可见，返回null
  if (!visible) return null;

  return (
    <div className="relative w-full h-full">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-80 z-10">
          <div className="flex flex-col items-center">
            <svg className="animate-spin h-10 w-10 text-gray-500 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="text-gray-700">加载地图中...</span>
          </div>
        </div>
      )}
      <div
        ref={cesiumContainerRef}
        className="cesium-container"
        style={{ width: '100%', height: '100%', position: 'relative' }}
      ></div>
    </div>
  );
};

export default SimpleCesiumMap;