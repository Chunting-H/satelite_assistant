// components/Satellite/SatelliteDetail.jsx - 修复版本：解决3D地球底部控制组件显示问题
import React, { useState, useRef, useEffect } from 'react';
import EnhancedCesiumMap from '../Map/EnhancedCesiumMap';

const SatelliteDetail = ({ satellite, onBack }) => {
  const [activeTab, setActiveTab] = useState('basic');
  const [showOrbitMap, setShowOrbitMap] = useState(true);
  const [mapKey, setMapKey] = useState(0);
  const mapContainerRef = useRef(null);
  const [containerHeight, setContainerHeight] = useState('100vh');

  // 🔧 新增：动态计算容器高度
  useEffect(() => {
    const calculateHeight = () => {
      // 获取顶部信息面板的高度
      const infoPanel = document.querySelector('[data-info-panel]');
      if (infoPanel) {
        const infoPanelHeight = infoPanel.offsetHeight;
        const newHeight = `calc(100vh - ${infoPanelHeight}px)`;
        setContainerHeight(newHeight);
      }
    };

    // 初始计算
    calculateHeight();

    // 监听窗口大小变化
    const handleResize = () => {
      calculateHeight();
      // 同时触发地图重新渲染
      setMapKey(prev => prev + 1);
    };

    window.addEventListener('resize', handleResize);

    // 延迟计算，确保DOM已完全渲染
    const timer = setTimeout(calculateHeight, 100);

    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timer);
    };
  }, [showOrbitMap]);

  if (!satellite) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">🛰️</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">未选择卫星</h3>
          <p className="text-gray-500">请从列表中选择一颗卫星查看详情</p>
        </div>
      </div>
    );
  }

  const handleToggleOrbitMap = () => {
    setShowOrbitMap(!showOrbitMap);
    setMapKey(prev => prev + 1);
  };

  // 监听容器大小变化，确保地图正确渲染
  useEffect(() => {
    if (!mapContainerRef.current || !showOrbitMap) return;

    const resizeObserver = new ResizeObserver(() => {
      // 触发地图重新渲染
      setTimeout(() => {
        setMapKey(prev => prev + 1);
      }, 100);
    });

    resizeObserver.observe(mapContainerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [showOrbitMap]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'Operational':
        return 'bg-green-100 text-green-800';
      case 'Nonoperational':
        return 'bg-red-100 text-red-800';
      case 'Decayed':
        return 'bg-gray-100 text-gray-800';
      case 'Unknown':
        return 'bg-yellow-100 text-yellow-800';
      case 'Partially Operational':
        return 'bg-orange-100 text-orange-800';
      case 'Extended Mission':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const InfoRow = ({ label, value, className = "" }) => (
    <tr className={className}>
      <td className="px-4 py-3 text-sm font-medium text-gray-900 bg-gray-50 border-b border-gray-200">
        {label}
      </td>
      <td className="px-4 py-3 text-sm text-gray-700 border-b border-gray-200">
        {value || '未知'}
      </td>
    </tr>
  );

  // 标签页内容组件
  const BasicInfoTab = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <tbody className="bg-white divide-y divide-gray-200">
          <InfoRow label="卫星名称" value={satellite.fullName} />
          <InfoRow label="英文名称" value={satellite.englishName} />
          <InfoRow label="别称" value={satellite.aliases?.join('，') || '无'} />
          <InfoRow label="COSPAR ID" value={satellite.cosparId || '2018-046A'} />
          <InfoRow label="NORAD ID" value={satellite.noradId || '43474'} />
          <InfoRow label="发射日期" value={satellite.launchDate} />
          <InfoRow label="终止日期" value={satellite.endDate || '在轨运行中'} />
          <InfoRow label="所有者" value={satellite.country || satellite.owner} />
          <InfoRow label="卫星机构" value={satellite.agencies?.join(',') || 'NASA,CSA,DLR,ESA,JAXA,Roscosmos'} />
          <InfoRow label="发射地点" value={satellite.launchSite || 'Wallops Island, Virginia, USA'} />
          <InfoRow
            label="运行状态"
            value={
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(satellite.status)}`}>
                {satellite.status || 'Unknown'}
              </span>
            }
          />
          <InfoRow label="卫星类型" value={satellite.type || '地球观测'} />
          <InfoRow label="任务描述" value={satellite.description} />
        </tbody>
      </table>
    </div>
  );

  const OrbitInfoTab = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <tbody className="bg-white divide-y divide-gray-200">
          <InfoRow label="轨道类型" value={satellite.orbitType || 'LLEO_I (Lower LEO/Intermediate)'} />
          <InfoRow label="轨道周期 (分钟)" value={satellite.orbitPeriod || '92.47'} />
          <InfoRow label="轨道高度 (km)" value={satellite.orbitHeight || '400'} />
          <InfoRow label="远地点高度 (km)" value={satellite.apogeeHeight || '410'} />
          <InfoRow label="近地点高度 (km)" value={satellite.perigeeHeight || '381'} />
          <InfoRow label="倾角 (°)" value={satellite.inclination || '51.64'} />
          <InfoRow label="轨道经度" value={satellite.orbitLongitude || '不适用'} />
          <InfoRow label="赤道过境时间" value={satellite.crossingTime || '不适用'} />
          <InfoRow label="重复周期 (天)" value={satellite.revisitPeriod || satellite.revisit || '不适用'} />
          <InfoRow label="轨道偏心率" value={satellite.eccentricity || '未知'} />
          <InfoRow label="升交点赤经 (°)" value={satellite.raan || '未知'} />
          <InfoRow label="近地点幅角 (°)" value={satellite.argumentOfPerigee || '未知'} />
        </tbody>
      </table>
    </div>
  );

  const TechnicalSpecsTab = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <tbody className="bg-white divide-y divide-gray-200">
          <InfoRow label="发射质量 (kg)" value={satellite.launchMass || '7200'} />
          <InfoRow label="干质量 (kg)" value={satellite.dryMass || '2000'} />
          <InfoRow label="功率 (W)" value={satellite.power || '未知'} />
          <InfoRow label="设计寿命" value={satellite.designLife || '未知'} />
          <InfoRow label="制造商" value={satellite.manufacturer || '未知'} />
          <InfoRow label="平台类型" value={satellite.platform || '未知'} />
          <InfoRow label="稳定方式" value={satellite.stabilization || '三轴稳定'} />
          <InfoRow label="推进系统" value={satellite.propulsion || '未知'} />
          <InfoRow label="通信频段" value={satellite.communicationBands || 'S波段, X波段'} />
          <InfoRow label="数据传输速率" value={satellite.dataRate || '未知'} />
          <InfoRow label="存储容量" value={satellite.storageCapacity || '未知'} />
        </tbody>
      </table>
    </div>
  );

  const PayloadInfoTab = () => (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <tbody className="bg-white divide-y divide-gray-200">
            <InfoRow label="主要载荷" value="MM Radiometer（Millimetre-wave Radiometer）" />
            <InfoRow label="载荷类型" value="地球观测载荷" />
            <InfoRow label="观测光谱" value={satellite.spectralBands?.join(', ') || '毫米波'} />
            <InfoRow label="空间分辨率" value={satellite.spatialResolution || '未知'} />
            <InfoRow label="光谱分辨率" value={satellite.spectralResolution || '未知'} />
            <InfoRow label="时间分辨率" value={satellite.temporalResolution || satellite.revisit || '未知'} />
            <InfoRow label="观测幅宽" value={satellite.swathWidth || '未知'} />
            <InfoRow label="观测模式" value={satellite.observationModes || '推扫成像'} />
          </tbody>
        </table>
      </div>

      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-2">载荷详细信息</h4>
        <p className="text-sm text-gray-700">
          MM Radiometer (Millimetre-wave Radiometer) 是一个毫米波辐射计，用于观测地球大气中的水汽、云层和降水情况。
          该载荷能够提供高精度的大气参数测量，支持天气预报和气候研究。
        </p>
      </div>
    </div>
  );

  const ApplicationDataTab = () => (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <tbody className="bg-white divide-y divide-gray-200">
            <InfoRow label="主要应用" value="气象观测、大气研究" />
            <InfoRow label="数据级别" value="L0, L1A, L1B, L2" />
            <InfoRow label="数据格式" value="HDF5, NetCDF" />
            <InfoRow label="数据覆盖" value="全球" />
            <InfoRow label="数据更新频率" value="实时" />
            <InfoRow label="数据延迟" value="< 3小时" />
            <InfoRow label="存档状态" value="长期存档" />
          </tbody>
        </table>
      </div>

      <div className="bg-blue-50 p-4 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-2">OSCAR 描述</h4>
        <p className="text-sm text-gray-700">
          Spacecraft engaged in practical applications and uses of space technology such as weather or communications.
          This satellite provides critical atmospheric and meteorological data for weather forecasting and climate monitoring.
        </p>
      </div>

      <div className="bg-green-50 p-4 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-2">相关网站信息</h4>
        <div className="space-y-2 text-sm">
          <div>
            <span className="font-medium">eoPortal: </span>
            <a href="#" className="text-blue-600 hover:text-blue-800">
              https://eoportal.org/web/eoportal/satellite-missions
            </a>
          </div>
          <div>
            <span className="font-medium">NASA官网: </span>
            <a href="#" className="text-blue-600 hover:text-blue-800">
              https://www.nasa.gov/mission_pages/station/research/tempest-d
            </a>
          </div>
        </div>
      </div>

      <div className="bg-yellow-50 p-4 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-2">数据访问</h4>
        <div className="space-y-2 text-sm">
          <div>
            <span className="font-medium">数据门户: </span>
            <a href="#" className="text-blue-600 hover:text-blue-800">
              NASA Goddard Earth Sciences Data and Information Services Center
            </a>
          </div>
          <div>
            <span className="font-medium">FTP服务: </span>
            <span className="text-gray-700">ftp://data.gov/satellite/tempest-d/</span>
          </div>
          <div>
            <span className="font-medium">API接口: </span>
            <span className="text-gray-700">支持REST API访问</span>
          </div>
        </div>
      </div>
    </div>
  );

  const tabs = [
    { id: 'basic', label: '基本信息', component: BasicInfoTab },
    { id: 'orbit', label: '轨道信息', component: OrbitInfoTab },
    { id: 'technical', label: '技术规格', component: TechnicalSpecsTab },
    { id: 'payload', label: '载荷信息', component: PayloadInfoTab },
    { id: 'application', label: '应用与数据', component: ApplicationDataTab },
  ];

  return (
    <div className="h-screen w-full flex bg-white overflow-hidden">
      {/* 左侧详情信息 - 固定占据 50% 宽度 */}
      <div className="w-1/2 flex flex-col border-r border-gray-200 overflow-hidden">
        {/* 头部 */}
        <div className="flex-shrink-0 p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="flex items-center text-gray-600 hover:text-gray-800 transition-colors"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                返回列表
              </button>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleToggleOrbitMap}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  showOrbitMap 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {showOrbitMap ? '隐藏轨道' : '显示轨道'}
              </button>
              <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                下载数据
              </button>
              <button className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors">
                添加到收藏
              </button>
            </div>
          </div>

          <div className="mt-4">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{satellite.fullName}</h1>
                {satellite.englishName && (
                  <p className="text-lg text-gray-600 mt-1">{satellite.englishName}</p>
                )}
                <div className="flex items-center space-x-4 mt-2">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(satellite.status)}`}>
                    {satellite.status || 'Unknown'}
                  </span>
                  <span className="text-sm text-gray-500">
                    {satellite.country || satellite.owner}
                  </span>
                  <span className="text-sm text-gray-500">
                    发射于 {satellite.launchDate}
                  </span>
                </div>
              </div>

              <div className="text-right">
                <div className="text-6xl">🛰️</div>
              </div>
            </div>
          </div>
        </div>

        {/* 标签导航 */}
        <div className="flex-shrink-0 border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* 标签内容 - 可滚动区域 */}
        <div className="flex-1 overflow-y-auto p-6">
          {tabs.find(tab => tab.id === activeTab)?.component()}
        </div>
      </div>

      {/* 右侧 3D 轨道显示 - 固定占据 50% 宽度 */}
      <div className="w-1/2 flex flex-col bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 overflow-hidden">
        {/* 🔧 轨道信息面板 - 添加 data-info-panel 标识 */}
        <div
          className="flex-shrink-0 p-4 bg-black bg-opacity-30"
          data-info-panel
        >
          <div className="bg-white bg-opacity-90 rounded-lg p-4 shadow-md">
            <div className="grid grid-cols-1 gap-4">
              {/* 第一行：卫星名称和状态 */}
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-gray-900">{satellite.fullName}</h3>
                <div className="flex items-center space-x-2">
                  {satellite.status === '在轨运行' || satellite.status === 'Operational' ? (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                      <div className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></div>
                      在轨运行
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
                      <div className="w-2 h-2 bg-gray-400 rounded-full mr-2"></div>
                      {satellite.status}
                    </span>
                  )}
                </div>
              </div>

              {/* 第二行：轨道参数网格 */}
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div className="bg-white bg-opacity-60 rounded-md p-3">
                  <span className="text-gray-600 block font-medium">轨道高度</span>
                  <span className="text-gray-900 font-bold text-base">
                    {satellite.altitude || '400-800km'}
                  </span>
                </div>
                <div className="bg-white bg-opacity-60 rounded-md p-3">
                  <span className="text-gray-600 block font-medium">轨道周期</span>
                  <span className="text-gray-900 font-bold text-base">
                    {satellite.orbitParams?.orbitPeriod ?
                      `${(satellite.orbitParams.orbitPeriod / 60).toFixed(1)}分钟` :
                      '90-120分钟'
                    }
                  </span>
                </div>
                <div className="bg-white bg-opacity-60 rounded-md p-3">
                  <span className="text-gray-600 block font-medium">轨道倾角</span>
                  <span className="text-gray-900 font-bold text-base">
                    {satellite.orbitParams?.inclination || satellite.inclination || '约98°'}
                  </span>
                </div>
                <div className="bg-white bg-opacity-60 rounded-md p-3">
                  <span className="text-gray-600 block font-medium">轨道类型</span>
                  <span className="text-gray-900 font-bold text-base">
                    {satellite.orbit || 'LEO'}
                  </span>
                </div>
              </div>

              {/* 第三行：控制按钮 */}
              <div className="flex gap-3">
                <button className="flex-1 bg-blue-500 text-white text-sm px-4 py-2 rounded-md hover:bg-blue-600 transition-colors font-medium">
                  跟踪卫星
                </button>
                <button className="flex-1 bg-gray-500 text-white text-sm px-4 py-2 rounded-md hover:bg-gray-600 transition-colors font-medium">
                  重置视角
                </button>
                <button className="flex-1 bg-green-500 text-white text-sm px-4 py-2 rounded-md hover:bg-green-600 transition-colors font-medium">
                  模拟轨道
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 🔧 3D地图容器 - 使用动态高度并确保显示完整 */}
        <div
          ref={mapContainerRef}
          className="flex-1 relative min-h-0"
          style={{
            height: containerHeight === '100vh' ? 'calc(100vh - 200px)' : containerHeight,
            minHeight: '400px' // 确保最小高度
          }}
        >
          {showOrbitMap ? (
            <div
              className="absolute inset-0 w-full h-full"
              style={{
                // 🔧 确保 Cesium 控制器完全可见
                paddingBottom: '70px' // 为底部控制器预留空间
              }}
            >
              <EnhancedCesiumMap
                key={`satellite-orbit-${satellite.id}-${mapKey}`}
                location={null}
                visible={true}
                satelliteNames={[satellite.fullName]}
                onSatelliteClick={(satelliteName) => {
                  console.log('点击卫星:', satelliteName);
                }}
              />

              {/* 🔧 新增：底部渐变遮罩，确保控制器可见性 */}
              <div
                className="absolute bottom-0 left-0 right-0 pointer-events-none"
                style={{
                  height: '80px',
                  background: 'linear-gradient(to top, rgba(0,0,0,0.1) 0%, transparent 100%)',
                  zIndex: 0
                }}
              />
            </div>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-white">
                <div className="text-6xl mb-4">🛰️</div>
                <h3 className="text-xl font-semibold mb-2">轨道视图已隐藏</h3>
                <p className="text-gray-300">点击"显示轨道"按钮查看3D轨道</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SatelliteDetail;