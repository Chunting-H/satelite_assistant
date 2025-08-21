// components/Satellite/SatelliteFilters.jsx - 修复版本：修复JSX语法错误
import React, { useState } from 'react';

const SatelliteFilters = ({ filters, onFiltersChange, statistics }) => {
  const [expandedSections, setExpandedSections] = useState({
    launchDate: true,
    status: true,
    owner: true,
    orbitType: true,
    orbitPeriod: false,
    revisitPeriod: false,
    crossingTime: false,
    orbitLongitude: false,
    launchSite: false,
    endDate: false
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleFilterChange = (filterType, value) => {
    onFiltersChange(prev => ({
      ...prev,
      [filterType]: value
    }));
  };

  const handleCheckboxChange = (filterType, option) => {
    // 🔧 修复：确保 currentValues 始终是数组
    const currentValues = Array.isArray(filters[filterType]) ? filters[filterType] : [];
    const newValues = currentValues.includes(option)
      ? currentValues.filter(item => item !== option)
      : [...currentValues, option];

    handleFilterChange(filterType, newValues);
  };

  const clearAllFilters = () => {
    onFiltersChange({
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
    });
  };

  // 按数量降序；数量相同按中文友好顺序
  const sortByCountDesc = (obj) =>
  Object.entries(obj || {}).sort(([aLabel, aCount], [bLabel, bCount]) => {
    if ((bCount || 0) !== (aCount || 0)) return (bCount || 0) - (aCount || 0);
    // 数量相同：按中英文名自然顺序
    return String(aLabel).localeCompare(String(bLabel), 'zh-Hans-CN');
  });


  // 🔧 修复：安全获取 filters 值的辅助函数
  const getFilterArray = (filterName) => {
    return Array.isArray(filters[filterName]) ? filters[filterName] : [];
  };

  const getFilterObject = (filterName, defaultValue = {}) => {
    return filters[filterName] && typeof filters[filterName] === 'object' ? filters[filterName] : defaultValue;
  };

  const FilterSection = ({ title, isExpanded, onToggle, children }) => (
    <div className="border-b border-gray-200">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-50"
      >
        <span className="font-medium text-gray-900">{title}</span>
        <svg
          className={`w-5 h-5 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isExpanded && (
        <div className="px-4 pb-4">
          {children}
        </div>
      )}
    </div>
  );

  const CheckboxOption = ({ label, count, checked, onChange }) => (
    <label className="flex items-center space-x-2 py-1 cursor-pointer hover:bg-gray-50 px-2 rounded">
      <input
        type="checkbox"
        checked={checked || false}
        onChange={onChange}
        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
      />
      <span className="text-sm text-gray-700 flex-1">{label}</span>
      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
        {count || 0}
      </span>
    </label>
  );

  const RangeInput = ({ label, value, onChange, type = "text", placeholder }) => (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div className="flex space-x-2">
        <input
          type={type}
          placeholder={`最小${placeholder || ''}`}
          value={value.min || ''}
          onChange={(e) => onChange({ ...value, min: e.target.value })}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
        <input
          type={type}
          placeholder={`最大${placeholder || ''}`}
          value={value.max || ''}
          onChange={(e) => onChange({ ...value, max: e.target.value })}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    </div>
  );

  const DateRangeInput = ({ label, value, onChange }) => (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div className="flex space-x-2">
        <input
          type="date"
          value={value.start || ''}
          onChange={(e) => onChange({ ...value, start: e.target.value })}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
        <input
          type="date"
          value={value.end || ''}
          onChange={(e) => onChange({ ...value, end: e.target.value })}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    </div>
  );

  const TimeRangeInput = ({ label, value, onChange }) => (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div className="flex space-x-2">
        <input
          type="time"
          value={value.start || ''}
          onChange={(e) => onChange({ ...value, start: e.target.value })}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
        <input
          type="time"
          value={value.end || ''}
          onChange={(e) => onChange({ ...value, end: e.target.value })}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    </div>
  );

  // 🔧 修复：安全获取统计数据，避免 undefined 错误
  const safeStatistics = {
    status: statistics?.status || {},
    owner: statistics?.owner || {},
    orbitType: statistics?.orbitType || {},
    launchSite: statistics?.launchSite || {}
  };

  return (
    <div className="h-full flex flex-col">
      {/* 标题和清除按钮 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">过滤条件</h2>
          <button
            onClick={clearAllFilters}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            清除全部
          </button>
        </div>
      </div>

      {/* 过滤条件列表 */}
      <div className="flex-1 overflow-y-auto">
        {/* 发射日期 */}
        <FilterSection
          title="发射日期"
          isExpanded={expandedSections.launchDate}
          onToggle={() => toggleSection('launchDate')}
        >
          <DateRangeInput
            label="发射日期范围"
            value={getFilterObject('launchDateRange', { start: '', end: '' })}
            onChange={(value) => handleFilterChange('launchDateRange', value)}
          />
        </FilterSection>

        {/* 运行状态 */}
        <FilterSection
          title="运行状态"
          isExpanded={expandedSections.status}
          onToggle={() => toggleSection('status')}
        >
          <div className="space-y-1">
            {sortByCountDesc(safeStatistics.status).map(([status, count]) => (
                <CheckboxOption
                  key={status}
                  label={status}
                  count={count}
                  checked={getFilterArray('status').includes(status)}
                  onChange={() => handleCheckboxChange('status', status)}
                />
             ))}
          </div>
        </FilterSection>

        {/* 所有者 */}
        <FilterSection
          title="所有者"
          isExpanded={expandedSections.owner}
          onToggle={() => toggleSection('owner')}
        >
          <div className="space-y-1">
            {sortByCountDesc(safeStatistics.owner).map(([owner, count]) => (
                <CheckboxOption
                  key={owner}
                  label={owner}
                  count={count}
                  checked={getFilterArray('owner').includes(owner)}
                  onChange={() => handleCheckboxChange('owner', owner)}
                />
             ))}
          </div>
        </FilterSection>

        {/* 轨道类型 */}
        <FilterSection
          title="轨道类型"
          isExpanded={expandedSections.orbitType}
          onToggle={() => toggleSection('orbitType')}
        >
          <div className="space-y-1">
            {sortByCountDesc(safeStatistics.orbitType).map(([orbitType, count]) => (
                <CheckboxOption
                  key={orbitType}
                  label={orbitType}
                  count={count}
                  checked={getFilterArray('orbitType').includes(orbitType)}
                  onChange={() => handleCheckboxChange('orbitType', orbitType)}
                />
             ))}
          </div>
        </FilterSection>

        {/* 轨道周期 */}
        <FilterSection
          title="轨道周期 (分钟)"
          isExpanded={expandedSections.orbitPeriod}
          onToggle={() => toggleSection('orbitPeriod')}
        >
          <RangeInput
            label="轨道周期范围"
            value={getFilterObject('orbitPeriodRange', { min: '', max: '' })}
            onChange={(value) => handleFilterChange('orbitPeriodRange', value)}
            type="number"
            placeholder="分钟"
          />
        </FilterSection>

        {/* 重复周期 */}
        <FilterSection
          title="重复周期 (天)"
          isExpanded={expandedSections.revisitPeriod}
          onToggle={() => toggleSection('revisitPeriod')}
        >
          <RangeInput
            label="重复周期范围"
            value={getFilterObject('revisitRange', { min: '', max: '' })}
            onChange={(value) => handleFilterChange('revisitRange', value)}
            type="number"
            placeholder="天"
          />
        </FilterSection>

        {/* 赤道过境时间 */}
        <FilterSection
          title="赤道过境时间"
          isExpanded={expandedSections.crossingTime}
          onToggle={() => toggleSection('crossingTime')}
        >
          <TimeRangeInput
            label="过境时间范围"
            value={getFilterObject('crossingTimeRange', { start: '', end: '' })}
            onChange={(value) => handleFilterChange('crossingTimeRange', value)}
          />
        </FilterSection>

        {/* 轨道经度 */}
        <FilterSection
          title="轨道经度"
          isExpanded={expandedSections.orbitLongitude}
          onToggle={() => toggleSection('orbitLongitude')}
        >
          <RangeInput
            label="轨道经度范围"
            value={getFilterObject('orbitLongitudeRange', { min: '', max: '' })}
            onChange={(value) => handleFilterChange('orbitLongitudeRange', value)}
            type="number"
            placeholder="度"
          />
        </FilterSection>

        {/* 发射地点 */}
        <FilterSection
          title="发射地点"
          isExpanded={expandedSections.launchSite}
          onToggle={() => toggleSection('launchSite')}
        >
          <div className="space-y-1">
            {sortByCountDesc(safeStatistics.launchSite).map(([site, count]) => (
                <CheckboxOption
                  key={site}
                  label={site}
                  count={count}
                  checked={getFilterArray('launchSite').includes(site)}
                  onChange={() => handleCheckboxChange('launchSite', site)}
                />
             ))}
          </div>
        </FilterSection>

        {/* 终止日期 */}
        <FilterSection
          title="终止日期"
          isExpanded={expandedSections.endDate}
          onToggle={() => toggleSection('endDate')}
        >
          <DateRangeInput
            label="终止日期范围"
            value={getFilterObject('endDateRange', { start: '', end: '' })}
            onChange={(value) => handleFilterChange('endDateRange', value)}
          />
        </FilterSection>
      </div>
    </div>
  );
};

export default SatelliteFilters;