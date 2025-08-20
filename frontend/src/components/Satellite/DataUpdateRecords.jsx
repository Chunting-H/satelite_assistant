// components/Satellite/DataUpdateRecords.jsx - 数据更新记录可视化组件
import React, { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { 
  getCrawlLogs, 
  getCrawlStatistics, 
  startCrawlJob, 
  getCrawlJobStatus,
  manualCrawl 
} from '../../services/api';

const DataUpdateRecords = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [crawlLogs, setCrawlLogs] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [crawlJobId, setCrawlJobId] = useState(null);
  const [crawlJobStatus, setCrawlJobStatus] = useState(null);
  const [refreshInterval, setRefreshInterval] = useState(null);
  
  // ECharts图表引用
  const dailyChartRef = useRef(null);
  const siteChartRef = useRef(null);
  const trendChartRef = useRef(null);
  
  // 组件挂载时加载数据
  useEffect(() => {
    loadInitialData();
    return () => {
      // 清理定时器
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [logsResult, statsResult] = await Promise.all([
        getCrawlLogs(50),
        getCrawlStatistics(30)
      ]);
      
      if (!logsResult.error) {
        setCrawlLogs(logsResult.logs || []);
      }
      
      if (!statsResult.error) {
        setStatistics(statsResult);
      }
    } catch (error) {
      console.error('加载数据失败:', error);
    }
    setLoading(false);
  };

  // 渲染图表
  useEffect(() => {
    if (statistics && activeTab === 'overview') {
      renderCharts();
    }
  }, [statistics, activeTab]);

  const renderCharts = () => {
    // 每日数据图表
    if (dailyChartRef.current && statistics.daily_stats) {
      const dailyChart = echarts.init(dailyChartRef.current);
      
      const dailyData = statistics.daily_stats.slice(-7); // 最近7天
      const dates = dailyData.map(item => item.date);
      const newSatellites = dailyData.map(item => item.new_satellites);
      const crawlCounts = dailyData.map(item => item.crawls);
      
      const dailyOption = {
        title: {
          text: '最近7天数据获取情况',
          textStyle: { fontSize: 14 }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' }
        },
        legend: {
          data: ['新增卫星', '爬取次数']
        },
        xAxis: {
          type: 'category',
          data: dates,
          axisLabel: {
            formatter: function(value) {
              return value.split('-')[2]; // 只显示日期
            }
          }
        },
        yAxis: [
          {
            type: 'value',
            name: '新增卫星数',
            position: 'left'
          },
          {
            type: 'value',
            name: '爬取次数',
            position: 'right'
          }
        ],
        series: [
          {
            name: '新增卫星',
            type: 'bar',
            data: newSatellites,
            itemStyle: { color: '#3b82f6' }
          },
          {
            name: '爬取次数',
            type: 'line',
            yAxisIndex: 1,
            data: crawlCounts,
            itemStyle: { color: '#10b981' }
          }
        ]
      };
      
      dailyChart.setOption(dailyOption);
    }

    // 来源网站统计图表
    if (siteChartRef.current && statistics.site_stats) {
      const siteChart = echarts.init(siteChartRef.current);
      
      const siteData = statistics.site_stats.map(item => ({
        value: item.new_satellites,
        name: item.site
      }));
      
      const siteOption = {
        title: {
          text: '数据来源分布',
          textStyle: { fontSize: 14 }
        },
        tooltip: {
          trigger: 'item'
        },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          data: siteData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          label: {
            show: true,
            formatter: '{b}: {c}个'
          }
        }]
      };
      
      siteChart.setOption(siteOption);
    }

    // 趋势图表
    if (trendChartRef.current && statistics.daily_stats) {
      const trendChart = echarts.init(trendChartRef.current);
      
      const trendData = statistics.daily_stats.slice(-30); // 最近30天
      const dates = trendData.map(item => item.date);
      const cumulative = trendData.reduce((acc, item, index) => {
        const prev = index > 0 ? acc[index - 1] : 0;
        acc.push(prev + item.new_satellites);
        return acc;
      }, []);
      
      const trendOption = {
        title: {
          text: '累计新增卫星趋势',
          textStyle: { fontSize: 14 }
        },
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: dates,
          axisLabel: {
            formatter: function(value) {
              return value.split('-').slice(1).join('/'); // MM/DD格式
            }
          }
        },
        yAxis: {
          type: 'value',
          name: '累计卫星数'
        },
        series: [{
          name: '累计新增',
          type: 'line',
          data: cumulative,
          smooth: true,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.1)' }
            ])
          },
          itemStyle: { color: '#3b82f6' }
        }]
      };
      
      trendChart.setOption(trendOption);
    }
  };

  // 手动触发爬取
  const handleManualCrawl = async () => {
    try {
      setLoading(true);
      const result = await manualCrawl(["Gunter's Space Page"], [], 5);
      
      if (result.success !== false) {
        setCrawlJobId(result.job_id);
        
        // 开始轮询任务状态
        const interval = setInterval(async () => {
          const status = await getCrawlJobStatus(result.job_id);
          setCrawlJobStatus(status);
          
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(interval);
            setRefreshInterval(null);
            
            // 刷新数据
            setTimeout(() => {
              loadInitialData();
            }, 1000);
          }
        }, 2000);
        
        setRefreshInterval(interval);
      }
    } catch (error) {
      console.error('手动爬取失败:', error);
    }
    setLoading(false);
  };

  // 格式化时间
  const formatTime = (timeStr) => {
    if (!timeStr) return '未知';
    return new Date(timeStr).toLocaleString('zh-CN');
  };

  // 获取状态颜色
  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'text-green-600 bg-green-100';
      case 'failed': return 'text-red-600 bg-red-100';
      case 'pending': return 'text-yellow-600 bg-yellow-100';
      case 'running': return 'text-blue-600 bg-blue-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-5/6 flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">数据更新记录</h2>
              <p className="text-sm text-gray-600">卫星数据爬取统计与监控</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={handleManualCrawl}
              disabled={loading || crawlJobId}
              className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {loading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              )}
              <span>手动更新</span>
            </button>
            
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 transition-colors p-2"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* 任务状态提示 */}
        {crawlJobStatus && (
          <div className="mx-6 mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium text-blue-900">当前任务状态:</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(crawlJobStatus.status)}`}>
                  {crawlJobStatus.status}
                </span>
              </div>
              {crawlJobStatus.results && (
                <div className="text-sm text-blue-700">
                  新增卫星: {crawlJobStatus.results.new_satellites} 个
                </div>
              )}
            </div>
          </div>
        )}

        {/* 标签导航 */}
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            统计概览
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
              activeTab === 'logs'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            详细日志
          </button>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* 概览卡片 */}
              {statistics && (
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg p-4 text-white">
                    <div className="text-2xl font-bold">{statistics.total_crawls}</div>
                    <div className="text-blue-100">总爬取次数</div>
                  </div>
                  <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-lg p-4 text-white">
                    <div className="text-2xl font-bold">{statistics.total_new_satellites}</div>
                    <div className="text-green-100">新增卫星总数</div>
                  </div>
                  <div className="bg-gradient-to-r from-yellow-500 to-yellow-600 rounded-lg p-4 text-white">
                    <div className="text-2xl font-bold">{statistics.total_failed}</div>
                    <div className="text-yellow-100">失败次数</div>
                  </div>
                  <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg p-4 text-white">
                    <div className="text-2xl font-bold">
                      {statistics.total_crawls > 0 ? ((1-(statistics.total_failed / statistics.total_crawls)) * 100).toFixed(1) : 0}%
                    </div>
                    <div className="text-purple-100">成功率</div>
                  </div>
                </div>
              )}

              {/* 图表区域 */}
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <div ref={dailyChartRef} style={{ height: '300px' }}></div>
                </div>
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <div ref={siteChartRef} style={{ height: '300px' }}></div>
                </div>
              </div>

              {/* 趋势图 */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <div ref={trendChartRef} style={{ height: '300px' }}></div>
              </div>
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="space-y-4">
              {crawlLogs.length === 0 ? (
                <div className="text-center py-12">
                  <div className="text-4xl mb-4">📊</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">暂无爬取记录</h3>
                  <p className="text-gray-500">点击"手动更新"开始第一次数据爬取</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {crawlLogs.map((log, index) => (
                    <div key={index} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                          <span className="font-medium text-gray-900">
                            {formatTime(log.crawlTime)}
                          </span>
                          <span className="text-sm text-gray-500">
                            来源: {log.targetSites?.join(', ') || '未知'}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500">
                          耗时: {log.executionTime?.toFixed(1) || 0}秒
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">新增:</span>
                          <span className="ml-1 font-medium text-green-600">{log.newDataCount || 0}个</span>
                        </div>
                        <div>
                          <span className="text-gray-600">更新:</span>
                          <span className="ml-1 font-medium text-blue-600">{log.updatedDataCount || 0}个</span>
                        </div>
                        <div>
                          <span className="text-gray-600">失败:</span>
                          <span className="ml-1 font-medium text-red-600">{log.failedCount || 0}个</span>
                        </div>
                        <div>
                          <span className="text-gray-600">总处理:</span>
                          <span className="ml-1 font-medium text-gray-900">{log.totalProcessed || 0}个</span>
                        </div>
                      </div>
                      
                      {log.dataList && log.dataList.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-100">
                          <div className="text-sm text-gray-600 mb-2">本次新增卫星:</div>
                          <div className="flex flex-wrap gap-2">
                            {log.dataList.slice(0, 5).map((satellite, idx) => (
                              <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                                {satellite}
                              </span>
                            ))}
                            {log.dataList.length > 5 && (
                              <span className="text-xs text-gray-500">
                                +{log.dataList.length - 5} 更多...
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {log.failReasons && log.failReasons.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-100">
                          <div className="text-sm text-red-600 mb-2">失败原因:</div>
                          <div className="text-xs text-red-500">
                            {log.failReasons.join(', ')}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DataUpdateRecords;
