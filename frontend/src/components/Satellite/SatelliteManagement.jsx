// components/Satellite/SatelliteManagement.jsx
import React, { useState, useEffect, useMemo } from 'react';
import SatelliteFilters from './SatelliteFilters';
import SatelliteList from './SatelliteList';
import SatelliteDetail from './SatelliteDetail';
import SatelliteChat from './SatelliteChat';
import DataUpdateRecords from './DataUpdateRecords';
// ✅ 引入 JSON 数据源（Vite 原生支持 JSON 导入）
import eo from '../../config/eo_satellite.zh.json';

/* -------------------- 内联适配器：把 JSON 数组 → 旧的对象结构 -------------------- */
// 小工具
const splitToArray = (s) => (s ? String(s).split(/[;,，、]\s*/).filter(Boolean) : []);
// —— 解析出轨道代码（始终返回代码字符串）——
const parseOrbitCode = (raw) => {
  if (!raw) return 'UNKNOWN';
  const s = String(raw).trim();

  // 1) 先看中文/英文括号里是否有代码：如 “中地轨道（MEO）”、“GEO（GEO_S）”
  const mParen = s.match(/[（(]\s*([A-Z][A-Z0-9_]{1,8})\s*[)）]/);
  if (mParen) return mParen[1];

  // 2) 再看是否以代码打头：如 “LEO_I (xxx)”
  const mHead = s.match(/^([A-Z][A-Z0-9_]{1,8})/);
  if (mHead) return mHead[1];

  // 3) 中文关键词兜底
  if (/中地/.test(s)) return 'MEO';
  if (/转移/.test(s)) return 'GTO';
  if (/地球同步/.test(s)) return 'GEO_S';
  if (/高椭圆|莫尔尼亚|molniya/i.test(s)) return /莫尔尼亚|molniya/i.test(s) ? 'HEO_M' : 'HEO';
  if (/近地|低轨|LEO/i.test(s)) return 'LEO_I';
  return 'UNKNOWN';
};

// —— 代码 → 统一展示“中文（代码）”——
const ORBIT_DISPLAY_MAP = {
  // 近地近地轨道（LEO 系列）
  LEO_I: '近地倾斜轨道（LEO_I）',
  LEO_S: '太阳同步近地轨道（LEO_S）',
  LEO_P: '近地极地轨道（LEO_P）',
  LEO_E: '近地椭圆轨道（LEO_E）',
  LEO_R: '近地逆行轨道（LEO_R）',

  // 超低近地轨道（LLEO 系列）
  LLEO_I: '超低近地倾斜轨道（LLEO_I）',
  LLEO_S: '超低太阳同步近地轨道（LLEO_S）',
  LLEO_P: '超低近地极地轨道（LLEO_P）',
  LLEO_R: '超低近地逆行轨道（LLEO_R）',

  // 中地轨道
  MEO: '中地轨道（MEO）',

  // 地球同步轨道（GEO 系列）
  GEO_S: '地球同步轨道（GEO_S）',
  GEO_I: '倾斜地球同步轨道（GEO_I）',
  GEO_R: '地球同步漂移轨道（GEO_R）',
  GEO_D: '地球同步弃置轨道（GEO_D）',
  GEO_T: '地球同步试验轨道（GEO_T）',
  GEO_ID: '地球同步轨道（GEO_ID）', // 缩写含义未查到，请确认
  GEO_NS: '地球同步轨道（GEO_NS）', // 缩写含义未查到，请确认

  // 高椭圆轨道（HEO 系列）
  HEO: '高椭圆轨道（HEO）',
  HEO_M: '莫尔尼亚轨道（HEO_M）',
  HEO_R: '高椭圆轨道（HEO_R）',

  // 其他轨道类型
  VHEO: '极高地球轨道（VHEO）',
  GTO: '地球同步转移轨道（GTO）',
  CLO: '环月轨道（CLO）',
  DSO: '深空轨道（DSO）',

  UNKNOWN: '未知轨道（UNKNOWN）',
};


const toOrbitDisplay = (codeOrRaw) => {
  const code = parseOrbitCode(codeOrRaw);
  return ORBIT_DISPLAY_MAP[code] || `未知（${code}）`;
};


// ✅ 状态直接展示（英文 → 中文映射），不做“合并/归类”
const mapStatusZh = (v) => {
  const t = String(v || '').trim().toLowerCase();
  if (t === 'operational') return '运行中';
  if (t === 'nonoperational') return '停用/退役';
  if (t === 'partially operational') return '部分运行';
  if (t === 'extended mission') return '延长任务';
  if (t === 'backup/standby' || t === 'backup' || t === 'standby') return '备用/待机';
  if (t === 'decayed') return '已再入/衰减';
  if (t === 'unknown' || !t) return '未知';
  // 兜底：如果是其他英文状态，直接原样返回；否则仍给“未知”
  return /[a-z]/.test(t) ? v : '未知';
};

// 适配：把 eo_satellite.zh.json（数组）转换成页面一直使用的对象结构 SATELLITE_DATABASE
const adaptEoToLegacy = (list) => Object.fromEntries(
  (Array.isArray(list) ? list : []).map((rec, idx) => {
    const id = rec.NORADId ?? rec.COSPARId ?? `${rec.satelliteName || 'SAT'}-${idx}`;
    const fullName = rec.satelliteName_zh || rec.satelliteName || `SAT-${id}`;
    const englishName = (rec.alternateNames && rec.alternateNames[0]) || rec.satelliteName || '';
    const owner = rec.owner_zh || rec.owner || rec.satelliteAgencies_zh || rec.satelliteAgencies || 'Unknown';
    const agencies = splitToArray(rec.satelliteAgencies_zh || rec.satelliteAgencies);
    const orbitTypeCode = parseOrbitCode(rec.orbitType_zh || rec.orbitType);
    const orbitType = ORBIT_DISPLAY_MAP[orbitTypeCode] || `未知（${orbitTypeCode}）`;
    const periodMin = (rec.period != null && !Number.isNaN(Number(rec.period))) ? Number(rec.period) : undefined;

    return [fullName, {
      // —— 列表 / 筛选常用字段 —— 
      id,
      fullName,
      englishName,
      // ❌ 删除“描述清洗/去重/摘要”的逻辑与字段（未使用）
      // description: ...
      launchDate: rec.launchDate || '',     // ISO: YYYY-MM-DD
      endDate: rec.eolDate || null,
      owner,
      country: owner,                       // 向后兼容
      // ✅ 仅使用 operStatusCode，并映射为中文展示值
      status: mapStatusZh(rec.operStatusCode),
      orbitType,         // ✅ 用于界面&筛选：始终是“中文（代码）”
      orbitTypeCode,     // ✅ 备用：纯代码（如需要做统计或对接）

      orbitPeriod: periodMin,               // 分钟（数字）

      // —— 详情页字段（尽量补齐） —— 
      aliases: rec.alternateNames || [],
      cosparId: rec.COSPARId || '',
      noradId: rec.NORADId || '',
      agencies,
      type: rec.objectType_zh || rec.objectType || '地球观测',
      launchSite: rec.launchSite_zh || rec.launchSite || '',
      crossingTime: rec.ect || '',
      orbitLongitude: rec.orbitLongitude || '',
      revisit: rec.repeatCycle || '',
      revisitPeriod: rec.repeatCycle || '',

      // 轨道细节
      altitude: rec.orbitAltitude || '',
      orbitParams: {
        inclination: rec.inclination,   // °
        apogeeHeight: rec.apogee,       // km
        perigeeHeight: rec.perigee,     // km
      },

      // 载荷/仪器（源数据缺就留空）
      spectralBands: [],
      swathWidth: '',
      spatialResolution: '',
      instrumentNames: rec.instrumentNames_zh || rec.instrumentNames || [],
      instrumentIds: rec.instrumentIds || [],

      // ✅ 新增：应用与数据相关字段（供详情页“应用与数据”使用）
      applications: rec.applications || rec.applications_zh || [],
      applicationsZh: rec.applications_zh || rec.applications || [],
      webInfo: Array.isArray(rec.webInfo) ? rec.webInfo : [],
      dataPortal: Array.isArray(rec.dataPortal) ? rec.dataPortal : [],
      eoPortal: rec.eoPortal || '',
    }];
  })
);

// ✅ 页面后续逻辑仍然使用这个名字，其他组件无感知
const SATELLITE_DATABASE = adaptEoToLegacy(eo);

/* -------------------- 通用：安全取年份（兼容 ISO 和 “YYYY年…”） -------------------- */
const getYear = (val) => {
  if (!val) return 0;
  const d = new Date(val);
  if (!Number.isNaN(d.getTime())) return d.getFullYear(); // 兼容 YYYY-MM-DD
  const m = String(val).match(/^(\d{4})年/);              // 兼容 “2013年4月26日”
  return m ? Number(m[1]) : 0;
};

const SatelliteManagement = ({ onBack }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSatellite, setSelectedSatellite] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showDataUpdate, setShowDataUpdate] = useState(false);

  // 过滤器默认结构（集中管理）
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

  // 安全合并过滤器
  const handleFiltersChange = (newFiltersOrUpdater) => {
    setFilters(prevFilters => {
      const incoming = (typeof newFiltersOrUpdater === 'function')
        ? newFiltersOrUpdater(prevFilters)
        : newFiltersOrUpdater;

      const safe = { ...defaultFilters, ...prevFilters, ...incoming };

      // 数组字段兜底
      ['status', 'owner', 'orbitType', 'launchSite'].forEach(f => {
        if (!Array.isArray(safe[f])) safe[f] = [];
      });

      // 区间对象兜底
      ['launchDateRange', 'orbitPeriodRange', 'revisitRange', 'crossingTimeRange', 'orbitLongitudeRange', 'endDateRange']
        .forEach(f => {
          const v = safe[f];
          if (!v || typeof v !== 'object') {
            safe[f] = (f.includes('Period') || f.includes('Longitude') || f.includes('revisit'))
              ? { min: '', max: '' }
              : { start: '', end: '' };
          }
        });

      return safe;
    });
  };

  /* -------------------- 读库 & 规范化：对象 → 数组 -------------------- */
  const satelliteData = useMemo(() => {
    try {
      if (!SATELLITE_DATABASE || typeof SATELLITE_DATABASE !== 'object') return [];

      const entries = Object.entries(SATELLITE_DATABASE);
      if (entries.length === 0) return [];

      const processed = entries.map(([key, s]) => {
        if (!s || typeof s !== 'object') return null;

        // ✅ 状态不再二次归类，直接使用中文展示值
        const statusDisplay = s.status || '未知';

        const orbitTypeStd =
              s.orbitType ||
              ORBIT_DISPLAY_MAP[s.orbitTypeCode] ||
              ORBIT_DISPLAY_MAP['LEO_I'];

        // 统一成“分钟”数值
        const periodMin = (s.orbitPeriod != null && !Number.isNaN(Number(s.orbitPeriod)))
          ? Number(s.orbitPeriod)
          : (s.orbitParams?.orbitPeriod ? Number(s.orbitParams.orbitPeriod) / 60 : undefined);

        return {
          id: s.id || key,
          ...s,
          status: statusDisplay,
          owner: s.owner || s.country || 'Unknown',
          orbitType: orbitTypeStd,
          orbitPeriod: periodMin ?? 97.4, // 缺失时给一个合理默认
          revisitPeriod: s.revisitPeriod || s.revisit || 'Unknown',
          crossingTime: s.crossingTime || s.orbitParams?.crossingTime || 'Unknown',
          orbitLongitude: s.orbitLongitude || 'Unknown',
          launchSite: s.launchSite ||
            (s.country === '中国' ? 'Jiuquan Space Center, PRC'
              : s.country === '美国' ? 'Air Force Eastern Test Range'
              : 'Unknown'),
          endDate: s.endDate ?? null,
        };
      }).filter(Boolean);

      return processed;
    } catch (e) {
      console.error('处理卫星数据时出错:', e);
      return [];
    }
  }, []);

  /* -------------------- 搜索 + 过滤：得到当前视图 -------------------- */
  const filteredSatellites = useMemo(() => {
    try {
      if (!Array.isArray(satelliteData)) return [];

      return satelliteData.filter(satellite => {
        if (!satellite || typeof satellite !== 'object') return false;

        // 搜索：中英文名
        if (searchQuery && searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const full = (satellite.fullName || '').toLowerCase();
          const eng = (satellite.englishName || '').toLowerCase();
          if (!full.includes(q) && !eng.includes(q)) return false;
        }

        // 状态（注意：这里的 status 已是中文展示值）
        if (Array.isArray(filters.status) && filters.status.length > 0 &&
            !filters.status.includes(satellite.status)) {
          return false;
        }
        // 所有者
        if (Array.isArray(filters.owner) && filters.owner.length > 0 &&
            !filters.owner.includes(satellite.owner)) {
          return false;
        }
        // 轨道类型
        if (Array.isArray(filters.orbitType) && filters.orbitType.length > 0 &&
            !filters.orbitType.includes(satellite.orbitType)) {
          return false;
        }

        // 发射年份范围（✅ 用通用 getYear）
        if (filters.launchDateRange && (filters.launchDateRange.start || filters.launchDateRange.end)) {
          const ly = getYear(satellite.launchDate);
          const sy = filters.launchDateRange.start ? getYear(filters.launchDateRange.start) : 0;
          const ey = filters.launchDateRange.end ? getYear(filters.launchDateRange.end) : 9999;
          if (ly < sy || ly > ey) return false;
        }

        // 轨道周期范围（分钟）
        if (filters.orbitPeriodRange && (filters.orbitPeriodRange.min || filters.orbitPeriodRange.max)) {
          const p = Number(satellite.orbitPeriod) || 0;
          const min = Number(filters.orbitPeriodRange.min) || 0;
          const max = Number(filters.orbitPeriodRange.max) || Infinity;
          if (p < min || p > max) return false;
        }

        return true;
      });
    } catch (e) {
      console.error('应用过滤器时出错:', e);
      return [];
    }
  }, [satelliteData, searchQuery, filters]);

  /* -------------------- 统计：供筛选侧栏计数 -------------------- */
  const statistics = useMemo(() => {
    const stats = { status: {}, owner: {}, orbitType: {}, launchSite: {} };
    if (!Array.isArray(filteredSatellites)) return stats;

    filteredSatellites.forEach(s => {
      const st = s.status || '未知';
      const ow = s.owner || 'Unknown';
      const ot = s.orbitType || 'Unknown';
      const ls = s.launchSite || 'Unknown';
      stats.status[st] = (stats.status[st] || 0) + 1;
      stats.owner[ow] = (stats.owner[ow] || 0) + 1;
      stats.orbitType[ot] = (stats.orbitType[ot] || 0) + 1;
      stats.launchSite[ls] = (stats.launchSite[ls] || 0) + 1;
    });

    return stats;
  }, [filteredSatellites]);

  /* -------------------- 加载态 & 调试 -------------------- */
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 100);
    return () => clearTimeout(timer);
  }, []);

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

  /* -------------------- 事件 -------------------- */
  const handleSatelliteSelect = (satellite) => {
    if (!satellite) return;
    setSelectedSatellite(satellite);
    setShowDetail(true);
  };

  const handleBackToList = () => {
    setShowDetail(false);
    setSelectedSatellite(null);
  };

  const handleSearchChange = (query) => {
    setSearchQuery(query || '');
  };

  /* -------------------- 渲染 -------------------- */
  // 基础校验
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
            {/* 数据更新按钮 */}
            <button
              onClick={() => setShowDataUpdate(true)}
              className="ml-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-3 py-1.5 rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 flex items-center space-x-2 shadow-lg hover:shadow-xl"
              title="查看数据更新记录与手动爬取"
            >
              {/* 爬虫/机器人图标 */}
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span className="text-sm font-medium">数据更新</span>
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

            {/* 中间卫星列表 - 修复：移除多余的滚动容器 */}
            <div className="flex-1 overflow-hidden flex">
              <div className="flex-1 min-h-0">  {/* 关键修改：移除 overflow-y-auto，添加 min-h-0 */}
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
              <div className="flex-1 min-h-0 overflow-hidden">
                <SatelliteDetail
                  satellite={selectedSatellite}
                  onBack={handleBackToList}
                />
              </div>
        )}
      </div>

      {/* 数据更新记录弹窗 */}
      {showDataUpdate && (
        <DataUpdateRecords onClose={() => setShowDataUpdate(false)} />
      )}
    </div>
  );
};

export default SatelliteManagement;
