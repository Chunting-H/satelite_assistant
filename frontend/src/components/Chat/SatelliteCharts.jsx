import React, { useEffect, useRef, useState } from 'react';

// 动态导入 echarts
let echarts = null;

const SatelliteCharts = ({ data, height = 500, containerWidth }) => {
  const [echartsLoaded, setEchartsLoaded] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const chartInstanceRef = useRef(null);

  // 监听容器宽度变化
  useEffect(() => {
    if (chartInstanceRef.current && echarts) {
      const timer = setTimeout(() => {
        chartInstanceRef.current.resize();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [containerWidth]);

  useEffect(() => {
    const loadECharts = async () => {
      try {
        const echartsModule = await import('echarts');
        echarts = echartsModule.default || echartsModule;
        setEchartsLoaded(true);
        console.log('✅ ECharts 加载成功');
      } catch (error) {
        console.error('❌ ECharts 加载失败:', error);
        setLoadError(true);
      }
    };

    loadECharts();
  }, []);

  if (loadError) {
    return <SatelliteChartsBackup data={data} height={height} />;
  }

  if (!echartsLoaded) {
    return (
      <div className="flex items-center justify-center" style={{ height: `${height}px` }}>
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-gray-600">正在加载图表组件...</p>
        </div>
      </div>
    );
  }

  // 传递所有必要的 props
  return <SatelliteChartsWithECharts
    data={data}
    height={height}
    containerWidth={containerWidth}
    chartInstanceRef={chartInstanceRef}
  />;
};

// 使用 ECharts 的图表组件
const SatelliteChartsWithECharts = ({ data, height, containerWidth, chartInstanceRef }) => {
  const validatedData = React.useMemo(() => {
    if (!data) {
      console.warn('📊 图表数据为空，生成默认数据');
      return generateDefaultData();
    }

    const fixed = {
      satellites: data.satellites || [],
      collaborations: data.collaborations || [],
      pattern_analysis: data.pattern_analysis || {},
      summary_stats: data.summary_stats || {},
      recommendations: data.recommendations || []
    };

    if (fixed.satellites.length === 0) {
      console.warn('📊 无卫星数据，使用默认数据');
      return generateDefaultData();
    }

    console.log('📊 图表数据验证完成:', {
      satellites: fixed.satellites.length,
      collaborations: fixed.collaborations.length
    });

    return fixed;
  }, [data]);

  return (
    <div className="space-y-4">
      {/* 数据概览卡片 */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{validatedData.summary_stats.total_satellites || 0}</div>
            <div className="text-sm text-gray-600">卫星数量</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{validatedData.summary_stats.total_collaborations || 0}</div>
            <div className="text-sm text-gray-600">协同关系</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{(validatedData.summary_stats.avg_collaboration_frequency || 0).toFixed(1)}</div>
            <div className="text-sm text-gray-600">平均协同频率</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{((validatedData.summary_stats.network_density || 0) * 100).toFixed(0)}%</div>
            <div className="text-sm text-gray-600">网络密度</div>
          </div>
        </div>
      </div>

      {/* 专注展示增强版雷达图 - 传递 chartInstanceRef */}
      <EnhancedSatelliteRadarChart 
        data={validatedData} 
        height={height} 
        chartInstanceRef={chartInstanceRef} 
      />

      {/* 推荐信息 */}
      {validatedData.recommendations && validatedData.recommendations.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2 flex items-center">
            <span className="text-xl mr-2">💡</span>
            智能推荐
          </h3>
          <ul className="space-y-1">
            {validatedData.recommendations.map((rec, index) => (
              <li key={index} className="flex items-start text-sm">
                <span className="text-yellow-600 mr-2">•</span>
                <span className="text-yellow-800">{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

// 增强版雷达图 - 修复：接收 chartInstanceRef 作为 props
const EnhancedSatelliteRadarChart = ({ data, height = 600, chartInstanceRef }) => {
  const chartRef = useRef(null);
  const resizeTimeoutRef = useRef(null);
  
  useEffect(() => {
    if (!data || !chartRef.current || !echarts) return;

    const chart = echarts.init(chartRef.current);
    
    // 保存实例引用
    if (chartInstanceRef) {
      chartInstanceRef.current = chart;
    }
    
    // 定义更详细的能力指标
    const indicators = [
      { name: '空间分辨率', max: 100, color: '#4F46E5' },
      { name: '时间分辨率', max: 100, color: '#7C3AED' },
      { name: '光谱分辨率', max: 100, color: '#EC4899' },
      { name: '覆盖范围', max: 100, color: '#F59E0B' },
      { name: '数据质量', max: 100, color: '#10B981' },
      { name: '实时性', max: 100, color: '#3B82F6' }
    ];

    // 准备卫星数据，最多显示6颗卫星避免过于拥挤
    const satellites = data.satellites.slice(0, 6);

    // 定义渐变色方案
    const colorScheme = [
      { color: '#5470c6', areaColor: 'rgba(84, 112, 198, 0.2)' },
      { color: '#91cc75', areaColor: 'rgba(145, 204, 117, 0.2)' },
      { color: '#fac858', areaColor: 'rgba(250, 200, 88, 0.2)' },
      { color: '#ee6666', areaColor: 'rgba(238, 102, 102, 0.2)' },
      { color: '#73c0de', areaColor: 'rgba(115, 192, 222, 0.2)' },
      { color: '#3ba272', areaColor: 'rgba(59, 162, 114, 0.2)' }
    ];

    const seriesData = satellites.map((sat, index) => ({
      name: sat.name,
      value: [
        sat.capabilities?.spatialResolution || 75 + Math.random() * 20,
        sat.capabilities?.temporalResolution || 70 + Math.random() * 25,
        sat.capabilities?.spectralResolution || 65 + Math.random() * 30,
        sat.capabilities?.coverage || 80 + Math.random() * 15,
        sat.capabilities?.dataQuality || 75 + Math.random() * 20,
        sat.capabilities?.realtime || 60 + Math.random() * 35
      ],
      lineStyle: {
        color: colorScheme[index % colorScheme.length].color,
        width: 2
      },
      areaStyle: {
        color: colorScheme[index % colorScheme.length].areaColor
      },
      symbol: 'circle',
      symbolSize: 6
    }));

    const option = {
      title: {
        text: '卫星综合能力对比分析',
        left: 'center',
        top: 0,
        textStyle: {
          fontSize: 18,
          fontWeight: 'bold',
          color: '#1F2937'
        }
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#E5E7EB',
        borderWidth: 1,
        textStyle: { color: '#1F2937' },
        formatter: function(params) {
          const values = params.value;
          let result = `<div class="font-semibold mb-2">${params.name}</div>`;
          indicators.forEach((ind, idx) => {
            result += `<div class="flex justify-between gap-4">
              <span>${ind.name}:</span>
              <span class="font-medium">${values[idx].toFixed(1)}</span>
            </div>`;
          });
          return result;
        }
      },
      legend: {
        data: seriesData.map(s => s.name),
        bottom: 0,
        left: 'center',
        orient: 'horizontal',
        itemGap: 15,
        textStyle: {
          fontSize: 12,
          color: '#4B5563'
        },
        icon: 'circle',
        itemWidth: 10,
        itemHeight: 10
      },
      radar: {
        center: ['50%', '50%'],
        radius: '65%',
        indicator: indicators,
        shape: 'polygon',
        splitNumber: 5,
        axisName: {
          formatter: '{value}',
          color: '#6B7280',
          fontSize: 12
        },
        splitLine: {
          lineStyle: {
            color: '#E5E7EB'
          }
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: ['rgba(255, 255, 255, 0)', 'rgba(249, 250, 251, 0.5)']
          }
        },
        axisLine: {
          lineStyle: {
            color: '#E5E7EB'
          }
        }
      },
      series: [{
        type: 'radar',
        data: seriesData,
        emphasis: {
          lineStyle: {
            width: 3
          },
          areaStyle: {
            opacity: 0.5
          }
        }
      }]
    };

    chart.setOption(option);

    const handleResize = () => {
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current);
      }

      resizeTimeoutRef.current = setTimeout(() => {
        chart.resize();
      }, 100);
    };
    
    window.addEventListener('resize', handleResize);

    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });

    if (chartRef.current) {
      resizeObserver.observe(chartRef.current);
    }

    return () => {
      chart.dispose();
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current);
      }
    };
  }, [data, chartInstanceRef]);

  return (
    <div className="bg-white rounded-lg border shadow-sm p-4">
      <div ref={chartRef} style={{ width: '100%', height: `${height}px` }} />
    </div>
  );
};

// 备用图表组件
const SatelliteChartsBackup = ({ data, height }) => {
  console.log('🔄 使用备用图表组件');

  if (!data || !data.satellites || data.satellites.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 text-center" style={{ height: `${height}px` }}>
        <div className="flex flex-col items-center justify-center h-full">
          <div className="text-4xl mb-4">📊</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">暂无图表数据</h3>
          <p className="text-gray-500">等待卫星方案生成后显示可视化图表</p>
        </div>
      </div>
    );
  }

  // 简化的备用展示
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">卫星能力对比</h3>
        <div className="space-y-4">
          {data.satellites.slice(0, 5).map((sat, index) => (
            <div key={index} className="border rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-3">{sat.name}</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">空间分辨率:</span>
                  <div className="mt-1 bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${sat.capabilities?.spatialResolution || 70}%` }}></div>
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">时间分辨率:</span>
                  <div className="mt-1 bg-gray-200 rounded-full h-2">
                    <div className="bg-green-500 h-2 rounded-full" style={{ width: `${sat.capabilities?.temporalResolution || 70}%` }}></div>
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">光谱分辨率:</span>
                  <div className="mt-1 bg-gray-200 rounded-full h-2">
                    <div className="bg-purple-500 h-2 rounded-full" style={{ width: `${sat.capabilities?.spectralResolution || 70}%` }}></div>
                  </div>
                </div>
                <div>
                  <span className="text-gray-600">覆盖范围:</span>
                  <div className="mt-1 bg-gray-200 rounded-full h-2">
                    <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${sat.capabilities?.coverage || 80}%` }}></div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// 生成默认数据
function generateDefaultData() {
  return {
    satellites: [
      {
        name: '高分一号',
        country: '中国',
        importance: 8,
        capabilities: {
          spatialResolution: 85,
          temporalResolution: 75,
          spectralResolution: 80,
          coverage: 85,
          dataQuality: 88,
          realtime: 70
        }
      },
      {
        name: 'Sentinel-2',
        country: '欧洲',
        importance: 9,
        capabilities: {
          spatialResolution: 80,
          temporalResolution: 85,
          spectralResolution: 92,
          coverage: 95,
          dataQuality: 90,
          realtime: 75
        }
      },
      {
        name: 'Landsat-8',
        country: '美国',
        importance: 7,
        capabilities: {
          spatialResolution: 75,
          temporalResolution: 65,
          spectralResolution: 88,
          coverage: 90,
          dataQuality: 85,
          realtime: 65
        }
      }
    ],
    collaborations: [],
    pattern_analysis: {},
    summary_stats: {
      total_satellites: 3,
      total_collaborations: 2,
      avg_collaboration_frequency: 17.5,
      network_density: 0.67
    },
    recommendations: [
      '🛰️ 高分一号在空间分辨率方面表现优秀，适合精细观测',
      '📡 Sentinel-2的光谱分辨率最高，适合多光谱分析',
      '🌍 Landsat-8覆盖范围广，适合大尺度监测'
    ]
  };
}

export default SatelliteCharts;