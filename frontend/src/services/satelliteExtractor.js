// src/services/satelliteExtractor.js - 优化版本：只从卫星组成部分提取
import axios from 'axios';
import { findSatelliteInfo } from '../config/satelliteDatabase';
// 本地卫星列表 - 添加 PlanetScope
const COMMON_SATELLITES = [
  // // 中国卫星
  // '风云一号', '风云二号', '风云三号', '风云四号',
  // '高分一号', '高分二号', '高分三号', '高分四号', '高分五号', '高分六号', '高分七号',
  // 'GF-1', 'GF-2', 'GF-3', 'GF-4', 'GF-5', 'GF-6', 'GF-7',
  // '海洋一号', '海洋二号', '资源一号', '资源二号', '资源三号',
  // '环境一号', '实践九号', '遥感系列',

  // // 国际卫星
  // 'Landsat-8', 'Landsat-9', 'Sentinel-1', 'Sentinel-2', 'Sentinel-3',
  // '哨兵-1号', '哨兵-2号', '哨兵-3号',
  // 'MODIS', 'WorldView', 'QuickBird', 'IKONOS', 'Pleiades',
  // 'SPOT', 'TerraSAR-X', 'RADARSAT', 'ALOS', 'Himawari',
  // '葵花8号', '葵花9号', 'GOES', 'Meteosat', 'NOAA',

  // // 🆕 新增商业小卫星星座
  // 'PlanetScope', 'Planet', 'Dove', 'SkySat', 'RapidEye',
  // 'BlackSky', 'ICEYE', 'Capella', 'SuperView', 'Jilin-1',
  // '吉林一号'
    // 中国卫星
  '风云一号', '风云二号', '风云三号', '风云四号',
  '高分一号', '高分二号', '高分三号', '高分四号', '高分五号', '高分六号', '高分七号','高分八号','高分九号','高分十号','高分十一号','高分十二号','高分十三号','高分十四号',
  'GF-1', 'GF-2', 'GF-3', 'GF-4', 'GF-5', 'GF-6', 'GF-7',
  '海洋一号', '海洋二号', '资源一号', '资源二号','yaogan-11','海洋三号','资源三号',
  '环境一号','HJ-1A',
  // 国际卫星
  'Landsat-8', 'Landsat-9', 'Sentinel-1', 'Sentinel-2', 'Sentinel-3','Sentinel-5P','Sentinel-6','Landsat-8', 'Landsat-9','Landsat-1', 'Landsat-2','Landsat-3', 'Landsat-4','Landsat-5', 'Landsat-6','Landsat-7', 'Landsat 8', 'Landsat 9', 'Sentinel 1', 'Sentinel 2', 'Sentinel 3','Sentinel 6','Landsat 4',
  '哨兵-1号', '哨兵-2号', '哨兵-3号','ECOSTRESS',
  'STARLETTE', 'LAGEOS-1', 'LAGEOS 1','AJISAI','LAGEOS 2','STELLA', 'USA 105', 'USA 118', 'FORTE', 'USA 139', 'NOAA 15','TERRA', 'AQUA', 'AURA', 'ODIN', 'SCISAT 1',
  'PROBA-1', 'XMM-NEWTON', 'BEIJING 1','EROS B','KOMPSAT-2','HINODE','DMSP F17', 'SAR-LUPE 1','TERRASAR-X','COSMO-SKYMED 1','WORLDVIEW-1','RADARSAT-2','CARTOSAT-2A',
  'GEOEYE 1','THEOS','COSMO-SKYMED 2','COSMO-SKYMED 3','CBERS-4',
  // 第一轮添加卫星
'TANDEM-X', 'OFEQ 9', 'CARTOSAT-2B', 'AISSAT 1', 'ALSAT 2A',
'YAOGAN-10', '天绘一号', 'USA 215', 'YAOGAN-11',
'实践六号04A', 'SHIJIAN-6 04B', 'COSMO-SKYMED 4',
'WORLDVIEW-2', 'DMSP F18', 'SMOS', 'PROBA-2', 'COSMOS 2455', 'WORLDVIEW-1','WORLDVIEW-4','WorldView-4','WorldView-1','WorldView-2','WORLDVIEW-3','WorldView-3',
'IGS 5A', 'YAOGAN-7', 'YAOGAN-8', 'SDO', 'YAOGAN-9A',
'YAOGAN-9B', 'YAOGAN-9C', 'CRYOSAT-2',
//k73
// 美国卫星
'USA 223', 'USA 224','USA 217','USA 229','USA 230','USA 234','USA 237','STPSAT-2','SBIRS GEO-1','QUICKBIRD 1','QUICKBIRD 2','GEOEYE 1',
// 中国卫星
'HAIYANG-2A', '海洋二号A', 'ZY 1-02C', '资源一号02', 'ZY 3-1', 'YAOGAN-15',
'资源三号01', 'SJ-11-02', '实践十一号02','CHUANGXIN 1-03','SHIYAN 4','YAOGAN-12','YAOGAN-13','YAOGAN-14','天绘一号02','风云二号F',
// 欧洲卫星
'PLEIADES 1A', 'PLEIADES 1B', 'SPOT 6', 'METEOSAT-10','SPOT 1','SPOT 2','SPOT 3','SPOT 4','SPOT 5','SPOT 7',
// 印度卫星
'RESOURCESAT-2', 'YOUTHSAT','JUGNU','SRMSAT','GSAT-12','RISAT-1','MEGHA-TROPIQUES',
// 日本卫星
'IGS 6A','IGS 7A','GCOM-W1','向日葵1号','向日葵2号','向日葵3号','向日葵4号','向日葵5号','向日葵6号','向日葵7号','向日葵8号','向日葵9号','ALOS-2',
// 韩国卫星
'ARIRANG-3', 'ARIRANG-5',
// 其他国家卫星
'SUOMI NPP','METOP-B','PROBA-V','SWARM A','SARAL','SKYSAT-A','ELISA W11','ELISA E24','ELISA W23','ELISA E12','X-SAT','ELEKTRO-L 1','SAC-D','NIGERIASAT-2','RASAT',
'SICH-2','LARES','NIGERIASAT-X', 'SSOT',

//k74
// 中国卫星
'遥感二十号01A', '遥感二十号01B', '遥感二十号01C', '遥感二十一号', '遥感二十二号',
'遥感二十三号', '遥感二十四号', '遥感二十五号01A', '遥感二十五号01B', '遥感二十五号01C',
'遥感二十六号', '遥感二十七号', '遥感二十八号', '遥感二十九号', '遥感三十号',
'风云二号G', '高分八号', '高分九号', '吉林一号', '天拓二号', '天绘一号','天绘二号','天绘四号',
'CBERS 4', '创新一号04',

// 美国卫星
'GPM-CORE', 'OCO 2', 'WORLDVIEW-3', 'JASON-3', 'DSCOVR', 'MMS 1', 'MMS 2',
'MMS 3', 'MMS 4', 'USA 250', 'USA 259', 'USA 264', 'USA 267',

// 日本卫星
'ALOS-2', 'UNIFORM 1', 'RISING 2', 'HODOYOSHI-3', 'HODOYOSHI-4',
'HIMAWARI-8', 'ASNARO', 'HODOYOSHI-1', 'CHUBUSAT-1', 'QSAT-EOS',
'TSUBAME', 'IGS 9A', 'IGS O-5',

// 欧洲卫星
'SENTINEL-1A', 'SENTINEL-2A', 'SENTINEL-3A', 'SENTINEL-1B',

// 其他国家卫星
'DMSP 5D-3 F19', 'OFEQ 10', 'EGYPTSAT 2', 'KAZEOSAT 1', 'KAZEOSAT 2',
'DEIMOS-2', 'BUGSAT-1', 'TABLETSAT-AURORA', 'TIGRISAT', 'LEMUR-1',
'SPOT 7', 'METEOR-M 2', 'MKA-PN 2', 'SKYSAT-B', 'AISSAT 2',
'TECHDEMOSAT-1', 'RESURS-P 2', 'COSMOS 2502', 'COSMOS 2503',
'COSMOS 2506', 'COSMOS 2510', 'COSMOS 2511', 'COSMOS 2515',
'ELEKTRO-L 2', 'KOMPSAT-3A', 'DMC3-FM1', 'DMC3-FM2', 'DMC3-FM3',
'CARBONITE 1', 'LAPAN-A2', 'LEMUR-2-JOEL', 'LEMUR-2-CHRIS',
'LEMUR-2-JEROEN', 'LEMUR-2-PETER', 'LQSAT', 'LINGQIAO VIDEO A',
'LINGQIAO VIDEO B', 'TELEOS-1', 'KENT RIDGE 1', 'VELOX-CI',
'KMS 4', 'RESURS-P 3', 'KONDOR-E', 'DIWATA-1'
];

// 增强卫星名称映射（避免重复）
const SATELLITE_MAPPING = {
// 高分系列
'gf-1': '高分一号',
'gf-2': '高分二号',
'gf-3': '高分三号',
'gf-4': '高分四号',
'gf-5': '高分五号',
'gf-6': '高分六号',
'gf-7': '高分七号',
'gf-8': '高分八号',
'gf-9': '高分九号',
'gf-10': '高分十号',
'gf-11': '高分十一号',
'gf-12': '高分十二号',
'gf-13': '高分十三号',
'gf-14': '高分十四号',
'gf1': '高分一号',
'gf2': '高分二号',
'gf3': '高分三号',
'gf4': '高分四号',
'gf5': '高分五号',
'gf6': '高分六号',
'gf7': '高分七号',
'gf8': '高分八号',
'gf9': '高分九号',
'gf10': '高分十号',
'gf11': '高分十一号',
'gf12': '高分十二号',
'gf13': '高分十三号',
'gf14': '高分十四号',

// 风云系列
'fy-1': '风云一号',
'fy-2': '风云二号',
'fy-3': '风云三号',
'fy-4': '风云四号',
'fy1': '风云一号',
'fy2': '风云二号',
'fy3': '风云三号',
'fy4': '风云四号',
'fy-2f': '风云二号F',
'fy-2g': '风云二号G',
'fy2f': '风云二号F',
'fy2g': '风云二号G',

// 哨兵系列
'sentinel-1': '哨兵-1号',
'sentinel-2': '哨兵-2号',
'sentinel-3': '哨兵-3号',
'sentinel-5p': 'Sentinel-5P',
'sentinel-6': '哨兵-6号',
'sentinel1': '哨兵-1号',
'sentinel2': '哨兵-2号',
'sentinel3': '哨兵-3号',
'sentinel5p': 'Sentinel-5P',
'sentinel6': '哨兵-6号',
'哨兵1号': '哨兵-1号',
'哨兵2号': '哨兵-2号',
'哨兵3号': '哨兵-3号',
'sentinel-1a': 'Sentinel-1A',
'sentinel-1b': 'Sentinel-1B',
'sentinel-2a': 'Sentinel-2A',
'sentinel-2b': 'Sentinel-2B',
'sentinel-3a': 'Sentinel-3A',

// Landsat系列
'landsat-1': 'Landsat-1',
'landsat-2': 'Landsat-2',
'landsat-3': 'Landsat-3',
'landsat-4': 'Landsat-4',
'landsat-5': 'Landsat-5',
'landsat-6': 'Landsat-6',
'landsat-7': 'Landsat-7',
'landsat-8': 'Landsat-8',
'landsat-9': 'Landsat-9',
'landsat1': 'Landsat-1',
'landsat2': 'Landsat-2',
'landsat3': 'Landsat-3',
'landsat4': 'Landsat-4',
'landsat5': 'Landsat-5',
'landsat6': 'Landsat-6',
'landsat7': 'Landsat-7',
'landsat8': 'Landsat-8',
'landsat9': 'Landsat-9',

// 海洋系列
'hy-1': '海洋一号',
'hy-2': '海洋二号',
'hy-3': '海洋三号',
'hy1': '海洋一号',
'hy2': '海洋二号',
'hy3': '海洋三号',
'hy-2a': '海洋二号A',
'haiyang-2a': '海洋二号A',

// 资源系列
'zy-1': '资源一号',
'zy-2': '资源二号',
'zy-3': '资源三号',
'zy1': '资源一号',
'zy2': '资源二号',
'zy3': '资源三号',
'zy-1-02c': '资源一号02C',
'zy-3-1': '资源三号01',
'zy1-02c': '资源一号02C',
'zy3-1': '资源三号01',

// 环境系列
'hj-1': '环境一号',
'hj1': '环境一号',

// 遥感系列
'yaogan-7': '遥感七号',
'yaogan-8': '遥感八号',
'yaogan-9': '遥感九号',
'yaogan-10': '遥感十号',
'yaogan-11': '遥感十一号',
'yaogan-12': '遥感十二号',
'yaogan-13': '遥感十三号',
'yaogan-14': '遥感十四号',
'yaogan-15': '遥感十五号',
'yaogan-20': '遥感二十号',
'yaogan-21': '遥感二十一号',
'yaogan-22': '遥感二十二号',
'yaogan-23': '遥感二十三号',
'yaogan-24': '遥感二十四号',
'yaogan-25': '遥感二十五号',
'yaogan-26': '遥感二十六号',
'yaogan-27': '遥感二十七号',
'yaogan-28': '遥感二十八号',
'yaogan-29': '遥感二十九号',
'yaogan-30': '遥感三十号',

// 天绘系列
'th-1': '天绘一号',
'th-2': '天绘二号',
'th-4': '天绘四号',
'th1': '天绘一号',
'th2': '天绘二号',
'th4': '天绘四号',
'th-1-02': '天绘一号02',

// 实践系列
'sj-6-04a': '实践六号04A',
'sj-11-02': '实践十一号02',
'shijian-6-04b': 'SHIJIAN-6 04B',

// WorldView系列
'worldview-1': 'WorldView-1',
'worldview-2': 'WorldView-2',
'worldview-3': 'WorldView-3',
'worldview-4': 'WorldView-4',
'worldview1': 'WorldView-1',
'worldview2': 'WorldView-2',
'worldview3': 'WorldView-3',
'worldview4': 'WorldView-4',
'wv-1': 'WorldView-1',
'wv-2': 'WorldView-2',
'wv-3': 'WorldView-3',
'wv-4': 'WorldView-4',

// 日本卫星
'himawari': '向日葵8号',
'himawari-8': '向日葵8号',
'himawari-9': '向日葵9号',
'himawari8': '向日葵8号',
'himawari9': '向日葵9号',
'向日葵8号': '向日葵8号',
'向日葵9号': '向日葵9号',

// 商业小卫星星座
'skysat': 'SkySat',
'skysat-a': 'SkySat',
'skysat-b': 'SkySat',
'jilin-1': '吉林一号',
'jilin1': '吉林一号',
'jl-1': '吉林一号',
'jl1': '吉林一号',

// SPOT系列
'spot-1': 'SPOT 1',
'spot-2': 'SPOT 2',
'spot-3': 'SPOT 3',
'spot-4': 'SPOT 4',
'spot-5': 'SPOT 5',
'spot-6': 'SPOT 6',
'spot-7': 'SPOT 7',
'spot1': 'SPOT 1',
'spot2': 'SPOT 2',
'spot3': 'SPOT 3',
'spot4': 'SPOT 4',
'spot5': 'SPOT 5',
'spot6': 'SPOT 6',
'spot7': 'SPOT 7',

// Pleiades系列
'pleiades-1a': 'PLEIADES 1A',
'pleiades-1b': 'PLEIADES 1B',
'pleiades1a': 'PLEIADES 1A',
'pleiades1b': 'PLEIADES 1B',

// COSMO-SkyMed系列
'cosmo-skymed-1': 'COSMO-SKYMED 1',
'cosmo-skymed-2': 'COSMO-SKYMED 2',
'cosmo-skymed-3': 'COSMO-SKYMED 3',
'cosmo-skymed-4': 'COSMO-SKYMED 4',
'cosmoskymed1': 'COSMO-SKYMED 1',
'cosmoskymed2': 'COSMO-SKYMED 2',
'cosmoskymed3': 'COSMO-SKYMED 3',
'cosmoskymed4': 'COSMO-SKYMED 4',

// QuickBird系列
'quickbird-1': 'QUICKBIRD 1',
'quickbird-2': 'QUICKBIRD 2',
'quickbird1': 'QUICKBIRD 1',
'quickbird2': 'QUICKBIRD 2',

// 其他重要卫星
'terrasar-x': 'TerraSAR-X',
'terrasarx': 'TerraSAR-X',
'tandem-x': 'TANDEM-X',
'tandemx': 'TANDEM-X',
'radarsat-2': 'RADARSAT-2',
'radarsat2': 'RADARSAT-2',
'alos-2': 'ALOS-2',
'alos2': 'ALOS-2',
'gcom-w1': 'GCOM-W1',
'gcomw1': 'GCOM-W1',
'suomi-npp': 'SUOMI NPP',
'suominpp': 'SUOMI NPP',
'gpm-core': 'GPM-CORE',
'gpmcore': 'GPM-CORE',
'oco-2': 'OCO 2',
'oco2': 'OCO 2',
'jason-3': 'JASON-3',
'jason3': 'JASON-3',

// 印度卫星
'resourcesat-2': 'RESOURCESAT-2',
'resourcesat2': 'RESOURCESAT-2',
'cartosat-2a': 'CARTOSAT-2A',
'cartosat-2b': 'CARTOSAT-2B',
'cartosat2a': 'CARTOSAT-2A',
'cartosat2b': 'CARTOSAT-2B',
'risat-1': 'RISAT-1',
'risat1': 'RISAT-1',

// 韩国卫星
'kompsat-2': 'KOMPSAT-2',
'kompsat-3': 'KOMPSAT-3',
'kompsat-3a': 'KOMPSAT-3A',
'kompsat2': 'KOMPSAT-2',
'kompsat3': 'KOMPSAT-3',
'kompsat3a': 'KOMPSAT-3A',
'arirang-3': 'ARIRANG-3',
'arirang-5': 'ARIRANG-5',
'arirang3': 'ARIRANG-3',
'arirang5': 'ARIRANG-5',

// 欧洲卫星
'meteosat-10': 'METEOSAT-10',
'meteosat10': 'METEOSAT-10',
'metop-b': 'METOP-B',
'metopb': 'METOP-B',
'proba-1': 'PROBA-1',
'proba-2': 'PROBA-2',
'proba-v': 'PROBA-V',
'proba1': 'PROBA-1',
'proba2': 'PROBA-2',
'probav': 'PROBA-V',

// 其他卫星系列
'dmsp-f17': 'DMSP F17',
'dmsp-f18': 'DMSP F18',
'dmsp-f19': 'DMSP 5D-3 F19',
'dmc3-fm1': 'DMC3-FM1',
'dmc3-fm2': 'DMC3-FM2',
'dmc3-fm3': 'DMC3-FM3',

// CBERS系列
'cbers-4': 'CBERS 4',
'cbers4': 'CBERS 4',

// 创新系列
'cx-1-03': '创新一号03',
'cx-1-04': '创新一号04',
'chuangxin-1-03': 'CHUANGXIN 1-03',

// 电磁监测系列
'zhangheng-1': '张衡一号',
'zhangheng1': '张衡一号',

// 北斗系列（如果需要）
'beidou': '北斗',
'bd': '北斗',

// 通信卫星系列
'tdrs': 'TDRS',
'intelsat': 'Intelsat',

// 气象卫星
'goes': 'GOES',
'noaa': 'NOAA',
'noaa-15': 'NOAA 15',
'noaa15': 'NOAA 15',

// 科学卫星
'terra': 'TERRA',
'aqua': 'AQUA',
'aura': 'AURA',
'calipso': 'CALIPSO',
'cloudsat': 'CloudSat',

// 军事侦察卫星
'igs-5a': 'IGS 5A',
'igs-6a': 'IGS 6A',
'igs-7a': 'IGS 7A',
'igs-9a': 'IGS 9A',
'igs-o-5': 'IGS O-5',

// 以色列卫星
'ofeq-9': 'OFEQ 9',
'ofeq-10': 'OFEQ 10',
'ofeq9': 'OFEQ 9',
'ofeq10': 'OFEQ 10',

// 埃及卫星
'egyptsat-2': 'EGYPTSAT 2',
'egyptsat2': 'EGYPTSAT 2',

// 其他国家卫星
'deimos-2': 'DEIMOS-2',
'deimos2': 'DEIMOS-2',
'kazeosat-1': 'KAZEOSAT 1',
'kazeosat-2': 'KAZEOSAT 2',
'kazeosat1': 'KAZEOSAT 1',
'kazeosat2': 'KAZEOSAT 2',
'alsat-2a': 'ALSAT 2A',
'alsat2a': 'ALSAT 2A',
'nigeriasat-2': 'NIGERIASAT-2',
'nigeriasat-x': 'NIGERIASAT-X',
'nigeriasat2': 'NIGERIASAT-2',
'nigeriasatx': 'NIGERIASAT-X',

// Lemur系列
'lemur-1': 'LEMUR-1',
'lemur-2': 'LEMUR-2',
'lemur1': 'LEMUR-1',
'lemur2': 'LEMUR-2',

// 俄罗斯卫星
'resurs-p2': 'RESURS-P 2',
'resurs-p3': 'RESURS-P 3',
'resursp2': 'RESURS-P 2',
'resursp3': 'RESURS-P 3',
'meteor-m2': 'METEOR-M 2',
'meteorm2': 'METEOR-M 2',
'elektro-l1': 'ELEKTRO-L 1',
'elektro-l2': 'ELEKTRO-L 2',
'elektrol1': 'ELEKTRO-L 1',
'elektrol2': 'ELEKTRO-L 2',
'kondor-e': 'KONDOR-E',
'kondore': 'KONDOR-E',
'ECOSTRESS': 'Zarya',
    'CBERS-4A': 'CBERS-4',
    
};

// 增强 normalizeSatelliteName 函数
// export const normalizeSatelliteName = (name) => {
//   // 统一处理中英文映射
//   const normalizedMappings = {
//     'gf-1': '高分一号',
//     'gf-2': '高分二号',
//     'gf-3': '高分三号',
//     'gf-4': '高分四号',
//     'gf-5': '高分五号',
//     'gf-6': '高分六号',
//     'gf-7': '高分七号',
//     'gf1': '高分一号',
//     'gf2': '高分二号',
//     'gf3': '高分三号',
//     'gf4': '高分四号',
//     'gf5': '高分五号',
//     'gf6': '高分六号',
//     'gf7': '高分七号',
//     'sentinel-1': '哨兵-1号',
//     'sentinel-2': '哨兵-2号',
//     'sentinel-3': '哨兵-3号',
//     'sentinel1': '哨兵-1号',
//     'sentinel2': '哨兵-2号',
//     'sentinel3': '哨兵-3号',
//     'himawari': '葵花8号',
//     '哨兵1号': '哨兵-1号',
//     '哨兵2号': '哨兵-2号',
//     '哨兵3号': '哨兵-3号',
//     'fy-4': '风云四号',
//     'fy4': '风云四号',
//     'landsat8': 'Landsat-8',
//     'landsat9': 'Landsat-9',
//     'landsat-8': 'Landsat-8',
//     'landsat-9': 'Landsat-9',
//     // 🆕 新增标准化映射
//     'planet': 'PlanetScope',
//     'planetscope': 'PlanetScope',
//     'dove': 'PlanetScope',
//     'skysat': 'SkySat',
//     'jilin-1': '吉林一号',
//     'jilin1': '吉林一号'
//   };

//   const lower = name.toLowerCase().replace(/[- ]/g, '');
//   return normalizedMappings[lower] || name;
// };
// export const normalizeSatelliteName = (name) => {
//   // 使用智能查找
//   const result = findSatelliteInfo(name);
  
//   if (result) {
//     // 返回数据库中的标准名称（优先使用fullName）
//     return result.data.fullName || result.key;
//   }
  
//   // 如果未找到，返回原名称
//   return name;
// };
export const normalizeSatelliteName = (name) => {
  // 先进行基本的标准化处理
  const trimmedName = name.trim();
  
  // 手动处理常见的映射关系
  const manualMappings = {
    'GF-1': '高分一号',
    'GF-2': '高分二号',
    'GF-3': '高分三号',
    'GF-4': '高分四号',
    'GF-5': '高分五号',
    'GF-6': '高分六号',
    'GF-7': '高分七号',
    'GF1': '高分一号',
    'GF2': '高分二号',
    'GF3': '高分三号',
    'GF4': '高分四号',
    'GF5': '高分五号',
    'GF6': '高分六号',
    'GF7': '高分七号',
    'Sentinel-1': '哨兵-1号',
    'Sentinel-2': '哨兵-2号',
    'Sentinel-3': '哨兵-3号',
    'FY-1': '风云一号',
    'FY-2': '风云二号',
    'FY-3': '风云三号',
    'FY-4': '风云四号',
    'HY-1': '海洋一号',
    'HY-2': '海洋二号',
    'ZY-1': '资源一号',
    'ZY-2': '资源二号',
    'ZY-3': '资源三号',
    'HJ-1': '环境一号',
    'gf-1': '高分一号',
'gf-2': '高分二号',
'gf-3': '高分三号',
'gf-4': '高分四号',
'gf-5': '高分五号',
'gf-6': '高分六号',
'gf-7': '高分七号',
'gf-8': '高分八号',
'gf-9': '高分九号',
'gf-10': '高分十号',
'gf-11': '高分十一号',
'gf-12': '高分十二号',
'gf-13': '高分十三号',
'gf-14': '高分十四号',
'gf1': '高分一号',
'gf2': '高分二号',
'gf3': '高分三号',
'gf4': '高分四号',
'gf5': '高分五号',
'gf6': '高分六号',
'gf7': '高分七号',
'gf8': '高分八号',
'gf9': '高分九号',
'gf10': '高分十号',
'gf11': '高分十一号',
'gf12': '高分十二号',
'gf13': '高分十三号',
'gf14': '高分十四号',

// 风云系列
'fy-1': '风云一号',
'fy-2': '风云二号',
'fy-3': '风云三号',
'fy-4': '风云四号',
'fy1': '风云一号',
'fy2': '风云二号',
'fy3': '风云三号',
'fy4': '风云四号',
'fy-2f': '风云二号F',
'fy-2g': '风云二号G',
'fy2f': '风云二号F',
'fy2g': '风云二号G',

// 哨兵系列
'sentinel-1': '哨兵-1号',
'sentinel-2': '哨兵-2号',
'sentinel-3': '哨兵-3号',
'sentinel-5p': 'Sentinel-5P',
'sentinel-6': '哨兵-6号',
'sentinel1': '哨兵-1号',
'sentinel2': '哨兵-2号',
'sentinel3': '哨兵-3号',
'sentinel5p': 'Sentinel-5P',
'sentinel6': '哨兵-6号',
'哨兵1号': '哨兵-1号',
'哨兵2号': '哨兵-2号',
'哨兵3号': '哨兵-3号',
'sentinel-1a': 'Sentinel-1A',
'sentinel-1b': 'Sentinel-1B',
'sentinel-2a': 'Sentinel-2A',
'sentinel-2b': 'Sentinel-2B',
'sentinel-3a': 'Sentinel-3A',

// Landsat系列
'landsat-1': 'Landsat-1',
'landsat-2': 'Landsat-2',
'landsat-3': 'Landsat-3',
'landsat-4': 'Landsat-4',
'landsat-5': 'Landsat-5',
'landsat-6': 'Landsat-6',
'landsat-7': 'Landsat-7',
'landsat-8': 'Landsat-8',
'landsat-9': 'Landsat-9',
'landsat1': 'Landsat-1',
'landsat2': 'Landsat-2',
'landsat3': 'Landsat-3',
'landsat4': 'Landsat-4',
'landsat5': 'Landsat-5',
'landsat6': 'Landsat-6',
'landsat7': 'Landsat-7',
'landsat8': 'Landsat-8',
'landsat9': 'Landsat-9',

// 海洋系列
'hy-1': '海洋一号',
'hy-2': '海洋二号',
'hy-3': '海洋三号',
'hy1': '海洋一号',
'hy2': '海洋二号',
'hy3': '海洋三号',
'hy-2a': '海洋二号A',
'haiyang-2a': '海洋二号A',

// 资源系列
'zy-1': '资源一号',
'zy-2': '资源二号',
'zy-3': '资源三号',
'zy1': '资源一号',
'zy2': '资源二号',
'zy3': '资源三号',
'zy-1-02c': '资源一号02C',
'zy-3-1': '资源三号01',
'zy1-02c': '资源一号02C',
'zy3-1': '资源三号01',

// 环境系列
'hj-1': '环境一号',
'hj1': '环境一号',

// 遥感系列
'yaogan-7': '遥感七号',
'yaogan-8': '遥感八号',
'yaogan-9': '遥感九号',
'yaogan-10': '遥感十号',
'yaogan-11': '遥感十一号',
'yaogan-12': '遥感十二号',
'yaogan-13': '遥感十三号',
'yaogan-14': '遥感十四号',
'yaogan-15': '遥感十五号',
'yaogan-20': '遥感二十号',
'yaogan-21': '遥感二十一号',
'yaogan-22': '遥感二十二号',
'yaogan-23': '遥感二十三号',
'yaogan-24': '遥感二十四号',
'yaogan-25': '遥感二十五号',
'yaogan-26': '遥感二十六号',
'yaogan-27': '遥感二十七号',
'yaogan-28': '遥感二十八号',
'yaogan-29': '遥感二十九号',
'yaogan-30': '遥感三十号',

// 天绘系列
'th-1': '天绘一号',
'th-2': '天绘二号',
'th-4': '天绘四号',
'th1': '天绘一号',
'th2': '天绘二号',
'th4': '天绘四号',
'th-1-02': '天绘一号02',

// 实践系列
'sj-6-04a': '实践六号04A',
'sj-11-02': '实践十一号02',
'shijian-6-04b': 'SHIJIAN-6 04B',

// WorldView系列
'worldview-1': 'WorldView-1',
'worldview-2': 'WorldView-2',
'worldview-3': 'WorldView-3',
'worldview-4': 'WorldView-4',
'worldview1': 'WorldView-1',
'worldview2': 'WorldView-2',
'worldview3': 'WorldView-3',
'worldview4': 'WorldView-4',
'wv-1': 'WorldView-1',
'wv-2': 'WorldView-2',
'wv-3': 'WorldView-3',
'wv-4': 'WorldView-4',

// 日本卫星
'himawari': '向日葵8号',
'himawari-8': '向日葵8号',
'himawari-9': '向日葵9号',
'himawari8': '向日葵8号',
'himawari9': '向日葵9号',
'向日葵8号': '向日葵8号',
'向日葵9号': '向日葵9号',

// 商业小卫星星座
'planet': 'PlanetScope',
'planetscope': 'PlanetScope',
'dove': 'PlanetScope',
'skysat': 'SkySat',
'skysat-a': 'SkySat',
'skysat-b': 'SkySat',
'jilin-1': '吉林一号',
'jilin1': '吉林一号',
'jl-1': '吉林一号',
'jl1': '吉林一号',

// SPOT系列
'spot-1': 'SPOT 1',
'spot-2': 'SPOT 2',
'spot-3': 'SPOT 3',
'spot-4': 'SPOT 4',
'spot-5': 'SPOT 5',
'spot-6': 'SPOT 6',
'spot-7': 'SPOT 7',
'spot1': 'SPOT 1',
'spot2': 'SPOT 2',
'spot3': 'SPOT 3',
'spot4': 'SPOT 4',
'spot5': 'SPOT 5',
'spot6': 'SPOT 6',
'spot7': 'SPOT 7',

// Pleiades系列
'pleiades-1a': 'PLEIADES 1A',
'pleiades-1b': 'PLEIADES 1B',
'pleiades1a': 'PLEIADES 1A',
'pleiades1b': 'PLEIADES 1B',

// COSMO-SkyMed系列
'cosmo-skymed-1': 'COSMO-SKYMED 1',
'cosmo-skymed-2': 'COSMO-SKYMED 2',
'cosmo-skymed-3': 'COSMO-SKYMED 3',
'cosmo-skymed-4': 'COSMO-SKYMED 4',
'cosmoskymed1': 'COSMO-SKYMED 1',
'cosmoskymed2': 'COSMO-SKYMED 2',
'cosmoskymed3': 'COSMO-SKYMED 3',
'cosmoskymed4': 'COSMO-SKYMED 4',

// QuickBird系列
'quickbird-1': 'QUICKBIRD 1',
'quickbird-2': 'QUICKBIRD 2',
'quickbird1': 'QUICKBIRD 1',
'quickbird2': 'QUICKBIRD 2',

// 其他重要卫星
'terrasar-x': 'TerraSAR-X',
'terrasarx': 'TerraSAR-X',
'tandem-x': 'TANDEM-X',
'tandemx': 'TANDEM-X',
'radarsat-2': 'RADARSAT-2',
'radarsat2': 'RADARSAT-2',
'alos-2': 'ALOS-2',
'alos2': 'ALOS-2',
'gcom-w1': 'GCOM-W1',
'gcomw1': 'GCOM-W1',
'suomi-npp': 'SUOMI NPP',
'suominpp': 'SUOMI NPP',
'gpm-core': 'GPM-CORE',
'gpmcore': 'GPM-CORE',
'oco-2': 'OCO 2',
'oco2': 'OCO 2',
'jason-3': 'JASON-3',
'jason3': 'JASON-3',

// 印度卫星
'resourcesat-2': 'RESOURCESAT-2',
'resourcesat2': 'RESOURCESAT-2',
'cartosat-2a': 'CARTOSAT-2A',
'cartosat-2b': 'CARTOSAT-2B',
'cartosat2a': 'CARTOSAT-2A',
'cartosat2b': 'CARTOSAT-2B',
'risat-1': 'RISAT-1',
'risat1': 'RISAT-1',

// 韩国卫星
'kompsat-2': 'KOMPSAT-2',
'kompsat-3': 'KOMPSAT-3',
'kompsat-3a': 'KOMPSAT-3A',
'kompsat2': 'KOMPSAT-2',
'kompsat3': 'KOMPSAT-3',
'kompsat3a': 'KOMPSAT-3A',
'arirang-3': 'ARIRANG-3',
'arirang-5': 'ARIRANG-5',
'arirang3': 'ARIRANG-3',
'arirang5': 'ARIRANG-5',

// 欧洲卫星
'meteosat-10': 'METEOSAT-10',
'meteosat10': 'METEOSAT-10',
'metop-b': 'METOP-B',
'metopb': 'METOP-B',
'proba-1': 'PROBA-1',
'proba-2': 'PROBA-2',
'proba-v': 'PROBA-V',
'proba1': 'PROBA-1',
'proba2': 'PROBA-2',
'probav': 'PROBA-V',

// 其他卫星系列
'dmsp-f17': 'DMSP F17',
'dmsp-f18': 'DMSP F18',
'dmsp-f19': 'DMSP 5D-3 F19',
'dmc3-fm1': 'DMC3-FM1',
'dmc3-fm2': 'DMC3-FM2',
'dmc3-fm3': 'DMC3-FM3',

// CBERS系列
'cbers-4': 'CBERS 4',
'cbers4': 'CBERS 4',

// 创新系列
'cx-1-03': '创新一号03',
'cx-1-04': '创新一号04',
'chuangxin-1-03': 'CHUANGXIN 1-03',

// 电磁监测系列
'zhangheng-1': '张衡一号',
'zhangheng1': '张衡一号',

// 北斗系列（如果需要）
'beidou': '北斗',
'bd': '北斗',

// 通信卫星系列
'tdrs': 'TDRS',
'intelsat': 'Intelsat',

// 气象卫星
'goes': 'GOES',
'noaa': 'NOAA',
'noaa-15': 'NOAA 15',
'noaa15': 'NOAA 15',

// 科学卫星
'terra': 'TERRA',
'aqua': 'AQUA',
'aura': 'AURA',
'calipso': 'CALIPSO',
'cloudsat': 'CloudSat',

// 军事侦察卫星
'igs-5a': 'IGS 5A',
'igs-6a': 'IGS 6A',
'igs-7a': 'IGS 7A',
'igs-9a': 'IGS 9A',
'igs-o-5': 'IGS O-5',

// 以色列卫星
'ofeq-9': 'OFEQ 9',
'ofeq-10': 'OFEQ 10',
'ofeq9': 'OFEQ 9',
'ofeq10': 'OFEQ 10',

// 埃及卫星
'egyptsat-2': 'EGYPTSAT 2',
'egyptsat2': 'EGYPTSAT 2',

// 其他国家卫星
'deimos-2': 'DEIMOS-2',
'deimos2': 'DEIMOS-2',
'kazeosat-1': 'KAZEOSAT 1',
'kazeosat-2': 'KAZEOSAT 2',
'kazeosat1': 'KAZEOSAT 1',
'kazeosat2': 'KAZEOSAT 2',
'alsat-2a': 'ALSAT 2A',
'alsat2a': 'ALSAT 2A',
'nigeriasat-2': 'NIGERIASAT-2',
'nigeriasat-x': 'NIGERIASAT-X',
'nigeriasat2': 'NIGERIASAT-2',
'nigeriasatx': 'NIGERIASAT-X',

// Lemur系列
'lemur-1': 'LEMUR-1',
'lemur-2': 'LEMUR-2',
'lemur1': 'LEMUR-1',
'lemur2': 'LEMUR-2',

// 俄罗斯卫星
'resurs-p2': 'RESURS-P 2',
'resurs-p3': 'RESURS-P 3',
'resursp2': 'RESURS-P 2',
'resursp3': 'RESURS-P 3',
'meteor-m2': 'METEOR-M 2',
'meteorm2': 'METEOR-M 2',
'elektro-l1': 'ELEKTRO-L 1',
'elektro-l2': 'ELEKTRO-L 2',
'elektrol1': 'ELEKTRO-L 1',
'elektrol2': 'ELEKTRO-L 2',
'kondor-e': 'KONDOR-E',
'kondore': 'KONDOR-E',
'ECOSTRESS': 'Zarya',
  };
  
  // 检查手动映射
  const upperName = trimmedName.toUpperCase();
  if (manualMappings[upperName]) {
    return manualMappings[upperName];
  }
  
  // 使用智能查找
  const result = findSatelliteInfo(trimmedName);
  
  if (result) {
    // 返回数据库中的标准名称（优先使用fullName）
    return result.data.fullName || result.key;
  }
  
  // 如果未找到，返回原名称
  return trimmedName;
};

// 创建正则表达式用于快速匹配
const createSatelliteRegex = () => {
  const patterns = COMMON_SATELLITES.map(sat => {
    // 转义特殊字符
    const escaped = sat.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return escaped;
  });
  return new RegExp(`(${patterns.join('|')})`, 'gi');
};

const SATELLITE_REGEX = createSatelliteRegex();

// 🔧 优化：快速本地提取
const extractSatellitesLocally = (text) => {
  const foundSatellites = new Set();
  const matches = text.match(SATELLITE_REGEX);

  if (matches) {
    matches.forEach(match => {
      // 标准化名称并去重
      const normalized = normalizeSatelliteName(match.trim());
      foundSatellites.add(normalized);
    });
  }

  return Array.from(foundSatellites);
};

// 🆕 新增：从方案的卫星组成部分精确提取卫星
const extractSatellitesFromComposition = (content) => {
  console.log("🛰️ 从卫星组成部分提取卫星...");

  const satellites = new Set();

  // 🆕 优先查找"推荐卫星"列表
  const recommendPatterns = [
    /推荐卫星[：:]\s*([^\n]+)/i,
    /推荐的卫星[：:]\s*([^\n]+)/i,
    /建议卫星[：:]\s*([^\n]+)/i,
    /卫星列表[：:]\s*([^\n]+)/i
  ];

  // 尝试匹配推荐卫星列表
  for (const pattern of recommendPatterns) {
    const match = content.match(pattern);
    if (match && match[1]) {
      const satelliteListStr = match[1];
      console.log("📋 找到推荐卫星列表:", satelliteListStr);

      // 分割卫星列表（支持多种分隔符）
      const separators = /[、,，]|(?:和)|(?:以及)|(?:及)/g;
      const satelliteNames = satelliteListStr.split(separators);

      // 提取每个卫星名称
      for (const satName of satelliteNames) {
        const trimmedName = satName.trim();
        if (trimmedName) {
          // 使用本地快速提取验证
          const localSatellites = extractSatellitesLocally(trimmedName);
          if (localSatellites.length > 0) {
            localSatellites.forEach(sat => {
              const normalized = normalizeSatelliteName(sat);
              satellites.add(normalized);
              console.log("✅ 从推荐列表提取到卫星:", normalized);
            });
          } else {
            // 直接尝试标准化
            const normalized = normalizeSatelliteName(trimmedName);
            if (COMMON_SATELLITES.includes(normalized)) {
              satellites.add(normalized);
              console.log("✅ 从推荐列表提取到卫星:", normalized);
            }
          }
        }
      }

      // 如果成功提取到卫星，直接返回
      if (satellites.size > 0) {
        const result = Array.from(satellites);
        console.log("🎯 成功从推荐卫星列表提取:", result);
        return result;
      }
    }
  }

  // 如果没有找到推荐卫星列表，尝试在卫星组成部分查找
  console.log("⚠️ 未找到推荐卫星列表，尝试其他提取方法...");

  // 查找"卫星组成"部分
  const satelliteCompositionRegex = /(?:卫星组成|卫星列表|卫星配置|组成卫星|卫星组)[：:]*\s*\n([\s\S]*?)(?=\n(?:##|###|\d+\.|[三四五六七八九十]、)|$)/i;
  const match = content.match(satelliteCompositionRegex);

  if (match && match[1]) {
    const compositionSection = match[1];
    console.log("📄 找到卫星组成部分:", compositionSection.slice(0, 200));

    // 在组成部分中再次查找推荐卫星列表
    for (const pattern of recommendPatterns) {
      const recMatch = compositionSection.match(pattern);
      if (recMatch && recMatch[1]) {
        const satelliteListStr = recMatch[1];
        const separators = /[、,，]|(?:和)|(?:以及)|(?:及)/g;
        const satelliteNames = satelliteListStr.split(separators);

        for (const satName of satelliteNames) {
          const trimmedName = satName.trim();
          if (trimmedName) {
            const localSatellites = extractSatellitesLocally(trimmedName);
            if (localSatellites.length > 0) {
              localSatellites.forEach(sat => {
                const normalized = normalizeSatelliteName(sat);
                satellites.add(normalized);
              });
            } else {
              const normalized = normalizeSatelliteName(trimmedName);
              if (COMMON_SATELLITES.includes(normalized)) {
                satellites.add(normalized);
              }
            }
          }
        }

        if (satellites.size > 0) {
          const result = Array.from(satellites);
          console.log("🎯 从卫星组成部分的推荐列表提取:", result);
          return result;
        }
      }
    }

    // 如果还是没找到，使用原有逻辑
    const lines = compositionSection.split('\n');
    for (const line of lines) {
      if (!line.trim()) continue;

      const localMatches = line.match(SATELLITE_REGEX);
      if (localMatches) {
        localMatches.forEach(sat => {
          const normalized = normalizeSatelliteName(sat.trim());
          satellites.add(normalized);
          console.log("✅ 找到卫星:", normalized);
        });
      }
    }
  }

  // 备用方法保持不变
  if (satellites.size === 0) {
    console.log("⚠️ 未找到明确的卫星组成部分，尝试备用提取方法");
    const altRegex = /(?:包含|包括|选择了?|组合了?|采用了?)[：:]*\s*([^\n]*(?:、|,|和|以及)[^\n]*)/gi;
    let altMatch;
    while ((altMatch = altRegex.exec(content)) !== null) {
      const satelliteList = altMatch[1];
      const foundSats = extractSatellitesLocally(satelliteList);
      foundSats.forEach(sat => satellites.add(sat));
    }
  }

  const result = Array.from(satellites);
  console.log("🛰️ 最终提取到的卫星:", result);
  return result;
};

// 提取卫星名称 - 优化版本
export const extractSatelliteNames = async (text) => {
  try {
    console.log("开始提取卫星名称...");

    // 🔧 优化：先尝试从卫星组成部分提取
    const compositionSatellites = extractSatellitesFromComposition(text);
    if (compositionSatellites.length > 0) {
      return compositionSatellites;
    }

    // 如果没找到，使用本地快速提取
    const localResults = extractSatellitesLocally(text);

    if (localResults.length > 0) {
      console.log("本地快速提取到卫星:", localResults);
      return localResults;
    }

    // 🔧 优化：只有在本地没有找到时才调用API
    // 如果文本较短，直接返回空结果
    if (text.length < 50) {
      return [];
    }

    // 使用DeepSeek API进行深度提取
    try {
      const response = await axios.post("https://api.deepseek.com/v1/chat/completions", {
        model: "deepseek-chat",
        messages: [{
          role: "user",
          content: `请从这段文本中提取出所有卫星名称（包括中文和英文），以JSON数组格式返回。
          注意：
          1. 同一卫星的不同名称只取其一（如"高分6号"与"GF-6"只取前者）
          2. 只返回实际的卫星名称，不要包含描述性文字
          3. 返回格式必须是JSON数组，如：["风云四号", "高分一号", "Sentinel-2"]
          4. 如果没有找到卫星名称，返回空数组[]
          
          文本内容：${text.slice(0, 1000)}`  // 🔧 优化：限制文本长度
        }],
        temperature: 0.1
      }, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer sk-40059d9b6b6943319120ad243c2dd0e4"
        },
        timeout: 5000  // 🔧 优化：减少超时时间
      });

      const result = response.data.choices?.[0]?.message?.content?.trim();

      try {
        const satelliteNames = JSON.parse(result);
        if (Array.isArray(satelliteNames) && satelliteNames.length > 0) {
          console.log("DeepSeek API提取到卫星名称:", satelliteNames);

          // 🔧 优化：合并本地和API结果，去重
          const combined = new Set([...localResults, ...satelliteNames]);
          return Array.from(combined);
        }
      } catch (parseError) {
        console.log("解析API返回的JSON失败，返回本地结果");
      }
    } catch (apiError) {
      console.log("API调用失败，返回本地结果:", apiError.message);
    }

    return localResults;

  } catch (error) {
    console.error('卫星名称提取过程出错:', error);
    return [];
  }
};

// 🔧 优化：批量提取消息中的卫星名称 - 只从最新的方案消息中提取
export const extractSatelliteNamesFromMessages = async (messages) => {
  const allSatelliteNames = new Set();

  // 只从assistant的消息中提取
  const assistantMessages = messages.filter(msg => msg.role === 'assistant');

  // 🆕 查找最新的包含方案的消息
  let latestPlanMessage = null;
  for (let i = assistantMessages.length - 1; i >= 0; i--) {
    const msg = assistantMessages[i];
    if (msg.content && (
      msg.content.includes('卫星组成') ||
      msg.content.includes('## 2.') ||
      msg.content.includes('###') ||
      msg.content.includes('方案')
    )) {
      latestPlanMessage = msg;
      break;
    }
  }

  // 如果找到方案消息，只从这条消息中提取
  if (latestPlanMessage) {
    console.log('🛰️ 找到最新方案消息，从中提取卫星...');
    const satellites = extractSatellitesFromComposition(latestPlanMessage.content);
    satellites.forEach(name => {
      const normalized = normalizeSatelliteName(name);
      allSatelliteNames.add(normalized);
    });
  } else {
    // 如果没有找到方案消息，从最新的助手消息中提取
    console.log('🛰️ 未找到方案消息，从最新消息中提取...');
    if (assistantMessages.length > 0) {
      const latestMsg = assistantMessages[assistantMessages.length - 1];
      const satellites = extractSatellitesLocally(latestMsg.content);
      satellites.forEach(name => {
        const normalized = normalizeSatelliteName(name);
        allSatelliteNames.add(normalized);
      });
    }
  }

  // 🔧 额外的去重检查
  const finalSatellites = Array.from(allSatelliteNames);
  const uniqueSatellites = [];
  const seen = new Set();

  for (const sat of finalSatellites) {
    const key = sat.toLowerCase().replace(/[- ]/g, '');
    if (!seen.has(key)) {
      seen.add(key);
      uniqueSatellites.push(sat);
    }
  }

  console.log('🛰️ 提取并去重后的卫星:', uniqueSatellites);
  return uniqueSatellites;
};

// 🆕 新增：缓存提取结果
const extractionCache = new Map();

export const extractSatelliteNamesWithCache = async (text) => {
  // 生成文本的简单哈希作为缓存键
  const cacheKey = text.slice(0, 100) + text.length;

  if (extractionCache.has(cacheKey)) {
    console.log("使用缓存的卫星提取结果");
    return extractionCache.get(cacheKey);
  }

  const result = await extractSatelliteNames(text);
  extractionCache.set(cacheKey, result);

  // 限制缓存大小
  if (extractionCache.size > 100) {
    const firstKey = extractionCache.keys().next().value;
    extractionCache.delete(firstKey);
  }

  return result;
};

export const extractSatellitesFromTable = (content) => {
  console.log("🔍 从表格中提取卫星...");

  const satellites = new Set();

  // 匹配表格行
  const tableRowRegex = /\|\s*([^|]+?)\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|/g;
  let match;

  while ((match = tableRowRegex.exec(content)) !== null) {
    const cellContent = match[1].trim();
    // 跳过表头和分隔行
    if (cellContent && !cellContent.includes('卫星名称') && !cellContent.includes('---')) {
      const normalized = normalizeSatelliteName(cellContent);
      if (normalized && COMMON_SATELLITES.includes(normalized)) {
        satellites.add(normalized);
        console.log("✅ 从表格提取到卫星:", normalized);
      }
    }
  }

  return Array.from(satellites);
};

// 🆕 新增：两阶段提取策略
export const extractSatellitesTwoPhase = async (content) => {
  console.log("🚀 开始两阶段卫星提取...");

  // 第一阶段：快速本地提取
  const phase1Results = extractSatellitesFromComposition(content);
  console.log("📊 第一阶段提取结果:", phase1Results);

  // 第二阶段：表格精确提取
  const phase2Results = extractSatellitesFromTable(content);
  console.log("📊 第二阶段提取结果:", phase2Results);

  // 合并结果并去重
  const combined = new Set([...phase1Results, ...phase2Results]);
  const finalResults = Array.from(combined);

  console.log("✅ 两阶段提取完成，最终结果:", finalResults);
  return finalResults;
};