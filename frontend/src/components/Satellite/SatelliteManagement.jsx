// components/Satellite/SatelliteManagement.jsx - 修复版本：改进过滤器合并逻辑
import React, { useState, useEffect, useMemo } from 'react';
import SatelliteFilters from './SatelliteFilters';
import SatelliteList from './SatelliteList';
import SatelliteDetail from './SatelliteDetail';
import SatelliteChat from './SatelliteChat';
import DataUpdateRecords from './DataUpdateRecords';
import { SATELLITE_DATABASE } from '../../config/satelliteDatabase';

const SatelliteManagement = ({ onBack }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSatellite, setSelectedSatellite] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showDataUpdateRecords, setShowDataUpdateRecords] = useState(false);

  // 🔧 修复：确保初始 filters 结构完整
  const defaultFilters = {
    launchDateRange: { start: '', end: '' },
    status: [],
    owner: [],
    orbitType: [],
    orbitPeriodRange: { min: '', max: '' },
    revisitRange: { min: '', max: '' },
    crossingTimeRange: { start: '', end: '' },
    orbitLongitudeRange: { min: '', max: '' },
    launchSite: [],
    endDateRange: { start: '', end: '' }
  };

  const [filters, setFilters] = useState(defaultFilters);

  // 🔧 修复：改进 onFiltersChange 函数，确保安全合并
  const handleFiltersChange = (newFiltersOrUpdater) => {
    setFilters(prevFilters => {
      let newFilters;

      if (typeof newFiltersOrUpdater === 'function') {
        // 如果是函数，执行函数获取新的 filters
        newFilters = newFiltersOrUpdater(prevFilters);
      } else {
        // 如果是对象，直接使用
        newFilters = newFiltersOrUpdater;
      }

      // 🔧 安全合并：确保所有必要的字段都存在
      const safeNewFilters = {
        ...defaultFilters, // 首先使用默认值
        ...prevFilters,    // 然后使用之前的值
        ...newFilters      // 最后应用新的值
      };

      // 🔧 验证数组字段
      const arrayFields = ['status', 'owner', 'orbitType', 'launchSite'];
      arrayFields.forEach(field => {
        if (!Array.isArray(safeNewFilters[field])) {
          safeNewFilters[field] = [];
        }
      });

      // 🔧 验证对象字段
      const objectFields = [
        'launchDateRange', 'orbitPeriodRange', 'revisitRange',
        'crossingTimeRange', 'orbitLongitudeRange', 'endDateRange'
      ];
      objectFields.forEach(field => {
        if (!safeNewFilters[field] || typeof safeNewFilters[field] !== 'object') {
          safeNewFilters[field] = field.includes('Range') && !field.includes('DateRange') && !field.includes('TimeRange')
            ? { min: '', max: '' }
            : { start: '', end: '' };
        }
      });

      console.log('🔄 更新 filters:', safeNewFilters);
      return safeNewFilters;
    });
  };

  // 处理数据库数据，添加错误处理和加载状态
  const satelliteData = useMemo(() => {
    try {
      // 检查数据库是否存在
      if (!SATELLITE_DATABASE || typeof SATELLITE_DATABASE !== 'object') {
        console.error('SATELLITE_DATABASE 未正确导入或为空');
        return [];
      }

      const entries = Object.entries(SATELLITE_DATABASE);
      if (entries.length === 0) {
        console.warn('SATELLITE_DATABASE 为空对象');
        return [];
      }

      const processedData = entries.map(([key, satellite]) => {
        // 确保 satellite 是对象
        if (!satellite || typeof satellite !== 'object') {
          console.warn(`卫星数据异常: ${key}`, satellite);
          return null;
        }

        return {
          id: key,
          ...satellite,
          // 模拟一些缺失的字段，添加默认值保护
          status: satellite.status === '在轨运行' ? 'Operational' :
                  satellite.status === '失效' ? 'Nonoperational' :
                  satellite.status || 'Unknown',
          owner: satellite.country || satellite.owner || 'Unknown',
          orbitType: satellite.orbit?.includes('太阳同步') ? 'LLEO_S' :
                     satellite.orbit?.includes('地球同步') ? 'GEO_S' :
                     'LEO_I',
          orbitPeriod: satellite.orbitParams?.orbitPeriod ?
                       (satellite.orbitParams.orbitPeriod / 60).toFixed(2) :
                       '97.4',
          revisitPeriod: satellite.revisit || 'Unknown',
          crossingTime: satellite.orbitParams?.crossingTime || 'Unknown',
          orbitLongitude: 'Unknown',
          launchSite: satellite.country === '中国' ? 'Jiuquan Space Center, PRC' :
                      satellite.country === '美国' ? 'Air Force Eastern Test Range' :
                      'Unknown',
          endDate: satellite.status !== '在轨运行' ? '2023-12-31' : null
        };
      }).filter(Boolean); // 过滤掉 null 值

      console.log(`成功处理 ${processedData.length} 颗卫星数据`);
      return processedData;
    } catch (error) {
      console.error('处理卫星数据时出错:', error);
      return [];
    }
  }, []);

  // 应用过滤器，添加防护措施
  const filteredSatellites = useMemo(() => {
    try {
      // 确保 satelliteData 是数组
      if (!Array.isArray(satelliteData)) {
        console.error('satelliteData 不是数组:', typeof satelliteData);
        return [];
      }

      return satelliteData.filter(satellite => {
        try {
          // 确保 satellite 对象存在
          if (!satellite || typeof satellite !== 'object') {
            return false;
          }

          // 搜索查询
          if (searchQuery && searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            const fullName = (satellite.fullName || '').toLowerCase();
            const englishName = (satellite.englishName || '').toLowerCase();

            if (!fullName.includes(query) && !englishName.includes(query)) {
              return false;
            }
          }

          // 🔧 修复：安全的过滤器检查
          // 运行状态过滤
          if (Array.isArray(filters.status) && filters.status.length > 0 &&
              !filters.status.includes(satellite.status)) {
            return false;
          }

          // 所有者过滤
          if (Array.isArray(filters.owner) && filters.owner.length > 0 &&
              !filters.owner.includes(satellite.owner)) {
            return false;
          }

          // 轨道类型过滤
          if (Array.isArray(filters.orbitType) && filters.orbitType.length > 0 &&
              !filters.orbitType.includes(satellite.orbitType)) {
            return false;
          }

          // 发射日期范围过滤
          if (filters.launchDateRange &&
              (filters.launchDateRange.start || filters.launchDateRange.end)) {
            const launchDate = satellite.launchDate || '';
            const launchYear = parseInt(launchDate.split('年')[0]) || 0;

            const startYear = filters.launchDateRange.start ?
              parseInt(filters.launchDateRange.start.split('-')[0]) : 0;
            const endYear = filters.launchDateRange.end ?
              parseInt(filters.launchDateRange.end.split('-')[0]) : 9999;

            if (launchYear < startYear || launchYear > endYear) {
              return false;
            }
          }

          // 轨道周期范围过滤
          if (filters.orbitPeriodRange &&
              (filters.orbitPeriodRange.min || filters.orbitPeriodRange.max)) {
            const period = parseFloat(satellite.orbitPeriod) || 0;
            const min = parseFloat(filters.orbitPeriodRange.min) || 0;
            const max = parseFloat(filters.orbitPeriodRange.max) || Infinity;

            if (period < min || period > max) {
              return false;
            }
          }

          return true;
        } catch (filterError) {
          console.error('过滤单个卫星时出错:', filterError, satellite);
          return false;
        }
      });
    } catch (error) {
      console.error('应用过滤器时出错:', error);
      return [];
    }
  }, [satelliteData, searchQuery, filters]);

  // 修复：统计信息，添加安全检查
  const statistics = useMemo(() => {
    const stats = {
      status: {},
      owner: {},
      orbitType: {},
      launchSite: {}
    };

    try {
      if (!Array.isArray(filteredSatellites)) {
        console.warn('filteredSatellites 不是数组，返回空统计');
        return stats;
      }

      filteredSatellites.forEach(satellite => {
        try {
          if (!satellite || typeof satellite !== 'object') {
            return;
          }

          // 状态统计
          const status = satellite.status || 'Unknown';
          stats.status[status] = (stats.status[status] || 0) + 1;

          // 所有者统计
          const owner = satellite.owner || 'Unknown';
          stats.owner[owner] = (stats.owner[owner] || 0) + 1;

          // 轨道类型统计
          const orbitType = satellite.orbitType || 'Unknown';
          stats.orbitType[orbitType] = (stats.orbitType[orbitType] || 0) + 1;

          // 发射地点统计
          const launchSite = satellite.launchSite || 'Unknown';
          stats.launchSite[launchSite] = (stats.launchSite[launchSite] || 0) + 1;
        } catch (statError) {
          console.error('统计单个卫星时出错:', statError, satellite);
        }
      });
    } catch (error) {
      console.error('生成统计信息时出错:', error);
    }

    return stats;
  }, [filteredSatellites]);

  // 添加：数据加载效果
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  // 添加：调试信息
  useEffect(() => {
    console.log('卫星管理组件状态:', {
      satelliteDataLength: satelliteData?.length || 0,
      filteredSatellitesLength: filteredSatellites?.length || 0,
      searchQuery,
      isLoading,
      filtersActive: Object.values(filters).some(f =>
        Array.isArray(f) ? f.length > 0 :
        typeof f === 'object' ? Object.values(f).some(v => v) :
        Boolean(f)
      )
    });
  }, [satelliteData, filteredSatellites, searchQuery, filters, isLoading]);

  const handleSatelliteSelect = (satellite) => {
    try {
      if (!satellite) {
        console.error('尝试选择空的卫星对象');
        return;
      }
      setSelectedSatellite(satellite);
      setShowDetail(true);
    } catch (error) {
      console.error('选择卫星时出错:', error);
    }
  };

  const handleBackToList = () => {
    try {
      setShowDetail(false);
      setSelectedSatellite(null);
    } catch (error) {
      console.error('返回列表时出错:', error);
    }
  };

  // 🔧 修复：改进搜索查询处理
  const handleSearchChange = (query) => {
    console.log('🔍 搜索查询更新:', query);
    setSearchQuery(query || '');
  };

  // 添加：错误边界处理
  if (!SATELLITE_DATABASE) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">数据加载失败</h2>
          <p className="text-gray-600 mb-4">无法加载卫星数据库</p>
          <button
            onClick={onBack}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            返回主页
          </button>
        </div>
      </div>
    );
  }

  // 添加：加载状态
  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500 mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">加载卫星数据中...</h2>
          <p className="text-gray-600">请稍候</p>
        </div>
      </div>
    );
  }

  // 修复：安全地获取数组长度
  const satelliteCount = Array.isArray(filteredSatellites) ? filteredSatellites.length : 0;

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* 头部 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={onBack}
              className="flex items-center text-gray-600 hover:text-gray-800 transition-colors"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              返回主页
            </button>
            <h1 className="text-2xl font-bold text-gray-900">卫星管理</h1>
            <span className="bg-blue-100 text-blue-800 text-sm font-medium px-2.5 py-0.5 rounded">
              {satelliteCount} 颗卫星
            </span>
            
            {/* 数据更新记录按钮 */}
            <button
              onClick={() => setShowDataUpdateRecords(true)}
              className="flex items-center text-gray-600 hover:text-blue-600 transition-colors bg-white border border-gray-300 px-3 py-1.5 rounded-md hover:border-blue-300"
            >
              <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              数据更新
            </button>
          </div>

          {/* 搜索框 */}
          <div className="relative w-96">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              placeholder="搜索卫星名称..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="flex-1 flex overflow-hidden">
        {!showDetail ? (
          <>
            {/* 左侧过滤条件 */}
            <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto">
              <SatelliteFilters
                filters={filters}
                onFiltersChange={handleFiltersChange}
                statistics={statistics}
              />
            </div>

            {/* 中间卫星列表 */}
            <div className="flex-1 overflow-hidden flex">
              <div className="flex-1 overflow-y-auto">
                <SatelliteList
                  satellites={filteredSatellites || []}
                  onSatelliteSelect={handleSatelliteSelect}
                  searchQuery={searchQuery}
                />
              </div>

              {/* 右侧对话框 */}
              <div className="w-80 border-l border-gray-200">
                <SatelliteChat
                  satellites={filteredSatellites || []}
                  onFiltersChange={handleFiltersChange}
                  onSearchChange={handleSearchChange}
                />
              </div>
            </div>
          </>
        ) : (
          /* 卫星详情页面 */
          <SatelliteDetail
            satellite={selectedSatellite}
            onBack={handleBackToList}
          />
        )}
      </div>
      
      {/* 数据更新记录弹窗 */}
      {showDataUpdateRecords && (
        <DataUpdateRecords 
          onClose={() => setShowDataUpdateRecords(false)}
        />
      )}
    </div>
  );
};

export default SatelliteManagement;