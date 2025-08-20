// src/components/Chat/DataProcessingDialog.jsx
import React, { useState, useEffect } from 'react';
import api from '../../services/api';

const DataProcessingDialog = ({
  isVisible = false,
  satellites = [],
  conversationId,
  onConfirm,
  onCancel,
  onClose
}) => {
  const [selectedCombinations, setSelectedCombinations] = useState([]);
  const [processingOptions, setProcessingOptions] = useState({
    normalize_illumination: true,
    radiometric_correction: true,
    atmospheric_correction: false,
    geometric_correction: false,
    output_format: "geotiff"
  });
  const [showProgress, setShowProgress] = useState(false);
  const [progress, setProgress] = useState(0);

  const ProgressBar = ({ progress }) => (
    <div className="w-full">
      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-3 bg-blue-500 rounded-full transition-all duration-300"
          style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
        />
      </div>
    </div>
  );

  const satelliteCombinations = [
    { id: 'combination_a', name: '组合 A', description: '高分辨率光学卫星组合', satellites: ['高分一号', '高分二号', '高分四号'], estimatedSize: '150 MB', estimatedTime: '3 分钟' },
    { id: 'combination_b', name: '组合 B', description: '多光谱遥感卫星组合', satellites: ['Landsat-8', 'Sentinel-2', '高分六号'], estimatedSize: '200 MB', estimatedTime: '4 分钟' },
    { id: 'combination_c', name: '组合 C', description: '雷达卫星组合', satellites: ['Sentinel-1', '高分三号', 'TerraSAR-X'], estimatedSize: '180 MB', estimatedTime: '3.5 分钟' }
  ];

  useEffect(() => {
    if (satelliteCombinations.length > 0) {
      setSelectedCombinations([satelliteCombinations[0].id]);
    }
  }, []);

  const handleCombinationToggle = (combinationId) => {
    setSelectedCombinations(prev => prev.includes(combinationId) ? prev.filter(id => id !== combinationId) : [...prev, combinationId]);
  };

  const handleOptionChange = (option, value) => {
    setProcessingOptions(prev => ({ ...prev, [option]: value }));
  };

  // 优化：点击确定后立刻回传选择给父组件，由父组件发起处理并显示全局进度条
  const handleConfirm = async () => {
    if (selectedCombinations.length === 0) {
      alert('请至少选择一个卫星组合');
      return;
    }

    const selectedData = selectedCombinations
      .map(id => satelliteCombinations.find(combo => combo.id === id))
      .filter(Boolean);

    const selectedSatellites = selectedData
      .flatMap(combo => Array.isArray(combo.satellites) ? combo.satellites : [])
      .filter(Boolean);

    try {
      // 立即回传，不在对话框内等待后端响应
      if (onConfirm) {
        onConfirm({
          selectedSatellites,
          processingOptions,
          // 不提供 processingId，触发父组件 fallback：父组件自行调用 /api/process-data 并立刻显示全局进度条
          processingId: null
        });
      }
    } catch (error) {
      console.error('处理确认失败:', error);
      alert('启动数据处理失败，请稍后重试');
    }
  };

  useEffect(() => {
    if (!isVisible) {
      setShowProgress(false);
      setProgress(0);
    }
  }, [isVisible]);

  const handleSelectAll = () => {
    if (selectedCombinations.length === satelliteCombinations.length) {
      setSelectedCombinations([]);
    } else {
      setSelectedCombinations(satelliteCombinations.map(combo => combo.id));
    }
  };

  if (!isVisible) return null;

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 mb-4 border border-blue-200">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-800">是否要下载并处理以下卫星组合数据？</h3>
        <p className="text-sm text-gray-600 mt-1">请选择要处理的卫星组合，系统将自动下载并处理相关数据</p>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <label className="block text-gray-700 font-medium">选择卫星组合</label>
          <button onClick={handleSelectAll} className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span>{selectedCombinations.length === satelliteCombinations.length ? '取消全选' : '全选'}</span>
          </button>
        </div>

        <div className="space-y-2">
          {satelliteCombinations.map((combo) => {
            const isSelected = selectedCombinations.includes(combo.id);
            return (
              <label key={combo.id} className={`block p-3 rounded-lg border cursor-pointer transition-all ${isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}`}>
                <div className="flex items-start">
                  <input type="checkbox" checked={isSelected} onChange={() => handleCombinationToggle(combo.id)} className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
                  <div className="ml-3 flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-900">{combo.name}</span>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>约 {combo.estimatedSize}</span>
                        <span>•</span>
                        <span>约 {combo.estimatedTime}</span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{combo.description}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {combo.satellites.map((sat, index) => (
                        <span key={index} className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">{sat}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      <div className="mb-6">
        <label className="block text-gray-700 font-medium mb-3">数据处理选项</label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="flex items-center p-2 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
            <input type="checkbox" checked={processingOptions.normalize_illumination} onChange={(e) => handleOptionChange('normalize_illumination', e.target.checked)} className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
            <span className="ml-3 text-sm text-gray-900">匀光匀色</span>
          </label>
          <label className="flex items-center p-2 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
            <input type="checkbox" checked={processingOptions.radiometric_correction} onChange={(e) => handleOptionChange('radiometric_correction', e.target.checked)} className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
            <span className="ml-3 text-sm text-gray-900">辐射校正</span>
          </label>
          <label className="flex items-center p-2 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
            <input type="checkbox" checked={processingOptions.atmospheric_correction} onChange={(e) => handleOptionChange('atmospheric_correction', e.target.checked)} className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
            <span className="ml-3 text-sm text-gray-900">大气校正</span>
          </label>
          <label className="flex items-center p-2 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
            <input type="checkbox" checked={processingOptions.geometric_correction} onChange={(e) => handleOptionChange('geometric_correction', e.target.checked)} className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
            <span className="ml-3 text-sm text-gray-900">几何校正</span>
          </label>
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">输出格式</label>
          <select value={processingOptions.output_format} onChange={(e) => handleOptionChange('output_format', e.target.value)} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
            <option value="geotiff">GeoTIFF</option>
            <option value="tiff">TIFF</option>
            <option value="png">PNG</option>
            <option value="jpg">JPEG</option>
          </select>
        </div>
      </div>

      <div className="bg-white bg-opacity-50 p-4 rounded-lg mb-6">
        <h4 className="text-sm font-medium text-gray-900 mb-2">预估信息</h4>
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
          <div><span className="font-medium">预估数据大小:</span><span className="ml-2">约 {selectedCombinations.length * 50} MB</span></div>
          <div><span className="font-medium">预估处理时间:</span><span className="ml-2">约 {selectedCombinations.length * 2} 分钟</span></div>
        </div>
      </div>

      <div className="flex justify-between">
        <div></div>
        <div className="flex gap-3">
          <button onClick={onCancel} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">取消</button>
          <button onClick={handleConfirm} disabled={selectedCombinations.length === 0} className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors">确定</button>
        </div>
      </div>
    </div>
  );
};

export default DataProcessingDialog; 