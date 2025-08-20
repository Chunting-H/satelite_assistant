// config/extendedSatelliteDatabase.js - 扩展的卫星数据库，支持完整的过滤功能

// 扩展的卫星数据库，包含详细的轨道和技术参数
export const EXTENDED_SATELLITE_DATABASE = {
  // 中国卫星
  "GF-1": {
    fullName: "高分一号",
    englishName: "GaoFen-1",
    aliases: ["GF-1", "高分一号"],
    cosparId: "2013-018A",
    noradId: "39150",
    country: "中国",
    owner: "China",
    agencies: ["CNSA", "中国科学院"],
    launchDate: "2013-04-26",
    endDate: null,
    status: "Operational",
    type: "地球观测",
    description: "中国高分辨率对地观测系统首发星",

    // 轨道参数
    orbitType: "LLEO_S",
    orbitHeight: 645,
    orbitPeriod: 97.8,
    apogeeHeight: 654,
    perigeeHeight: 636,
    inclination: 98.05,
    eccentricity: 0.0013,
    raan: 10.7,
    argumentOfPerigee: 90.2,
    crossingTime: "10:30",
    revisitPeriod: 4,

    // 技术规格
    launchMass: 1140,
    dryMass: 850,
    power: 1200,
    designLife: "5-8年",
    manufacturer: "中国空间技术研究院",
    platform: "CAST2000",
    stabilization: "三轴稳定",
    propulsion: "单组元肼推进",
    communicationBands: ["S波段", "X波段"],
    dataRate: "300 Mbps",

    // 载荷信息
    spatialResolution: "2米(全色)/8米(多光谱)",
    spectralBands: ["全色", "蓝", "绿", "红", "近红外"],
    spectralResolution: "4个多光谱波段",
    temporalResolution: "4天",
    swathWidth: "60公里",
    observationModes: ["推扫成像"],

    // 发射信息
    launchSite: "Jiuquan Space Center, PRC",
    launchVehicle: "长征二号丁"
  },

  "GF-2": {
    fullName: "高分二号",
    englishName: "GaoFen-2",
    aliases: ["GF-2", "高分二号"],
    cosparId: "2014-047A",
    noradId: "40069",
    country: "中国",
    owner: "China",
    agencies: ["CNSA"],
    launchDate: "2014-08-19",
    endDate: null,
    status: "Operational",
    type: "地球观测",
    description: "中国首颗亚米级高分辨率光学遥感卫星",

    orbitType: "LLEO_S",
    orbitHeight: 631,
    orbitPeriod: 97.4,
    apogeeHeight: 631,
    perigeeHeight: 631,
    inclination: 97.89,
    crossingTime: "10:30",
    revisitPeriod: 5,

    launchMass: 1200,
    dryMass: 900,
    power: 1300,
    designLife: "5年",
    manufacturer: "中国空间技术研究院",

    spatialResolution: "1米(全色)/4米(多光谱)",
    spectralBands: ["全色", "蓝", "绿", "红", "近红外"],
    swathWidth: "45公里",

    launchSite: "Taiyuan Space Center, PRC",
    launchVehicle: "长征四号乙"
  },

  "FY-4A": {
    fullName: "风云四号A星",
    englishName: "Fengyun-4A",
    aliases: ["FY-4A", "风云四号A"],
    cosparId: "2016-077A",
    noradId: "41882",
    country: "中国",
    owner: "China",
    agencies: ["CMA", "NSMC"],
    launchDate: "2016-12-11",
    endDate: null,
    status: "Operational",
    type: "气象观测",
    description: "中国新一代静止轨道气象卫星",

    orbitType: "GEO_S",
    orbitHeight: 35786,
    orbitPeriod: 1436,
    orbitLongitude: 104.7,
    inclination: 0.1,

    launchMass: 5400,
    dryMass: 2800,
    power: 2800,
    designLife: "7年",
    manufacturer: "上海航天技术研究院",

    spatialResolution: "500米-4公里",
    spectralBands: ["可见光", "近红外", "中红外", "远红外"],
    temporalResolution: "15分钟",

    launchSite: "Xichang Space Center, PRC",
    launchVehicle: "长征三号乙"
  },

  // 美国卫星
  "LANDSAT-8": {
    fullName: "Landsat-8",
    englishName: "Landsat Data Continuity Mission",
    aliases: ["LDCM", "Landsat-8"],
    cosparId: "2013-008A",
    noradId: "39084",
    country: "美国",
    owner: "United States",
    agencies: ["NASA", "USGS"],
    launchDate: "2013-02-11",
    endDate: null,
    status: "Operational",
    type: "地球观测",
    description: "美国Landsat系列地球观测卫星",

    orbitType: "LLEO_S",
    orbitHeight: 705,
    orbitPeriod: 98.9,
    apogeeHeight: 705,
    perigeeHeight: 705,
    inclination: 98.2,
    crossingTime: "10:00",
    revisitPeriod: 16,

    launchMass: 2623,
    dryMass: 1300,
    power: 1550,
    designLife: "5年",
    manufacturer: "Orbital Sciences Corporation",

    spatialResolution: "15米(全色)/30米(多光谱)",
    spectralBands: ["沿海", "蓝", "绿", "红", "近红外", "短波红外1", "短波红外2", "全色", "卷云"],
    swathWidth: "185公里",

    launchSite: "Air Force Western Test Range",
    launchVehicle: "Atlas V 401"
  },

  "WORLDVIEW-3": {
    fullName: "WorldView-3",
    englishName: "WorldView-3",
    aliases: ["WV-3"],
    cosparId: "2014-048A",
    noradId: "40115",
    country: "美国",
    owner: "United States",
    agencies: ["DigitalGlobe", "Maxar Technologies"],
    launchDate: "2014-08-13",
    endDate: null,
    status: "Operational",
    type: "商业遥感",
    description: "高分辨率商业地球观测卫星",

    orbitType: "LLEO_S",
    orbitHeight: 617,
    orbitPeriod: 97.2,
    inclination: 97.97,
    crossingTime: "13:30",
    revisitPeriod: 1,

    launchMass: 2800,
    dryMass: 1500,
    designLife: "7.25年",
    manufacturer: "Ball Aerospace",

    spatialResolution: "0.31米(全色)/1.24米(多光谱)",
    spectralBands: ["全色", "8个多光谱", "8个短波红外"],
    swathWidth: "13.1公里",

    launchSite: "Air Force Western Test Range",
    launchVehicle: "Atlas V 401"
  },

  // 欧洲卫星
  "SENTINEL-2A": {
    fullName: "Sentinel-2A",
    englishName: "Sentinel-2A",
    aliases: ["S2A", "哨兵-2A"],
    cosparId: "2015-028A",
    noradId: "40697",
    country: "欧洲",
    owner: "European Space Agency",
    agencies: ["ESA", "EU"],
    launchDate: "2015-06-23",
    endDate: null,
    status: "Operational",
    type: "地球观测",
    description: "欧洲哥白尼计划多光谱成像卫星",

    orbitType: "LLEO_S",
    orbitHeight: 786,
    orbitPeriod: 100.6,
    inclination: 98.62,
    crossingTime: "10:30",
    revisitPeriod: 10,

    launchMass: 1140,
    dryMass: 900,
    power: 1700,
    designLife: "7.25年",
    manufacturer: "Airbus Defence and Space",

    spatialResolution: "10米/20米/60米",
    spectralBands: ["13个多光谱波段"],
    swathWidth: "290公里",

    launchSite: "Europe's Spaceport, Kourou, French Guiana",
    launchVehicle: "Vega"
  },

  "METEOSAT-11": {
    fullName: "Meteosat-11",
    englishName: "Meteosat Second Generation 4",
    aliases: ["MSG-4", "Meteosat-11"],
    cosparId: "2015-034A",
    noradId: "40732",
    country: "欧洲",
    owner: "European Space Agency",
    agencies: ["ESA", "EUMETSAT"],
    launchDate: "2015-07-15",
    endDate: null,
    status: "Operational",
    type: "气象观测",
    description: "欧洲第二代气象卫星",

    orbitType: "GEO_S",
    orbitHeight: 35786,
    orbitPeriod: 1436,
    orbitLongitude: 0.0,
    inclination: 0.1,

    launchMass: 2030,
    dryMass: 1200,
    power: 1500,
    designLife: "7年",
    manufacturer: "Thales Alenia Space",

    spatialResolution: "1公里(可见光)/3公里(红外)",
    spectralBands: ["12个波段"],
    temporalResolution: "15分钟",

    launchSite: "Europe's Spaceport, Kourou, French Guiana",
    launchVehicle: "Ariane 5 ECA"
  },

  // 日本卫星
  "HIMAWARI-8": {
    fullName: "Himawari-8",
    englishName: "Himawari-8",
    aliases: ["向日葵8号", "葵花8号"],
    cosparId: "2014-060A",
    noradId: "40267",
    country: "日本",
    owner: "Japan",
    agencies: ["JMA", "JAXA"],
    launchDate: "2014-10-07",
    endDate: null,
    status: "Operational",
    type: "气象观测",
    description: "日本新一代静止轨道气象卫星",

    orbitType: "GEO_S",
    orbitHeight: 35786,
    orbitPeriod: 1436,
    orbitLongitude: 140.7,
    inclination: 0.1,

    launchMass: 3500,
    dryMass: 1750,
    power: 2800,
    designLife: "8年",
    manufacturer: "三菱电机",

    spatialResolution: "0.5-2公里",
    spectralBands: ["16个波段"],
    temporalResolution: "10分钟",

    launchSite: "Tanegashima Space Center, Japan",
    launchVehicle: "H-IIA 202"
  },

  // 失效卫星示例
  "CYGNUS-OA9": {
    fullName: "CYGNUS OA-9",
    englishName: "SS J.R. Thompson",
    aliases: ["Cygnus OA-9", "Cygnus PCM-9", "ISS TEMPEST-D", "SS J.R. Thompson"],
    cosparId: "2018-046A",
    noradId: "43474",
    country: "美国",
    owner: "United States",
    agencies: ["NASA", "CSA", "DLR", "ESA", "JAXA", "Roscosmos"],
    launchDate: "2018-05-21",
    endDate: "2018-07-30",
    status: "Decayed",
    type: "货运飞船",
    description: "国际空间站货运任务，搭载TEMPEST-D实验载荷",

    orbitType: "LLEO_I",
    orbitHeight: 400,
    orbitPeriod: 92.47,
    apogeeHeight: 410,
    perigeeHeight: 381,
    inclination: 51.64,

    launchMass: 7200,
    dryMass: 2000,
    designLife: "3个月",
    manufacturer: "Orbital ATK",

    spatialResolution: "1公里",
    spectralBands: ["毫米波"],

    launchSite: "Wallops Island, Virginia, USA",
    launchVehicle: "Antares 230"
  },

  // 印度卫星
  "CARTOSAT-2F": {
    fullName: "Cartosat-2F",
    englishName: "Cartosat-2F",
    aliases: ["CARTOSAT-2F"],
    cosparId: "2017-008C",
    noradId: "42063",
    country: "印度",
    owner: "India",
    agencies: ["ISRO"],
    launchDate: "2017-02-15",
    endDate: null,
    status: "Operational",
    type: "地球观测",
    description: "印度高分辨率地球观测卫星",

    orbitType: "LLEO_S",
    orbitHeight: 505,
    orbitPeriod: 94.6,
    inclination: 97.46,
    crossingTime: "09:30",
    revisitPeriod: 5,

    launchMass: 712,
    dryMass: 400,
    power: 986,
    designLife: "5年",
    manufacturer: "ISRO Satellite Centre",

    spatialResolution: "0.65米(全色)",
    swathWidth: "9.6公里",

    launchSite: "Satish Dhawan Space Centre, India",
    launchVehicle: "PSLV-C37"
  }
};

// 统计信息生成函数
export const generateSatelliteStatistics = (satellites) => {
  const stats = {
    status: {},
    owner: {},
    orbitType: {},
    launchSite: {},
    total: 0
  };

  Object.values(satellites).forEach(satellite => {
    stats.total++;

    // 状态统计
    const status = satellite.status || 'Unknown';
    stats.status[status] = (stats.status[status] || 0) + 1;

    // 所有者统计
    const owner = satellite.owner || 'Unknown';
    stats.owner[owner] = (stats.owner[owner] || 0) + 1;

    // 轨道类型统计
    const orbitType = satellite.orbitType || 'Unknown';
    stats.orbitType[orbitType] = (stats.orbitType[orbitType] || 0) + 1;

    // 发射地点统计
    const launchSite = satellite.launchSite || 'Unknown';
    stats.launchSite[launchSite] = (stats.launchSite[launchSite] || 0) + 1;
  });

  return stats;
};

// 轨道类型映射
export const ORBIT_TYPE_MAPPING = {
  "LLEO_S": "Lower LEO/Sun-Sync",
  "LLEO_I": "Lower LEO/Intermediate",
  "LEO_S": "Upper LEO/Sun-Sync",
  "LEO_I": "Upper LEO/Intermediate",
  "GEO_S": "Stationary GEO",
  "GEO_D": "Drift GEO",
  "LLEO_P": "Lower LEO/Polar"
};

// 状态类型映射
export const STATUS_MAPPING = {
  "Operational": "正在运行",
  "Nonoperational": "非运行",
  "Decayed": "已失效",
  "Unknown": "未知",
  "Partially Operational": "部分运行",
  "Extended Mission": "延长任务"
};

export default EXTENDED_SATELLITE_DATABASE;