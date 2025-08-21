// components/Satellite/SatelliteDetail.jsx
import React, { useState, useRef, useEffect } from 'react';
import EnhancedCesiumMap from '../Map/EnhancedCesiumMap';

// 统一的未知值显示
const UNKNOWN_VALUE = '未知';

// 格式化辅助函数
const formatValue = (value, suffix = '') => {
  if (
    value === null ||
    value === undefined ||
    value === '' ||
    value === 'Unknown' ||
    value === 'unknown'
  ) {
    return UNKNOWN_VALUE;
  }
  return suffix ? `${value}${suffix}` : value;
};

// 格式化数组值
const formatArrayValue = (arr, separator = '、') => {
  if (!arr || !Array.isArray(arr) || arr.length === 0) {
    return UNKNOWN_VALUE;
  }
  return arr.filter(item => item && item !== '').join(separator);
};

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr || dateStr === 'Unknown') return UNKNOWN_VALUE;
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toISOString().split('T')[0];
  } catch {
    return dateStr;
  }
};

// 轨道周期（分钟→易读）
const formatOrbitPeriod = (periodMinutes) => {
  if (!periodMinutes || periodMinutes === 'Unknown') return UNKNOWN_VALUE;
  const minutes = Number(periodMinutes);
  if (isNaN(minutes)) return periodMinutes;

  if (minutes < 60) return `${minutes.toFixed(2)} 分钟`;
  if (minutes < 1440) {
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return mins > 0 ? `${hours} 小时 ${mins} 分钟` : `${hours} 小时`;
  }
  const days = Math.floor(minutes / 1440);
  const hours = Math.round((minutes % 1440) / 60);
  return hours > 0 ? `${days} 天 ${hours} 小时` : `${days} 天`;
};

const SatelliteDetail = ({ satellite, onBack }) => {
  const [activeTab, setActiveTab] = useState('basic');
  const [showOrbitMap, setShowOrbitMap] = useState(true);
  const [mapKey, setMapKey] = useState(0);
  const mapContainerRef = useRef(null);

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

  // 窗口尺寸变化时，强制刷新 Cesium（不手算高度）
  useEffect(() => {
    const handleResize = () => setMapKey(prev => prev + 1);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 监听右侧容器大小变化，兼容父级布局调整
  useEffect(() => {
    if (!mapContainerRef.current || !showOrbitMap) return;
    const resizeObserver = new ResizeObserver(() => {
      setTimeout(() => setMapKey(prev => prev + 1), 80);
    });
    resizeObserver.observe(mapContainerRef.current);
    return () => resizeObserver.disconnect();
  }, [showOrbitMap]);

  const getStatusColor = (status) => {
    const statusLower = (status || '').toLowerCase();
    if (status === '运行中' || statusLower === 'operational') return 'bg-green-100 text-green-800';
    if (status === '停用/退役' || statusLower === 'nonoperational') return 'bg-red-100 text-red-800';
    if (status === '已再入/衰减' || statusLower === 'decayed') return 'bg-gray-100 text-gray-800';
    if (status === '未知' || statusLower === 'unknown') return 'bg-yellow-100 text-yellow-800';
    if (status === '部分运行' || statusLower === 'partially operational') return 'bg-orange-100 text-orange-800';
    if (status === '延长任务' || statusLower === 'extended mission') return 'bg-blue-100 text-blue-800';
    return 'bg-gray-100 text-gray-800';
  };

  const InfoRow = ({ label, value, className = "" }) => (
    <tr className={className}>
      <td className="px-4 py-3 text-sm font-medium text-gray-900 bg-gray-50 border-b border-gray-200">
        {label}
      </td>
      <td className="px-4 py-3 text-sm text-gray-700 border-b border-gray-200">
        {value || UNKNOWN_VALUE}
      </td>
    </tr>
  );

  /* ---- 基本信息：按要求移除“任务描述”“应用领域” ---- */
  const BasicInfoTab = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <tbody className="bg-white divide-y divide-gray-200">
          <InfoRow label="卫星名称" value={formatValue(satellite.fullName)} />
          <InfoRow label="英文名称" value={formatValue(satellite.englishName)} />
          <InfoRow label="别称" value={formatArrayValue(satellite.aliases || satellite.alternateNames)} />
          <InfoRow label="COSPAR ID" value={formatValue(satellite.cosparId || satellite.COSPARId)} />
          <InfoRow label="NORAD ID" value={formatValue(satellite.noradId || satellite.NORADId)} />
          <InfoRow label="发射日期" value={formatDate(satellite.launchDate)} />
          <InfoRow label="终止日期" value={satellite.endDate || satellite.eolDate ? formatDate(satellite.endDate || satellite.eolDate) : '在轨运行中'} />
          <InfoRow label="所有者" value={formatValue(satellite.owner || satellite.country)} />
          <InfoRow label="卫星机构" value={formatArrayValue(satellite.agencies || (satellite.satelliteAgencies ? [satellite.satelliteAgencies] : []))} />
          <InfoRow label="发射地点" value={formatValue(satellite.launchSite)} />
          <InfoRow
            label="运行状态"
            value={
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(satellite.status)}`}>
                {formatValue(satellite.status)}
              </span>
            }
          />
          <InfoRow label="卫星类型" value={formatValue(satellite.type || satellite.objectType)} />
        </tbody>
      </table>
    </div>
  );

  const OrbitInfoTab = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <tbody className="bg-white divide-y divide-gray-200">
          <InfoRow label="轨道类型" value={formatValue(satellite.orbitType)} />
          <InfoRow label="轨道周期" value={formatOrbitPeriod(satellite.orbitPeriod || satellite.period)} />
          <InfoRow label="轨道高度" value={formatValue(satellite.orbitHeight || satellite.altitude || satellite.orbitAltitude, satellite.orbitAltitude ? ' km' : '')} />
          <InfoRow label="远地点高度" value={formatValue(satellite.apogeeHeight || satellite.apogee || satellite.orbitParams?.apogeeHeight, ' km')} />
          <InfoRow label="近地点高度" value={formatValue(satellite.perigeeHeight || satellite.perigee || satellite.orbitParams?.perigeeHeight, ' km')} />
          <InfoRow label="倾角" value={formatValue(satellite.inclination || satellite.orbitParams?.inclination, '°')} />
          <InfoRow label="轨道经度" value={formatValue(satellite.orbitLongitude)} />
          <InfoRow label="轨道中心" value={formatValue(satellite.orbitCenter)} />
          <InfoRow label="轨道方向" value={formatValue(satellite.orbitSense)} />
          <InfoRow label="赤道过境时间" value={formatValue(satellite.crossingTime || satellite.ect)} />
          <InfoRow label="重复周期" value={formatValue(satellite.repeatCycle || satellite.revisitPeriod || satellite.revisit, satellite.repeatCycle ? ' 天' : '')} />
          <InfoRow label="轨道偏心率" value={formatValue(satellite.eccentricity)} />
          <InfoRow label="升交点赤经" value={formatValue(satellite.raan, satellite.raan ? '°' : '')} />
          <InfoRow label="近地点幅角" value={formatValue(satellite.argumentOfPerigee, satellite.argumentOfPerigee ? '°' : '')} />
        </tbody>
      </table>
    </div>
  );

  /* ---- 载荷信息：移除“载荷列表”和下面的“应用描述” ---- */
  const PayloadInfoTab = () => {
    const instrumentNames = satellite.instrumentNames || satellite.instrumentIds || [];
    const hasInstruments = instrumentNames.length > 0;

    return (
      <div className="space-y-4">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <tbody className="bg-white divide-y divide-gray-200">
              <InfoRow label="主要载荷" value={formatArrayValue(instrumentNames)} />
              <InfoRow label="载荷类型" value={formatValue(satellite.payloadType || (satellite.isEO === 'Earth observation' ? '地球观测载荷' : UNKNOWN_VALUE))} />
              <InfoRow label="观测光谱" value={formatArrayValue(satellite.spectralBands)} />
              <InfoRow label="空间分辨率" value={formatValue(satellite.spatialResolution)} />
              <InfoRow label="光谱分辨率" value={formatValue(satellite.spectralResolution)} />
              <InfoRow label="时间分辨率" value={formatValue(satellite.temporalResolution || satellite.revisit)} />
              <InfoRow label="观测幅宽" value={formatValue(satellite.swathWidth)} />
              <InfoRow label="观测模式" value={formatValue(satellite.observationModes)} />
              <InfoRow label="载荷数量" value={hasInstruments ? instrumentNames.length : UNKNOWN_VALUE} />
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // 应用与数据：展示 applications_zh / webInfo / dataPortal / eoPortal
  const ApplicationDataTab = () => {
    const appsZh = satellite.applicationsZh || satellite.applications_zh || satellite.applications || [];
    const hasApps = Array.isArray(appsZh) && appsZh.length > 0;

    const webInfo = Array.isArray(satellite.webInfo) ? satellite.webInfo : [];
    const dataPortal = Array.isArray(satellite.dataPortal) ? satellite.dataPortal : [];
    const eoPortal = satellite.eoPortal;

    const hasWebInfo = webInfo.length > 0;
    const hasDataPortal = dataPortal.length > 0;
    const hasEoPortal = !!eoPortal;

    return (
      <div className="space-y-4">
        <div className="bg-blue-50 p-4 rounded-lg">
          <h4 className="font-medium text-gray-900 mb-2">应用与场景</h4>
          {hasApps ? (
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
              {appsZh.map((app, idx) => (
                <li key={idx}>{app}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">暂无应用信息</p>
          )}
        </div>

        {(hasWebInfo || hasDataPortal || hasEoPortal) ? (
          <div className="bg-green-50 p-4 rounded-lg">
            <h4 className="font-medium text-gray-900 mb-2">相关网站 / 数据</h4>
            <div className="space-y-2 text-sm">
              {hasEoPortal && (
                <div className="break-all">
                  <span className="font-medium">eoPortal：</span>
                  <a href={eoPortal} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 break-all">
                    {eoPortal}
                  </a>
                </div>
              )}

              {hasWebInfo && webInfo.map((url, index) => (
                <div key={index} className="break-all">
                  <span className="font-medium">网站 {index + 1}：</span>
                  <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 break-all">
                    {url}
                  </a>
                </div>
              ))}

              {hasDataPortal && dataPortal.map((url, index) => (
                <div key={index} className="break-all">
                  <span className="font-medium">数据门户 {index + 1}：</span>
                  <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 break-all">
                    {url}
                  </a>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-500">暂无相关网站或数据门户信息</p>
          </div>
        )}
      </div>
    );
  };

  const tabs = [
    { id: 'basic', label: '基本信息', component: BasicInfoTab },
    { id: 'orbit', label: '轨道信息', component: OrbitInfoTab },
    { id: 'payload', label: '载荷信息', component: PayloadInfoTab },
    { id: 'application', label: '应用与数据', component: ApplicationDataTab },
  ];

  return (
    <div className="h-full w-full flex bg-white overflow-hidden min-h-0">
      {/* 左侧详情信息 */}
      <div className="w-1/2 flex flex-col border-r border-gray-200 overflow-hidden min-h-0">
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
                  showOrbitMap ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
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
                <h1 className="text-2xl font-bold text-gray-900">{formatValue(satellite.fullName)}</h1>
                {satellite.englishName && (
                  <p className="text-lg text-gray-600 mt-1">{satellite.englishName}</p>
                )}
                <div className="flex items-center space-x-4 mt-2">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(satellite.status)}`}>
                    {formatValue(satellite.status)}
                  </span>
                  <span className="text-sm text-gray-500">
                    {formatValue(satellite.country || satellite.owner)}
                  </span>
                  <span className="text-sm text-gray-500">
                    发射于 {formatDate(satellite.launchDate)}
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

        {/* 标签内容（可滚动区域） */}
        <div className="flex-1 overflow-y-auto p-6 pb-8 min-h-0">
          {tabs.find(tab => tab.id === activeTab)?.component()}
        </div>
      </div>

      {/* 右侧 3D 轨道显示 */}
      <div className="w-1/2 flex flex-col bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 overflow-hidden min-h-0">
        {/* 轨道信息面板 */}
        <div className="flex-shrink-0 p-4 bg-black bg-opacity-30" data-info-panel>
          <div className="bg-white bg-opacity-90 rounded-lg p-4 shadow-md">
            <div className="grid grid-cols-1 gap-4">
              {/* 第一行：卫星名称和状态 */}
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-gray-900">{formatValue(satellite.fullName)}</h3>
                <div className="flex items-center space-x-2">
                  {satellite.status === '运行中' || satellite.status === 'Operational' ? (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                      <div className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></div>
                      在轨运行
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
                      <div className="w-2 h-2 bg-gray-400 rounded-full mr-2"></div>
                      {formatValue(satellite.status)}
                    </span>
                  )}
                </div>
              </div>

              {/* 第二行：轨道参数网格 */}
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div className="bg-white bg-opacity-60 rounded-md p-3">
                  <span className="text-gray-600 block font-medium">轨道高度</span>
                  <span className="text-gray-900 font-bold text-base">
                    {formatValue(satellite.altitude || satellite.orbitAltitude || satellite.orbitHeight, ' km')}
                  </span>
                </div>
                <div className="bg-white bg-opacity-60 rounded-md p-3">
                  <span className="text-gray-600 block font-medium">轨道周期</span>
                  <span className="text-gray-900 font-bold text-base">
                    {formatOrbitPeriod(satellite.orbitPeriod || satellite.period)}
                  </span>
                </div>
                <div className="bg-white bg-opacity-60 rounded-md p-3">
                  <span className="text-gray-600 block font-medium">轨道倾角</span>
                  <span className="text-gray-900 font-bold text-base">
                    {formatValue(satellite.inclination || satellite.orbitParams?.inclination, '°')}
                  </span>
                </div>
                <div className="bg-white bg-opacity-60 rounded-md p-3">
                  <span className="text-gray-600 block font-medium">轨道类型</span>
                  <span className="text-gray-900 font-bold text-base">
                    {satellite.orbitType ? satellite.orbitType.split(' ')[0] : 'LEO'}
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

        {/* 3D地图容器：纯 flex-1，自适应剩余高度 */}
        <div ref={mapContainerRef} className="flex-1 relative min-h-0">
          {showOrbitMap ? (
            <div className="absolute inset-0 w-full h-full">
              <EnhancedCesiumMap
                key={`satellite-orbit-${satellite.id}-${mapKey}`}
                location={null}
                visible={true}
                satelliteNames={[satellite.fullName]}
                onSatelliteClick={(satelliteName) => {
                  console.log('点击卫星:', satelliteName);
                }}
              />
              {/* 底部渐隐遮罩：仅视觉效果，不影响交互 */}
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
                <p className="text-gray-300">点击“显示轨道”按钮查看 3D 轨道</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SatelliteDetail;
