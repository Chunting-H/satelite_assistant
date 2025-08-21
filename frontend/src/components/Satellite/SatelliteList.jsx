// components/Satellite/SatelliteList.jsx
import React, { useState } from 'react';

const SatelliteList = ({ satellites, onSatelliteSelect, searchQuery }) => {
  const [sortField, setSortField] = useState('launchDate');
  const [sortDirection, setSortDirection] = useState('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  // 排序处理
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
    setCurrentPage(1);
  };

  // 排序卫星数据
  const sortedSatellites = [...satellites].sort((a, b) => {
    let aValue = a[sortField];
    let bValue = b[sortField];

    // 处理日期字段
    if (sortField === 'launchDate') {
      aValue = new Date(aValue || '1900-01-01').getTime();
      bValue = new Date(bValue || '1900-01-01').getTime();
    }

    // 处理数字字段
    if (sortField === 'orbitPeriod') {
      aValue = parseFloat(aValue) || 0;
      bValue = parseFloat(bValue) || 0;
    }

    // 处理字符串字段
    if (typeof aValue === 'string') {
      aValue = aValue.toLowerCase();
      bValue = bValue.toLowerCase();
    }

    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  // 分页处理
  const totalPages = Math.ceil(sortedSatellites.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedSatellites = sortedSatellites.slice(startIndex, startIndex + itemsPerPage);

  // 获取状态颜色
  const getStatusColor = (status) => {
    const s = String(status || '').toLowerCase(); // 英文会变小写，中文不受影响
    switch (s) {
      case 'operational':
      case '运行中':
        return 'bg-green-100 text-green-800';

      case 'nonoperational':
      case '停用/退役':
      case 'decayed':
      case '已再入/衰减':
        return 'bg-red-100 text-red-800';

      case 'unknown':
      case '未知':
        return 'bg-yellow-100 text-yellow-800';

      case 'partially operational':
      case '部分运行':
        return 'bg-orange-100 text-orange-800';

      case 'extended mission':
      case '延长任务':
        return 'bg-blue-100 text-blue-800';

      case 'backup/standby':
      case '备用/待机':
        return 'bg-purple-100 text-purple-800';

      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // 高亮搜索关键词（转义特殊字符，避免正则报错）
  const escapeRegExp = (s = '') => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const highlightText = (text, query) => {
    if (!query || !text) return text;
    const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
    const parts = String(text).split(regex);
    return parts.map((part, index) =>
      regex.test(part) ? (
        <mark key={index} className="bg-yellow-200 px-1 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  /* ---------------- 别名逻辑：中文主名 + 去重别名（含英文） ---------------- */
  const isChinese = (s = '') => /[\u4e00-\u9fa5]/.test(String(s));
  const buildAliasList = (satellite = {}) => {
    const primary = String(satellite.fullName || '').trim();
    const lowerPrimary = primary.toLowerCase();
    const rawAliases = Array.isArray(satellite.aliases) ? [...satellite.aliases] : [];

    // 若主名是中文，把英文名并入别名候选
    if (isChinese(primary) && satellite.englishName) {
      rawAliases.unshift(satellite.englishName);
    }

    // 去空、大小写去重、去掉与主名相同的项
    const seen = new Set();
    return rawAliases
      .map((v) => String(v || '').trim())
      .filter(Boolean)
      .filter((v) => v.toLowerCase() !== lowerPrimary)
      .filter((v) => {
        const k = v.toLowerCase();
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      });
  };

  const SortButton = ({ field, children }) => (
    <button
      onClick={() => handleSort(field)}
      className={`flex items-center space-x-1 px-3 py-1 rounded-md text-sm font-medium transition-colors ${
        sortField === field
          ? 'bg-blue-100 text-blue-700 border border-blue-200'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
      }`}
    >
      <span>{children}</span>
      {sortField === field && (
        <svg
          className={`w-4 h-4 transition-transform ${sortDirection === 'desc' ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      )}
    </button>
  );

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 头部 */}
      <div className="bg-gradient-to-r from-white-50 to-indigo-50 border-b border-black-200 shadow-sm">
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900">
              卫星列表 ({satellites.length} 颗)
            </h2>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600 bg-white/60 px-2 py-1 rounded-md">
                第 {startIndex + 1}-{Math.min(startIndex + itemsPerPage, satellites.length)} 条
              </span>
            </div>
          </div>

          {/* 排序控制 */}
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-gray-700 font-medium">排序方式：</span>
            <div className="flex items-center gap-2 flex-wrap">
              <SortButton field="launchDate">发射日期</SortButton>
              <SortButton field="fullName">名称</SortButton>
              <SortButton field="status">状态</SortButton>
              <SortButton field="owner">所有者</SortButton>
              <SortButton field="orbitPeriod">轨道周期</SortButton>
            </div>
          </div>
        </div>
      </div>

      {/* 列表 */}
      <div className="flex-1 overflow-y-auto">
        {paginatedSatellites.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="text-4xl mb-4">🛰️</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">未找到匹配的卫星</h3>
              <p className="text-gray-500">请尝试调整筛选条件或搜索关键词</p>
            </div>
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {paginatedSatellites.map((satellite) => (
              <div
                key={satellite.id}
                onClick={() => onSatelliteSelect(satellite)}
                className="bg-white rounded-xl p-5 hover:shadow-md cursor-pointer transition-all duration-200 border border-gray-200 hover:border-blue-300 hover:bg-blue-50/30"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* 主名（中文优先） */}
                    <h3 className="text-lg font-semibold text-gray-900 truncate mb-1">
                      {highlightText(satellite.fullName, searchQuery)}
                    </h3>

                    {/* 别名 chips（含英文，去重且不与主名重复） */}
                    {(() => {
                      const aliasList = buildAliasList(satellite);
                      return aliasList.length > 0 ? (
                        <div className="flex flex-wrap gap-2 mb-3">
                          {aliasList.map((name, i) => (
                            <span
                              key={i}
                              className="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-xs"
                              title={name}
                            >
                              {highlightText(name, searchQuery)}
                            </span>
                          ))}
                        </div>
                      ) : null;
                    })()}

                    {/* 基本信息网格 */}
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                      <div className="flex items-center">
                        <span className="text-gray-500 w-20 flex-shrink-0">🚀 发射：</span>
                        <span className="text-gray-900 font-medium">{satellite.launchDate || '未知'}</span>
                      </div>
                      <div className="flex items-center">
                        <span className="text-gray-500 w-20 flex-shrink-0">🌍 所有者：</span>
                        <span className="text-gray-900 font-medium truncate">{satellite.owner || '未知'}</span>
                      </div>
                      <div className="flex items-center">
                        <span className="text-gray-500 w-20 flex-shrink-0">🛸 轨道：</span>
                        <span className="text-gray-900 font-medium">{satellite.orbitType || '未知'}</span>
                      </div>
                      <div className="flex items-center">
                        <span className="text-gray-500 w-20 flex-shrink-0">⏱️ 周期：</span>
                        <span className="text-gray-900 font-medium">{satellite.orbitPeriod || '未知'}分钟</span>
                      </div>
                    </div>

                    {/* 描述 */}
                    {satellite.description && (
                      <p className="mt-3 text-sm text-gray-600 line-clamp-2 leading-relaxed">
                        {satellite.description}
                      </p>
                    )}
                  </div>

                  {/* 右侧状态和操作 */}
                  <div className="ml-6 flex flex-col items-end space-y-3">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium shadow-sm ${getStatusColor(satellite.status)}`}>
                      {satellite.status || 'Unknown'}
                    </span>
                    <span className="text-xs text-gray-600 bg-gray-100 px-3 py-1 rounded-full font-medium">
                      {satellite.country || satellite.owner}
                    </span>
                    <button className="text-blue-600 hover:text-blue-800 text-sm font-medium bg-blue-50 hover:bg-blue-100 px-3 py-1 rounded-md transition-colors">
                      查看详情 →
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="bg-gradient-to-r from-green-50 to-indigo-50 border-t border-black-200">
          <div className="p-4">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-700 bg-white/60 px-3 py-1 rounded-md">
                共 {satellites.length} 条记录，第 {currentPage} / {totalPages} 页
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-4 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
                >
                  上一页
                </button>

                {/* 页码显示（最多 5 个） */}
                <div className="flex space-x-1">
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
                    const pageNum = Math.max(1, currentPage - 2) + i;
                    if (pageNum > totalPages) return null;
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`px-3 py-2 text-sm border rounded-lg transition-colors shadow-sm ${
                          pageNum === currentPage
                            ? 'bg-blue-500 text-white border-blue-500'
                            : 'bg-white border-gray-300 hover:bg-blue-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="px-4 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
                >
                  下一页
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SatelliteList;
