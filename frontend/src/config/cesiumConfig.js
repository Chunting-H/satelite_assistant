// src/config/cesiumConfig.js

// Cesium Ion 访问令牌
export const CESIUM_ION_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJhYTJjNjM4Zi1hOTYxLTQxNTItODFlMS05YTEzMzU4ODk5MzIiLCJpZCI6MjAzNTE1LCJpYXQiOjE3MTEwMTAzMDV9.1zfBCCYAOJdwhmYScXFr8DhndCV2JaNhWwLBT29xZ5A';

// DeepSeek API 配置
export const DEEPSEEK_API_CONFIG = {
  url: 'https://api.deepseek.com/v1/chat/completions',
  apiKey: 'sk-40059d9b6b6943319120ad243c2dd0e4',
  model: 'deepseek-chat'
};

// CZML 文件路径配置
export const CZML_CONFIG = {
  // 确保将 wx.czml 文件放在 public 目录下
  defaultCzmlPath: '/wx.czml'
};

// 卫星图标 (Base64编码的图片)
export const SATELLITE_ICON = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADJSURBVDhPnZHRDcMgEEMZjVEYpaNklIzSEfLfD4qNnXAJSFWfhO7w2Zc0Tf9QG2rXrEzSUeZLOGm47WoH95x3Hl3jEgilvDgsOQUTqsNl68ezEwn1vae6lceSEEYvvWNT/Rxc4CXQNGadho1NXoJ+9iaqc2xi2xbt23PJCDIB6TQjOC6Bho/sDy3fBQT8PrVhibU7yBFcEPaRxOoeTwbwByCOYf9VGp1BYI1BA+EeHhmfzKbBoJEQwn1yzUZtyspIQUha85MpkNIXB7GizqDEECsAAAAASUVORK5CYII=";

// 卫星轨道参数范围
export const ORBIT_PARAMS = {
  inclination: { min: 45, max: 75 }, // 倾角范围 (度)
  semiMajorAxis: { min: 7000000, max: 9000000 }, // 半长轴范围 (米)
  eccentricity: 0.001 // 离心率 (接近圆形轨道)
};

// 常见卫星列表
export const COMMON_SATELLITES = [
  // 中国卫星
  '风云一号', '风云二号', '风云三号', '风云四号',
  '高分一号', '高分二号', '高分三号', '高分四号', '高分五号', '高分六号', '高分七号',
  'GF-1', 'GF-2', 'GF-3', 'GF-4', 'GF-5', 'GF-6', 'GF-7',
  '海洋一号', '海洋二号', '资源一号', '资源二号', '资源三号',
  '环境一号', '实践九号', '遥感系列',
  // 国际卫星
  'Landsat-8', 'Landsat-9', 'Sentinel-1', 'Sentinel-2', 'Sentinel-3',
  '哨兵-1号', '哨兵-2号', '哨兵-3号',
  'MODIS', 'WorldView', 'QuickBird', 'IKONOS', 'Pleiades',
  'SPOT', 'TerraSAR-X', 'RADARSAT', 'ALOS', 'Himawari',
  '葵花8号', '葵花9号', 'GOES', 'Meteosat', 'NOAA'
];

// 卫星名称映射（处理同一卫星的不同名称）
export const SATELLITE_NAME_MAPPING = {
  'GF-1': '高分一号',
  'GF-2': '高分二号',
  'GF-3': '高分三号',
  'GF-4': '高分四号',
  'GF-5': '高分五号',
  'GF-6': '高分六号',
  'GF-7': '高分七号',
  'Sentinel-1': '哨兵-1号',
  'Sentinel-2': '哨兵-2号',
  'Sentinel-3': '哨兵-3号',
  'Himawari': '葵花8号'
};