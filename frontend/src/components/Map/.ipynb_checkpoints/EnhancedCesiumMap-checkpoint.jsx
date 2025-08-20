// src/components/Map/EnhancedCesiumMap.jsx - 修复地球静止轨道卫星版本
import React, { useEffect, useRef, useState, useCallback } from 'react';
import 'cesium/Build/Cesium/Widgets/widgets.css';
// 6.20
import { getSatelliteInfo, getSatelliteOrbitParams,findSatelliteInfo } from '../../config/satelliteDatabase';
// import { 
//   getSatelliteInfo, 
//   getSatelliteOrbitParams,
//   getSatelliteOrbitParamsAsync,
//   getSatelliteInfoAsync,
//   preloadSatelliteParams
// } from '../../config/satelliteDatabase';
// 6.20
import { normalizeSatelliteName } from '../../services/satelliteExtractor';

// 轨道运动计算器
const OrbitCalculator = {
  // 地球引力常数 (m^3/s^2)
  GM: 3.986004418e14,

  // 地球半径 (m)
  EARTH_RADIUS: 6378137,

  // 地球自转角速度 (rad/s)
  EARTH_ROTATION_RATE: 7.2921159e-5,

  // 计算平均运动（弧度/秒）
  getMeanMotion: (semiMajorAxis) => {
    return Math.sqrt(OrbitCalculator.GM / Math.pow(semiMajorAxis, 3));
  },

  // 计算轨道周期（秒）
  getOrbitPeriod: (semiMajorAxis) => {
    return 2 * Math.PI / OrbitCalculator.getMeanMotion(semiMajorAxis);
  },

  // 计算给定时间的平近点角
  getMeanAnomaly: (initialMeanAnomaly, meanMotion, elapsedTime) => {
    return (initialMeanAnomaly + meanMotion * elapsedTime) % (2 * Math.PI);
  },

  // 求解开普勒方程得到偏近点角
  getEccentricAnomaly: (meanAnomaly, eccentricity, tolerance = 1e-8) => {
    let E = meanAnomaly;
    let delta = 1;
    let iterations = 0;

    while (Math.abs(delta) > tolerance && iterations < 100) {
      delta = (E - eccentricity * Math.sin(E) - meanAnomaly) / (1 - eccentricity * Math.cos(E));
      E -= delta;
      iterations++;
    }

    return E;
  },

  // 计算真近点角
  getTrueAnomaly: (eccentricAnomaly, eccentricity) => {
    const x = Math.cos(eccentricAnomaly) - eccentricity;
    const y = Math.sqrt(1 - eccentricity * eccentricity) * Math.sin(eccentricAnomaly);
    return Math.atan2(y, x);
  },

  // 计算轨道坐标系中的位置
  getOrbitPosition: (semiMajorAxis, eccentricity, trueAnomaly) => {
    const r = semiMajorAxis * (1 - eccentricity * eccentricity) / (1 + eccentricity * Math.cos(trueAnomaly));
    return {
      x: r * Math.cos(trueAnomaly),
      y: r * Math.sin(trueAnomaly),
      z: 0
    };
  },

  // 将轨道坐标转换为惯性坐标（ECI）
  convertToInertial: (position, inclination, rightAscension, argumentOfPeriapsis, Cesium) => {
    // 转换角度为弧度
    const i = Cesium.Math.toRadians(inclination);
    const omega = Cesium.Math.toRadians(rightAscension);
    const w = Cesium.Math.toRadians(argumentOfPeriapsis);

    // 创建旋转矩阵
    const cos_i = Math.cos(i);
    const sin_i = Math.sin(i);
    const cos_omega = Math.cos(omega);
    const sin_omega = Math.sin(omega);
    const cos_w = Math.cos(w);
    const sin_w = Math.sin(w);

    // 应用三次旋转：升交点赤经 -> 倾角 -> 近地点辐角
    const x = position.x * (cos_omega * cos_w - sin_omega * sin_w * cos_i) -
      position.y * (cos_omega * sin_w + sin_omega * cos_w * cos_i);
    const y = position.x * (sin_omega * cos_w + cos_omega * sin_w * cos_i) -
      position.y * (sin_omega * sin_w - cos_omega * cos_w * cos_i);
    const z = position.x * (sin_w * sin_i) + position.y * (cos_w * sin_i);

    return new Cesium.Cartesian3(x, y, z);
  },

  // 检查是否为地球静止轨道
  isGeostationaryOrbit: (semiMajorAxis, inclination, eccentricity) => {
    const altitudeKm = (semiMajorAxis - OrbitCalculator.EARTH_RADIUS) / 1000;
    // 地球静止轨道：高度约35786km，倾角接近0°，偏心率接近0
    return (altitudeKm > 35000 && altitudeKm < 36500 &&
      Math.abs(inclination) < 5 && eccentricity < 0.01);
  },

  // 🔧 修复：计算卫星在给定时间的位置（修复地球静止轨道）
  getSatellitePosition: (orbitParams, time, Cesium) => {
    const {
      semiMajorAxis,
      eccentricity,
      inclination,
      rightAscension,
      argumentOfPeriapsis,
      meanAnomaly,
      orbitPeriod
    } = orbitParams;

    const isGeostationary = OrbitCalculator.isGeostationaryOrbit(
      semiMajorAxis, inclination, eccentricity
    );

    // 🔧 修复：地球静止轨道特殊处理 - 在FIXED坐标系中保持静止
    if (isGeostationary) {
      // 使用固定经度位置，不随时间变化
      const fixedLongitude = rightAscension || 105; // 默认东经105度
      const longitude = Cesium.Math.toRadians(fixedLongitude);

      // 在FIXED坐标系中，地球静止轨道卫星相对地球表面静止
      return Cesium.Cartesian3.fromRadians(longitude, 0, semiMajorAxis - OrbitCalculator.EARTH_RADIUS);
    }

    // 非静止轨道使用真实轨道周期
    const realPeriod = orbitPeriod || OrbitCalculator.getOrbitPeriod(semiMajorAxis);
    const n = 2 * Math.PI / realPeriod; // 使用真实周期计算平均运动

    // 计算当前时刻的平近点角
    const M = OrbitCalculator.getMeanAnomaly(Cesium.Math.toRadians(meanAnomaly), n, time);
    const E = OrbitCalculator.getEccentricAnomaly(M, eccentricity);
    const v = OrbitCalculator.getTrueAnomaly(E, eccentricity);
    const orbitPos = OrbitCalculator.getOrbitPosition(semiMajorAxis, eccentricity, v);

    return OrbitCalculator.convertToInertial(orbitPos, inclination, rightAscension, argumentOfPeriapsis, Cesium);
  },

  // 🔧 修复：生成轨道路径（地球静止轨道显示完整圆形轨道）
  generateOrbitPath: (orbitParams, numPoints = 360, Cesium) => {
    const positions = [];
    const { semiMajorAxis, inclination, eccentricity, rightAscension } = orbitParams;

    const isGeostationary = OrbitCalculator.isGeostationaryOrbit(
      semiMajorAxis, inclination, eccentricity
    );

    if (isGeostationary) {
      // 🔧 修复：为地球静止轨道生成赤道圆形轨道
      const radius = semiMajorAxis - OrbitCalculator.EARTH_RADIUS;
      for (let i = 0; i <= numPoints; i++) {
        const longitude = (i / numPoints) * 2 * Math.PI;
        const position = Cesium.Cartesian3.fromRadians(longitude, 0, radius);
        positions.push(position);
      }
    } else {
      // 非静止轨道的常规轨道生成
      const period = OrbitCalculator.getOrbitPeriod(semiMajorAxis);
      for (let i = 0; i <= numPoints; i++) {
        const time = (i / numPoints) * period;
        const position = OrbitCalculator.getSatellitePosition(orbitParams, time, Cesium);
        positions.push(position);
      }
    }

    return positions;
  },

  // 计算卫星到达轨道上某个位置需要的时间
  getTimeToReachPosition: (clickedPosition, currentTime, orbitParams, satelliteName, Cesium) => {
    const { semiMajorAxis, eccentricity, inclination, orbitPeriod, rightAscension, argumentOfPeriapsis, meanAnomaly } = orbitParams;

    // 检查是否为地球静止轨道
    const isGeostationary = OrbitCalculator.isGeostationaryOrbit(semiMajorAxis, inclination, eccentricity);
    if (isGeostationary) {
      return 0; // 地球静止轨道卫星相对地球静止，没有到达时间的概念
    }

    // 计算轨道周期
    const period = orbitPeriod || OrbitCalculator.getOrbitPeriod(semiMajorAxis);
    const n = 2 * Math.PI / period; // 平均运动

    // 获取卫星当前位置
    const currentPosition = OrbitCalculator.getSatellitePosition(orbitParams, currentTime, Cesium);

    // 计算当前位置和点击位置在轨道平面上的角度
    // 首先需要将位置投影到轨道平面
    const orbitNormal = new Cesium.Cartesian3(
      Math.sin(Cesium.Math.toRadians(inclination)) * Math.sin(Cesium.Math.toRadians(rightAscension)),
      -Math.sin(Cesium.Math.toRadians(inclination)) * Math.cos(Cesium.Math.toRadians(rightAscension)),
      Math.cos(Cesium.Math.toRadians(inclination))
    );

    // 计算轨道平面的参考方向（升交点方向）
    const ascendingNode = new Cesium.Cartesian3(
      Math.cos(Cesium.Math.toRadians(rightAscension)),
      Math.sin(Cesium.Math.toRadians(rightAscension)),
      0
    );

    // 计算当前位置在轨道平面内的角度
    const currentPosProj = Cesium.Cartesian3.subtract(
      currentPosition,
      Cesium.Cartesian3.multiplyByScalar(
        orbitNormal,
        Cesium.Cartesian3.dot(currentPosition, orbitNormal),
        new Cesium.Cartesian3()
      ),
      new Cesium.Cartesian3()
    );

    // 计算目标位置在轨道平面内的角度
    const targetPosProj = Cesium.Cartesian3.subtract(
      clickedPosition,
      Cesium.Cartesian3.multiplyByScalar(
        orbitNormal,
        Cesium.Cartesian3.dot(clickedPosition, orbitNormal),
        new Cesium.Cartesian3()
      ),
      new Cesium.Cartesian3()
    );

    // 归一化
    Cesium.Cartesian3.normalize(currentPosProj, currentPosProj);
    Cesium.Cartesian3.normalize(targetPosProj, targetPosProj);

    // 计算角度差
    const dotProduct = Cesium.Cartesian3.dot(currentPosProj, targetPosProj);
    const crossProduct = Cesium.Cartesian3.cross(currentPosProj, targetPosProj, new Cesium.Cartesian3());
    const crossDotNormal = Cesium.Cartesian3.dot(crossProduct, orbitNormal);

    let angleDiff = Math.acos(Math.max(-1, Math.min(1, dotProduct)));

    // 确定角度方向（顺轨道方向为正）
    if (crossDotNormal < 0) {
      angleDiff = 2 * Math.PI - angleDiff;
    }

    // 计算时间（角度差 / 角速度）
    const angularVelocity = n; // 平均角速度
    const timeToReach = angleDiff / angularVelocity;

    console.log(`📊 轨道计算详情:`, {
      卫星: satelliteName,
      当前时间: currentTime,
      轨道周期: `${(period / 60).toFixed(1)}分钟`,
      角度差: `${Cesium.Math.toDegrees(angleDiff).toFixed(1)}°`,
      到达时间: `${timeToReach.toFixed(0)}秒 (${(timeToReach / 60).toFixed(1)}分钟)`
    });

    return timeToReach;
  },

  // 获取轨道上最近的点
  getClosestPointOnOrbit: (clickPosition, orbitParams, Cesium) => {
    // 生成轨道路径上的多个点（增加采样点数以提高精度）
    const orbitPoints = OrbitCalculator.generateOrbitPath(orbitParams, 720, Cesium); // 增加到720个点

    let closestPoint = null;
    let minDistance = Infinity;
    let closestIndex = -1;

    // 找到最近的轨道点
    for (let i = 0; i < orbitPoints.length; i++) {
      const distance = Cesium.Cartesian3.distance(clickPosition, orbitPoints[i]);
      if (distance < minDistance) {
        minDistance = distance;
        closestPoint = orbitPoints[i];
        closestIndex = i;
      }
    }

    // 在最近点附近进行插值以获得更精确的位置
    if (closestIndex > 0 && closestIndex < orbitPoints.length - 1) {
      const prevPoint = orbitPoints[closestIndex - 1];
      const nextPoint = orbitPoints[closestIndex + 1];

      // 使用二次插值找到更精确的最近点
      const t = 0.5; // 可以通过优化算法确定最佳t值
      closestPoint = Cesium.Cartesian3.lerp(
        Cesium.Cartesian3.lerp(prevPoint, closestPoint, t, new Cesium.Cartesian3()),
        Cesium.Cartesian3.lerp(closestPoint, nextPoint, t, new Cesium.Cartesian3()),
        t,
        new Cesium.Cartesian3()
      );
    }

    // 计算该点对应的轨道相位（0到1）
    const phase = closestIndex / orbitPoints.length;

    return {
      point: closestPoint,
      phase: phase,
      distance: minDistance,
      index: closestIndex
    };
  }
};

// 默认视角配置
const DEFAULT_VIEW = {
  longitude: 104.0,
  latitude: 35.0,
  height: 20000000
};

const EnhancedCesiumMap = ({
  location,
  visible,
  satelliteNames = [],
  onSatelliteClick
}) => {
  const cesiumContainerRef = useRef(null);
  const viewerRef = useRef(null);
  const cesiumLoadedRef = useRef(false);
  const cesiumRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);
  const [satelliteInfo, setSatelliteInfo] = useState(null);
  const [showPopup, setShowPopup] = useState(false);
  const [popupPosition, setPopupPosition] = useState({ top: 500, right: 25 });
  const customSatellitesRef = useRef([]);
  const prevVisibleRef = useRef(visible);
  const animationFrameRef = useRef(null);
  const startTimeRef = useRef(null);

  // 获取增强的卫星颜色
  const getEnhancedSatelliteColor = (index, total, satelliteName) => {
    const Cesium = cesiumRef.current;
    if (!Cesium) return null;

    const satelliteInfo = getSatelliteInfo(satelliteName);

    if (satelliteInfo.country === '中国') {
      const colors = [
        Cesium.Color.CRIMSON,
        Cesium.Color.DARKRED,
        Cesium.Color.INDIANRED
      ];
      return colors[index % colors.length];
    } else if (satelliteInfo.country === '欧洲') {
      const colors = [
        Cesium.Color.ROYALBLUE,
        Cesium.Color.DODGERBLUE,
        Cesium.Color.DEEPSKYBLUE
      ];
      return colors[index % colors.length];
    } else if (satelliteInfo.country === '美国') {
      const colors = [
        Cesium.Color.FORESTGREEN,
        Cesium.Color.SEAGREEN,
        Cesium.Color.LIMEGREEN
      ];
      return colors[index % colors.length];
    } else {
      const colors = [
        Cesium.Color.MEDIUMPURPLE,
        Cesium.Color.MEDIUMORCHID,
        Cesium.Color.DARKORCHID
      ];
      return colors[index % colors.length];
    }
  };

  // 清除所有自定义卫星
  const clearCustomSatellites = () => {
    if (!viewerRef.current) return;

    const entitiesToRemove = [];
    viewerRef.current.entities.values.forEach(entity => {
      if (entity.id && (entity.id.includes('satellite_') || entity.id.includes('orbit_'))) {
        entitiesToRemove.push(entity);
      }
    });

    entitiesToRemove.forEach(entity => {
      viewerRef.current.entities.remove(entity);
    });

    customSatellitesRef.current = [];

    if (viewerRef.current.scene) {
      viewerRef.current.scene.requestRender();
    }

    console.log(`🧹 清除了 ${entitiesToRemove.length} 个卫星实体`);
  };

  // 🔧 修复：添加动态卫星和轨道（修复地球静止轨道）
  // 6.20
  const addDynamicSatellite = (name, index, total) => {
    const Cesium = cesiumRef.current;
    if (!Cesium || !viewerRef.current) return;

      const satelliteResult = findSatelliteInfo(name);

  if (!satelliteResult) {
    console.warn(`无法找到卫星信息: ${name}`);
    return;
  }

  const satelliteInfo = satelliteResult.data;
  const standardName = satelliteInfo.fullName || satelliteResult.key;
  const orbitParams = satelliteInfo.orbitParams || getSatelliteOrbitParams(name);

  console.log(`➕ 添加动态卫星: ${standardName} (原始名称: ${name}, 匹配类型: ${satelliteResult.matchType})`);

    // const orbitParams = getSatelliteOrbitParams(name);
    // const satelliteInfo = getSatelliteInfo(name);
    const color = getEnhancedSatelliteColor(index, total, name);

  // const addDynamicSatellite = async (name, index, total) => {
  //   const Cesium = cesiumRef.current;
  //   if (!Cesium || !viewerRef.current) return;

  //   // 🆕 使用异步获取轨道参数
  //   const orbitParams = await getSatelliteOrbitParamsAsync(name);
  //   const satelliteInfo = await getSatelliteInfoAsync(name);
  //   const color = getEnhancedSatelliteColor(index, total, name);
// 6.20

    const { semiMajorAxis, inclination, eccentricity, orbitPeriod } = orbitParams;
    const isGeostationary = OrbitCalculator.isGeostationaryOrbit(
      semiMajorAxis, inclination, eccentricity
    );

    const altitudeKm = (semiMajorAxis - OrbitCalculator.EARTH_RADIUS) / 1000;
    const orbitPeriodMinutes = (orbitPeriod || OrbitCalculator.getOrbitPeriod(semiMajorAxis)) / 60;

    console.log(`➕ 添加动态卫星: ${name}`, {
      轨道高度: `${altitudeKm.toFixed(0)}km`,
      轨道倾角: `${inclination}°`,
      轨道周期: `${orbitPeriodMinutes.toFixed(1)}分钟`,
      是否静止轨道: isGeostationary,
      半长轴: `${semiMajorAxis}m`
    });

    // 生成轨道路径
    const orbitPositions = OrbitCalculator.generateOrbitPath(orbitParams, 360, Cesium);

    if (orbitPositions.length > 0) {
      // 添加轨道线
      const orbitEntity = viewerRef.current.entities.add({
        id: `orbit_${name}_${Date.now()}`,
        name: `${name}_orbit`,
        polyline: {
          positions: orbitPositions,
          width: 10,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.1,
            color: color.withAlpha(0.8),
            taperPower: 1
          }),
          clampToGround: false
        }
      });
      // const orbitEntity = viewerRef.current.entities.add({
      //   id: `orbit_${name}_${Date.now()}`,
      //   name: `${name}_orbit`,
      //   polyline: {
      //     positions: orbitPositions,
      //     width: isGeostationary ? 1.5 : 0.75,  // 减小线宽
      //     material: color,  // 直接使用纯色材质，不使用发光效果
      //     clampToGround: false
      //   }
      // });

      customSatellitesRef.current.push(orbitEntity);
    }

    // 🔧 修复：使用不同的位置计算策略
    let dynamicPosition;

    if (isGeostationary) {
      // 🔧 地球静止轨道：使用FIXED坐标系中的固定位置
      const fixedLongitude = orbitParams.rightAscension || 105; // 默认东经105度
      const height = semiMajorAxis - OrbitCalculator.EARTH_RADIUS;

      // 在FIXED坐标系中创建固定位置
      dynamicPosition = Cesium.Cartesian3.fromDegrees(fixedLongitude, 0, height);

      console.log(`🛰️ 地球静止轨道卫星 ${name} 固定位置: 经度${fixedLongitude}°, 高度${height / 1000}km`);
    } else {
      // 非地球静止轨道：使用动态计算位置
      dynamicPosition = new Cesium.CallbackProperty(function (time, result) {
        if (!startTimeRef.current) {
          startTimeRef.current = time;
        }

        const elapsedTime = Cesium.JulianDate.secondsDifference(time, startTimeRef.current);
        const position = OrbitCalculator.getSatellitePosition(orbitParams, elapsedTime, Cesium);

        return position;
      }, false);
    }

    // 🔧 修复：创建动态方向属性
    let dynamicOrientation;

    if (isGeostationary) {
      // 地球静止轨道：固定朝向
      const fixedLongitude = orbitParams.rightAscension || 105;
      const height = semiMajorAxis - OrbitCalculator.EARTH_RADIUS;
      const fixedPosition = Cesium.Cartesian3.fromDegrees(fixedLongitude, 0, height);

      // 使用 HeadingPitchRoll 来定义朝向
      // heading: 0 = 朝北, pitch: -90 = 平行于地面, roll: 0 = 不倾斜
      const hpr = new Cesium.HeadingPitchRoll(
        Cesium.Math.toRadians(0),    // heading: 朝北
        Cesium.Math.toRadians(0),   // pitch: 向下倾斜90度使其平行于地面
        Cesium.Math.toRadians(0)      // roll: 无滚转
      );

      // 获取该位置的变换矩阵
      const transform = Cesium.Transforms.eastNorthUpToFixedFrame(fixedPosition);
      const rotation = Cesium.Matrix3.fromHeadingPitchRoll(hpr);
      const rotationMatrix = Cesium.Matrix4.multiplyByMatrix3(transform, rotation, new Cesium.Matrix4());

      dynamicOrientation = Cesium.Quaternion.fromRotationMatrix(Cesium.Matrix4.getMatrix3(rotationMatrix, new Cesium.Matrix3()));
    } else {
      // 非静止轨道：动态计算方向
      dynamicOrientation = new Cesium.CallbackProperty(function (time, result) {
        if (!startTimeRef.current) {
          startTimeRef.current = time;
        }

        const elapsedTime = Cesium.JulianDate.secondsDifference(time, startTimeRef.current);
        const currentPos = OrbitCalculator.getSatellitePosition(orbitParams, elapsedTime, Cesium);
        const futurePos = OrbitCalculator.getSatellitePosition(orbitParams, elapsedTime + 60, Cesium);

        // 计算速度方向
        const velocity = Cesium.Cartesian3.subtract(futurePos, currentPos, new Cesium.Cartesian3());
        Cesium.Cartesian3.normalize(velocity, velocity);

        // 获取位置的本地坐标系
        const transform = Cesium.Transforms.eastNorthUpToFixedFrame(currentPos);

        // 计算航向角（速度矢量在水平面上的投影方向）
        const velocityENU = Cesium.Matrix4.multiplyByPointAsVector(
          Cesium.Matrix4.inverse(transform, new Cesium.Matrix4()),
          velocity,
          new Cesium.Cartesian3()
        );

        const heading = Math.atan2(velocityENU.x, velocityENU.y);

        // 使用 HeadingPitchRoll
        const hpr = new Cesium.HeadingPitchRoll(
          heading,                        // 朝向速度方向
          Cesium.Math.toRadians(0),    // 俯仰角：-90度使模型平行于地面
          Cesium.Math.toRadians(0)       // 滚转角：0
        );

        const rotation = Cesium.Matrix3.fromHeadingPitchRoll(hpr);
        const rotationMatrix = Cesium.Matrix4.multiplyByMatrix3(transform, rotation, new Cesium.Matrix4());

        return Cesium.Quaternion.fromRotationMatrix(Cesium.Matrix4.getMatrix3(rotationMatrix, new Cesium.Matrix3()));
      }, false);
    }

    // 根据轨道高度调整模型大小
    let modelScale = 30000;  // 基础大小增加2.5倍
    if (isGeostationary) {
      modelScale = 75000;  // 静止轨道卫星更大
    } else if (altitudeKm < 600) {
      modelScale = 20000;
    } else if (altitudeKm < 1000) {
      modelScale = 30000;
    } else {
      modelScale = 45000;
    }

    // 添加卫星实体
    const satelliteEntity = viewerRef.current.entities.add({
      id: `satellite_${name}_${Date.now()}`,
      name: name,
      position: dynamicPosition,
      orientation: dynamicOrientation,

      // 使用3D模型
      model: {
        uri: '/satellite.glb',
        minimumPixelSize: isGeostationary ? 150 : 120,
        maximumScale: isGeostationary ? 20000 : 8000,
        scale: satelliteInfo.country === '中国' ? modelScale * 2.5 : modelScale,

        nodeTransformations: {
          'Satellite': {
            rotation: {
              x: 0,  // 旋转90度使其平行于地球表面
              y: Cesium.Math.toRadians(90),
              z: 0
            }
          }
        },

        // 距离显示缩放
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 100000000),
      },

      // 标签
      label: {
        text: `🛰️ ${name}${isGeostationary ? ' (静止轨道)' : ''}`,
        font: "bold 28px 'Segoe UI', 'SF Pro Display', Arial, sans-serif",
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -80),
        scaleByDistance: new Cesium.NearFarScalar(1000000, 1.2, 30000000, 0.4),
        heightReference: Cesium.HeightReference.NONE,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        backgroundColor: Cesium.Color.fromCssColorString('rgba(0, 0, 0, 0.7)'),
        backgroundPadding: new Cesium.Cartesian2(10, 6),
        showBackground: true
      },

      // 描述信息
      description: `
        <div style="font-family: 'SF Pro Display', 'Segoe UI', Arial, sans-serif; max-width: 450px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
          <div style="text-align: center; margin-bottom: 20px;">
            <h3 style="color: #FFD700; margin: 0; font-size: 20px; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">
              🚀 ${name}
            </h3>
            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">${satelliteInfo.englishName}</p>
          </div>
          
          <div style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 15px; backdrop-filter: blur(10px);">
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
              <tr style="background: rgba(255,255,255,0.1);">
                <td style="padding: 10px; border-radius: 4px; font-weight: bold; color: #FFD700;">🗓️ 发射日期</td>
                <td style="padding: 10px;">${satelliteInfo.launchDate}</td>
              </tr>
              <tr>
                <td style="padding: 10px; font-weight: bold; color: #FFD700;">🌍 所属国家</td>
                <td style="padding: 10px;">${satelliteInfo.country}</td>
              </tr>
              <tr style="background: rgba(255,255,255,0.1);">
                <td style="padding: 10px; border-radius: 4px; font-weight: bold; color: #FFD700;">🛰️ 轨道高度</td>
                <td style="padding: 10px;">${altitudeKm.toFixed(0)} 公里</td>
              </tr>
              <tr>
                <td style="padding: 10px; font-weight: bold; color: #FFD700;">📐 轨道倾角</td>
                <td style="padding: 10px;">${inclination}°</td>
              </tr>
              <tr style="background: rgba(255,255,255,0.1);">
                <td style="padding: 10px; border-radius: 4px; font-weight: bold; color: #FFD700;">🔍 分辨率</td>
                <td style="padding: 10px;">${satelliteInfo.resolution}</td>
              </tr>
              <tr>
                <td style="padding: 10px; font-weight: bold; color: #FFD700;">⏱️ 轨道周期</td>
                <td style="padding: 10px;">${orbitPeriodMinutes.toFixed(1)} 分钟</td>
              </tr>
              <tr style="background: rgba(255,255,255,0.1);">
                <td style="padding: 10px; border-radius: 4px; font-weight: bold; color: #FFD700;">⚡ 轨道类型</td>
                <td style="padding: 10px;">${isGeostationary ? '地球静止轨道' : '非静止轨道'}</td>
              </tr>
            </table>
          </div>
          
          <div style="margin-top: 15px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px; border-left: 4px solid #FFD700;">
            <p style="margin: 0; font-style: italic; line-height: 1.6; font-size: 13px;">
              ${satelliteInfo.description}
            </p>
          </div>
        </div>
      `
    });

    customSatellitesRef.current.push(satelliteEntity);
  };

  // 更新卫星实体
  // 6.20
  const updateSatelliteEntities = useCallback((names) => {
    const Cesium = cesiumRef.current;
    if (!viewerRef.current || !Cesium) return;

    console.log('🔄 更新动态卫星实体:', names);

       // 增强的卫星名称标准化和去重
  const normalizedMap = new Map(); // 使用Map来追踪标准化结果

  names.forEach(name => {
    const normalized = normalizeSatelliteName(name);
    // 使用标准化后的名称作为键，避免重复
    if (!normalizedMap.has(normalized)) {
      normalizedMap.set(normalized, name); // 保存原始名称用于调试
    }
  });

  const uniqueNames = Array.from(normalizedMap.keys());
    // // 卫星名称标准化和去重
    // const normalizedNames = new Set();
    // names.forEach(name => {
    //   const normalized = normalizeSatelliteName(name);
    //   normalizedNames.add(normalized);
    // });
    // const uniqueNames = Array.from(normalizedNames);

    // console.log('🔄 标准化后的卫星列表:', uniqueNames);
      const activeSatellites = uniqueNames.filter(name => {
  const info = getSatelliteInfo(name);
  return info?.status === "在轨运行";
});

    // 清除所有现有卫星
    clearCustomSatellites();

    // 重置开始时间
    startTimeRef.current = null;
//8.4
    // 添加新卫星
    // uniqueNames.forEach((name, index) => {
    //   console.log(`➕ 添加动态卫星 ${index + 1}/${uniqueNames.length}:`, name);
    //   addDynamicSatellite(name, index, uniqueNames.length);
    // });
      activeSatellites.forEach((name, index) => {
  console.log(`➕ 添加在轨卫星 ${index + 1}/${activeSatellites.length}:`, name);
  addDynamicSatellite(name, index, activeSatellites.length);
});
      //8.4

    // 强制渲染更新
    if (viewerRef.current.scene) {
      viewerRef.current.scene.requestRender();
    }

  // const updateSatelliteEntities = useCallback(async (names) => {
  //   const Cesium = cesiumRef.current;
  //   if (!viewerRef.current || !Cesium) return;

  //   console.log('🔄 更新动态卫星实体:', names);

  //   // 🆕 预加载所有卫星参数
  //   await preloadSatelliteParams(names);

  //   // 卫星名称标准化和去重
  //   const normalizedNames = new Set();
  //   names.forEach(name => {
  //     const normalized = normalizeSatelliteName(name);
  //     normalizedNames.add(normalized);
  //   });
  //   const uniqueNames = Array.from(normalizedNames);

  //   console.log('🔄 标准化后的卫星列表:', uniqueNames);

  //   // 清除所有现有卫星
  //   clearCustomSatellites();

  //   // 重置开始时间
  //   startTimeRef.current = null;

  //   // 🆕 使用 Promise.all 并行添加卫星
  //   const addPromises = uniqueNames.map((name, index) => {
  //     console.log(`➕ 添加动态卫星 ${index + 1}/${uniqueNames.length}:`, name);
  //     return addDynamicSatellite(name, index, uniqueNames.length);
  //   });

  //   await Promise.all(addPromises);

  //   // 强制渲染更新
  //   if (viewerRef.current.scene) {
  //     viewerRef.current.scene.requestRender();
  //   }
    // 6.20

    // 开始动画
    viewerRef.current.clock.shouldAnimate = true;

    // 智能调整视角
    if (names.length > 0) {
      let maxAltitude = 800;
      let minAltitude = 200;
      let hasGeostationary = false;

      names.forEach(name => {
        const orbitParams = getSatelliteOrbitParams(name);
        const altitudeKm = (orbitParams.semiMajorAxis - OrbitCalculator.EARTH_RADIUS) / 1000;

        if (altitudeKm > maxAltitude) {
          maxAltitude = altitudeKm;
        }
        if (altitudeKm < minAltitude) {
          minAltitude = altitudeKm;
        }

        // 检查是否有地球静止轨道卫星
        if (OrbitCalculator.isGeostationaryOrbit(
          orbitParams.semiMajorAxis, orbitParams.inclination, orbitParams.eccentricity
        )) {
          hasGeostationary = true;
        }
      });

      let viewHeight;
      if (hasGeostationary) {
        viewHeight = Math.max(100000000, maxAltitude * 1000 * 4);
      } else if (maxAltitude > 10000) {
        viewHeight = Math.max(50000000, maxAltitude * 1000 * 3);
      } else if (names.length > 3) {
        viewHeight = Math.max(25000000, maxAltitude * 1000 * 4);
      } else {
        viewHeight = Math.max(15000000, maxAltitude * 1000 * 3);
      }

      viewerRef.current.scene.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(location ? 104.0 : 0, location ? 35.0 : 0, viewHeight),
        orientation: {
          heading: 0,
          pitch: -Cesium.Math.PI_OVER_TWO,
          roll: 0
        },
        duration: 2.5
      });

      console.log(`🎯 智能调整视角: 视距=${(viewHeight / 1000).toFixed(0)}km, 卫星数量=${names.length}, 最高轨道=${maxAltitude.toFixed(0)}km, 有静止轨道=${hasGeostationary}`);
    }

    if (names.length === 0 && !location) {
      viewerRef.current.scene.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          DEFAULT_VIEW.longitude,
          DEFAULT_VIEW.latitude,
          DEFAULT_VIEW.height
        ),
        orientation: {
          heading: 0,
          pitch: -Cesium.Math.PI_OVER_TWO,
          roll: 0
        },
        duration: 2.0
      });
      return;
    }
  }, [location]);

  // 处理卫星点击事件
  // 6.20
  const handleSatelliteClick = async (entityName, screenPosition, clickedEntity, clickPosition) => {
    console.log("🖱️ 点击实体:", entityName);

    // 检查是否是轨道实体
    const isOrbit = entityName.endsWith('_orbit');
    let satelliteName = entityName;

    // 如果是轨道，提取卫星名称
    if (isOrbit) {
      satelliteName = entityName.replace('_orbit', '');
      console.log("🛤️ 点击的是轨道，对应卫星:", satelliteName);
    }

    setPopupPosition({
      top: screenPosition.y,
      right: cesiumContainerRef.current.clientWidth - screenPosition.x
    });


      const satelliteInfoData = getSatelliteInfo(satelliteName);
    const orbitParams = getSatelliteOrbitParams(satelliteName);

  // const handleSatelliteClick = async (entityName, screenPosition, clickedEntity, clickPosition) => {
  //   console.log("🖱️ 点击实体:", entityName);

  //   // 检查是否是轨道实体
  //   const isOrbit = entityName.endsWith('_orbit');
  //   let satelliteName = entityName;

  //   // 如果是轨道，提取卫星名称
  //   if (isOrbit) {
  //     satelliteName = entityName.replace('_orbit', '');
  //     console.log("🛤️ 点击的是轨道，对应卫星:", satelliteName);
  //   }

  //   setPopupPosition({
  //     top: screenPosition.y,
  //     right: cesiumContainerRef.current.clientWidth - screenPosition.x
  //   });

  //   // 🆕 使用异步获取卫星信息
  //   const satelliteInfoData = await getSatelliteInfoAsync(satelliteName);
  //   const orbitParams = await getSatelliteOrbitParamsAsync(satelliteName);
      // 6.20



    // 使用卫星数据库中的实际高度信息
    let altitude = satelliteInfoData.altitude;

    // 如果数据库中没有高度信息，才计算
    if (!altitude || altitude === '未知') {
      const calculatedAltitude = ((orbitParams.semiMajorAxis - OrbitCalculator.EARTH_RADIUS) / 1000).toFixed(0);
      altitude = `${calculatedAltitude}公里`;
    }

    // 🆕 新增：如果点击的是轨道且有点击位置，计算到达时间
    let timeToReach = null;
    if (isOrbit && clickPosition && cesiumRef.current) {
      const Cesium = cesiumRef.current;

      // 获取当前时间（使用动画时间而不是真实时间）
      const currentTime = viewerRef.current.clock.currentTime;
      const elapsedTime = startTimeRef.current ?
        Cesium.JulianDate.secondsDifference(currentTime, startTimeRef.current) : 0;

      // 获取轨道上最近的点
      const closestPointInfo = OrbitCalculator.getClosestPointOnOrbit(clickPosition, orbitParams, Cesium);

      if (closestPointInfo && closestPointInfo.distance < 1000000) { // 如果点击位置距离轨道小于1000km
        // 计算到达时间
        timeToReach = OrbitCalculator.getTimeToReachPosition(
          closestPointInfo.point,
          elapsedTime,
          orbitParams,
          satelliteName, // 添加卫星名称参数
          Cesium
        );

        console.log(`⏱️ ${satelliteName} 到达点击位置需要: ${timeToReach.toFixed(0)}秒`);
      }
    }

    // 根据是否点击轨道来设置不同的信息
    if (isOrbit) {
      // 点击轨道时，显示轨道相关信息和到达时间
      setSatelliteInfo({
        name: `${satelliteName} - 轨道`,
        orbit: satelliteInfoData.orbit,
        altitude: altitude,
        inclination: satelliteInfoData.inclination || `${orbitParams.inclination}°`,
        period: (() => {
          const totalSeconds = orbitParams.orbitPeriod || OrbitCalculator.getOrbitPeriod(orbitParams.semiMajorAxis);
          const hours = Math.floor(totalSeconds / 3600);
          const minutes = Math.floor((totalSeconds % 3600) / 60);
          const seconds = Math.round(totalSeconds % 60);

          // 根据时长选择合适的显示格式
          if (hours > 0) {
            return `${hours}小时${minutes}分钟${seconds}秒`;
          } else if (minutes > 0) {
            return `${minutes}分钟${seconds}秒`;
          } else {
            return `${seconds}秒`;
          }
        })(),
        timeToReach: timeToReach, // 🆕 添加到达时间
        isOrbitInfo: true,
        // 添加时间戳确保状态更新
        _timestamp: Date.now()
      });
    } else {
      // 点击卫星时，显示完整信息
      setSatelliteInfo({
        name: satelliteName,
        launchDate: satelliteInfoData.launchDate,
        country: satelliteInfoData.country,
        status: satelliteInfoData.status,
        orbit: satelliteInfoData.orbit,
        altitude: altitude,
        inclination: satelliteInfoData.inclination || `${orbitParams.inclination}°`,
        resolution: satelliteInfoData.resolution,
        applications: satelliteInfoData.applications,
        description: satelliteInfoData.description,
        period: (() => {
          const totalSeconds = orbitParams.orbitPeriod || OrbitCalculator.getOrbitPeriod(orbitParams.semiMajorAxis);
          const hours = Math.floor(totalSeconds / 3600);
          const minutes = Math.floor((totalSeconds % 3600) / 60);
          const seconds = Math.round(totalSeconds % 60);

          // 根据时长选择合适的显示格式
          if (hours > 0) {
            return `${hours}小时${minutes}分钟${seconds}秒`;
          } else if (minutes > 0) {
            return `${minutes}分钟${seconds}秒`;
          } else {
            return `${seconds}秒`;
          }
        })(),
        isOrbitInfo: false,
        // 添加时间戳确保状态更新
        _timestamp: Date.now()
      });
    }

    setShowPopup(true);

    if (onSatelliteClick) {
      onSatelliteClick(satelliteName);
    }
  };
  const [pendingSatellites, setPendingSatellites] = useState([]);
  // Cesium初始化
  useEffect(() => {
    if (prevVisibleRef.current === visible && !visible) return;
    prevVisibleRef.current = visible;

    if (!cesiumContainerRef.current || !visible) return;

    if (cesiumLoadedRef.current && viewerRef.current) {
      console.log("Cesium已经加载，不重新初始化");

      // 🔧 新增：检查是否有卫星数据需要显示
      if (satelliteNames && satelliteNames.length > 0) {
        console.log("🛰️ 发现卫星数据，立即更新显示");
        updateSatelliteEntities(satelliteNames);
      }
      return;
    }

    setIsLoading(true);
    console.log("🚀 开始加载Cesium...");

    const timer = setTimeout(() => {
      import('cesium').then(Cesium => {
        cesiumRef.current = Cesium;

        if (viewerRef.current) {
          setIsLoading(false);
          return;
        }

        try {
          console.log("🔑 设置Cesium访问令牌...");
          Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJhYTJjNjM4Zi1hOTYxLTQxNTItODFlMS05YTEzMzU4ODk5MzIiLCJpZCI6MjAzNTE1LCJpYXQiOjE3MTEwMTAzMDV9.1zfBCCYAOJdwhmYScXFr8DhndCV2JaNhWwLBT29xZ5A';

          if (cesiumContainerRef.current) {
            cesiumContainerRef.current.style.width = '100%';
            cesiumContainerRef.current.style.height = '100%';
            cesiumContainerRef.current.style.position = 'relative';

            console.log("🛰️ 初始化Cesium查看器 (修复静止轨道版本)...");
            const viewer = new Cesium.Viewer(cesiumContainerRef.current, {
              geocoder: true,
              homeButton: true,
              sceneModePicker: true,
              baseLayerPicker: true,
              navigationHelpButton: true,
              animation: true,
              timeline: true,
              requestRenderMode: false,
              maximumRenderTimeChange: Infinity
            });

            // 设置当前时间为北京时间
            viewer.clock.currentTime = Cesium.JulianDate.addHours(
            Cesium.JulianDate.now(), // 获取当前 UTC 时间
            8, // 北京时间比 UTC 快 8 小时
            new Cesium.JulianDate() // 返回新的 JulianDate 对象
            );

            // 确保时间同步更新
            viewer.clock.shouldAnimate = true;

            // 设置初始视角
            viewer.scene.camera.setView({
              destination: Cesium.Cartesian3.fromDegrees(
                DEFAULT_VIEW.longitude,
                DEFAULT_VIEW.latitude,
                DEFAULT_VIEW.height
              ),
              orientation: {
                heading: 0,
                pitch: -Cesium.Math.PI_OVER_TWO,
                roll: 0
              }
            });

            // 隐藏Cesium版权信息
            viewer._cesiumWidget._creditContainer.style.display = "none";

            // 🔧 修复：设置时钟为真实时间速度（可选择加速）
            viewer.clock.shouldAnimate = true;
            viewer.clock.multiplier = 20; // 60倍速，让卫星运动更明显

            // 优化渲染设置
            viewer.scene.globe.enableLighting = true;
            viewer.scene.fog.enabled = true;
            viewer.scene.skyAtmosphere.show = true;
            viewer.scene.moon.show = true;
            viewer.scene.skyBox.show = true;
            viewer.scene.sun.show = true;

            viewerRef.current = viewer;
            cesiumLoadedRef.current = true;
            console.log("✅ Cesium加载成功 (修复静止轨道版本)");

            // 添加点击事件处理
            viewer.screenSpaceEventHandler.setInputAction(function onLeftClick(click) {
              const pickedObject = viewer.scene.pick(click.position);

              if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.name) {
                // 获取点击的3D位置
                const ray = viewer.camera.getPickRay(click.position);
                const clickPosition = viewer.scene.globe.pick(ray, viewer.scene);

                // 如果是轨道实体，尝试获取更精确的轨道点
                if (pickedObject.id.name.includes('orbit')) {
                  // 获取轨道线上的精确点
                  const cartesian = viewer.scene.pickPosition(click.position);
                  if (Cesium.defined(cartesian)) {
                    handleSatelliteClick(pickedObject.id.name, click.position, pickedObject.id, cartesian);
                  } else {
                    handleSatelliteClick(pickedObject.id.name, click.position, pickedObject.id, clickPosition);
                  }
                } else {
                  handleSatelliteClick(pickedObject.id.name, click.position, pickedObject.id, null);
                }
              } else {
                setShowPopup(false);
              }
            }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
            viewerRef.current = viewer;
            cesiumLoadedRef.current = true;
            console.log("✅ Cesium加载成功");

            // 🔧 关键修复：初始化完成后立即检查是否有待渲染的卫星
            if (satelliteNames && satelliteNames.length > 0) {
              console.log("🛰️ Cesium初始化完成，立即渲染卫星:", satelliteNames);
              // 使用 setTimeout 确保 Cesium 完全准备好
              setTimeout(() => {
                updateSatelliteEntities(satelliteNames);
              }, 100);
            }
            // 如果有指定位置，定位到该位置
            if (location) {
              const geocoder = viewer.geocoder.viewModel;
              if (geocoder) {
                geocoder.searchText = location;
                geocoder.search();
              }
            }
          }
        } catch (error) {
          console.error("❌ Cesium初始化失败:", error);
        } finally {
          setIsLoading(false);
        }
      }).catch(error => {
        console.error("❌ Cesium模块加载失败:", error);
        setIsLoading(false);
      });
    }, 100);

    return () => {
      clearTimeout(timer);
      if (!visible && viewerRef.current) {
        console.log("🧹 销毁Cesium查看器...");
        viewerRef.current.destroy();
        viewerRef.current = null;
        cesiumLoadedRef.current = false;
        cesiumRef.current = null;
      }
    };
  }, [visible, location, satelliteNames]); // 🔧 添加 satelliteNames 依赖

  // 定位到指定地点
  useEffect(() => {
    const Cesium = cesiumRef.current;
    if (!viewerRef.current || !Cesium) return;

    console.log("📍 位置更新:", location);

    if (!location) {
      console.log("📍 恢复默认视角");
      viewerRef.current.scene.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          DEFAULT_VIEW.longitude,
          DEFAULT_VIEW.latitude,
          DEFAULT_VIEW.height
        ),
        orientation: {
          heading: 0,
          pitch: -Cesium.Math.PI_OVER_TWO,
          roll: 0
        },
        duration: 2.0
      });
    } else {
      console.log("📍 在地图上定位到:", location);
      const geocoder = viewerRef.current.geocoder.viewModel;
      if (geocoder) {
        geocoder.searchText = location;
        geocoder.search();
      }
    }
  }, [location]);

  // 处理卫星名称变化
  useEffect(() => {
  console.log('🛰️ 卫星列表变化:', satelliteNames);

  if (satelliteNames.length === 0) {
    if (viewerRef.current && cesiumLoadedRef.current && cesiumRef.current) {
      clearCustomSatellites();
    }
    setPendingSatellites([]); // 清空待渲染卫星
    return;
  }

  // 如果 Cesium 还没准备好，保存到待渲染列表
  if (!viewerRef.current || !cesiumLoadedRef.current || !cesiumRef.current) {
    console.log('🛰️ Cesium尚未加载完成，保存卫星数据待渲染');
    setPendingSatellites(satelliteNames);
    return;
  }

  // Cesium 已准备好，直接更新
  updateSatelliteEntities(satelliteNames);
}, [satelliteNames, updateSatelliteEntities]);

  useEffect(() => {
    if (cesiumLoadedRef.current && viewerRef.current && cesiumRef.current && pendingSatellites.length > 0) {
      console.log('🛰️ Cesium已准备好，渲染待处理的卫星:', pendingSatellites);
      updateSatelliteEntities(pendingSatellites);
      setPendingSatellites([]); // 清空待渲染列表
    }
  }, [cesiumLoadedRef.current, pendingSatellites, updateSatelliteEntities]);
  // 清理副作用
  useEffect(() => {
    return () => {
      clearCustomSatellites();
    };
  }, []);

  if (!visible) return null;

  return (
    <div className="relative w-full h-full">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 bg-opacity-95 z-10">
          <div className="flex flex-col items-center">
            <div className="relative">
              <svg className="animate-spin h-16 w-16 text-blue-400 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <div className="absolute inset-0 animate-ping">
                <svg className="h-16 w-16 text-purple-400 opacity-20" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                </svg>
              </div>
            </div>
            <span className="text-white text-lg font-medium mb-2">🚀 加载地图中...</span>
            <span className="text-blue-300 text-sm">正在初始化</span>
          </div>
        </div>
      )}

      <div
        ref={cesiumContainerRef}
        className="cesium-container"
        style={{ width: '100%', height: '100%', position: 'relative' }}
      ></div>

      {/* 卫星信息弹窗 */}
      {showPopup && satelliteInfo && (
        <div
          className="absolute bg-gradient-to-br from-slate-800 via-purple-900 to-slate-800 bg-opacity-98 border-2 border-purple-400 rounded-2xl p-6 max-w-md text-sm shadow-2xl z-50 backdrop-blur-lg"
          style={{
            top: `${Math.max(10, Math.min(popupPosition.top - 200, cesiumContainerRef.current?.clientHeight - 400))}px`,
            right: `${Math.max(10, popupPosition.right)}px`,
            transform: 'none',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 30px rgba(168, 85, 247, 0.4)'
          }}
        >
          <div className="text-center text-yellow-300 pb-4 mb-4 font-bold text-lg border-b-2 border-purple-400">
            🚀 {satelliteInfo.name}
          </div>

          <div className="space-y-3">
            {/* 如果是轨道信息，只显示轨道相关数据 */}
            {satelliteInfo.isOrbitInfo ? (
              <>
                <div className="flex items-center">
                  <div className="flex-none w-28 text-purple-300 font-bold text-xs">🛰️ 轨道类型</div>
                  <div className="flex-1 text-blue-300 text-xs">{satelliteInfo.orbit}</div>
                </div>

                <div className="flex items-center">
                  <div className="flex-none w-28 text-purple-300 font-bold text-xs">📏 轨道高度</div>
                  <div className="flex-1 text-yellow-300 text-xs font-medium">{satelliteInfo.altitude}</div>
                </div>

                <div className="flex items-center">
                  <div className="flex-none w-28 text-purple-300 font-bold text-xs">⏱️ 轨道周期</div>
                  <div className="flex-1 text-orange-300 text-xs">{satelliteInfo.period}</div>
                </div>

                <div className="flex items-center">
                  <div className="flex-none w-28 text-purple-300 font-bold text-xs">📐 轨道倾角</div>
                  <div className="flex-1 text-orange-300 text-xs">{satelliteInfo.inclination}</div>
                </div>

                {/* 🆕 新增：显示到达时间 */}
                  {/* 🆕 新增：显示到达时间 */}
{satelliteInfo.timeToReach !== null && satelliteInfo.timeToReach !== undefined && (
  <div className="flex items-center mt-2 pt-2 border-t border-purple-600">
    <div className="flex-none w-28 text-purple-300 font-bold text-xs">⏰ 到达时间</div>
    <div className="flex-1 text-cyan-300 text-xs font-medium">
      {(() => {
        // 计算具体到达时间
        const arrivalTime = new Date(Date.now() + satelliteInfo.timeToReach * 1000);
        const arrivalTimeStr = arrivalTime.toLocaleTimeString('zh-CN', { 
          hour: '2-digit', 
          minute: '2-digit', 
          second: '2-digit' 
        });
        
        // 格式化倒计时
        // const countdownStr = satelliteInfo.timeToReach < 60
        //   ? `${satelliteInfo.timeToReach.toFixed(0)} 秒`
        //   : satelliteInfo.timeToReach < 3600
        //     ? `${(satelliteInfo.timeToReach / 60).toFixed(1)} 分钟`
        //     : `${(satelliteInfo.timeToReach / 3600).toFixed(1)} 小时`;
        const countdownStr = (() => {
          const totalSeconds = Math.round(satelliteInfo.timeToReach);
          if (totalSeconds < 60) {
            return `${totalSeconds}秒`;
          } else if (totalSeconds < 3600) {
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            return `${minutes}分钟${seconds}秒`;
          } else {
            const hours = Math.floor(totalSeconds / 3600);
            const minutes = Math.floor((totalSeconds % 3600) / 60);
            const seconds = totalSeconds % 60;
            return minutes > 0 
              ? `${hours}小时${minutes}分钟${seconds}秒`
              : `${hours}小时${seconds}秒`;
          }
        })();
        
        return (
          <span>
            {arrivalTimeStr}
            <span className="text-purple-300 ml-1">
              (还需{countdownStr})
            </span>
          </span>
        );
      })()}
    </div>
  </div>
)}
                {/* {satelliteInfo.timeToReach !== null && satelliteInfo.timeToReach !== undefined && (
                  <div className="flex items-center mt-2 pt-2 border-t border-purple-600">
                    <div className="flex-none w-28 text-purple-300 font-bold text-xs">⏰ 到达时间</div>
                    <div className="flex-1 text-cyan-300 text-xs font-medium">
                      {satelliteInfo.timeToReach < 60
                        ? `${satelliteInfo.timeToReach.toFixed(0)} 秒`
                        : satelliteInfo.timeToReach < 3600
                          ? `${(satelliteInfo.timeToReach / 60).toFixed(1)} 分钟`
                          : `${(satelliteInfo.timeToReach / 3600).toFixed(1)} 小时`
                      }
                    </div>
                  </div>
                )} */}
              </>
            ) : (
              // 完整的卫星信息（点击卫星时）
              <>
                <div className="flex items-center">
                  <div className="flex-none w-28 text-purple-300 font-bold text-xs">🗓️ 发射时间</div>
                  <div className="flex-1 text-white text-xs">{satelliteInfo.launchDate}</div>
                </div>

                <div className="flex items-center">
                  <div className="flex-none w-28 text-purple-300 font-bold text-xs">🌍 所属国家</div>
                  <div className="flex-1 text-white text-xs">{satelliteInfo.country}</div>
                </div>

                <div className="flex items-center">
                  <div className="flex-none w-28 text-purple-300 font-bold text-xs">📡 在轨状态</div>
                  <div className="flex-1 text-green-300 text-xs font-medium">{satelliteInfo.status}</div>
                </div>

                <div className="flex items-center">
                  <div className="flex-none w-28 text-purple-300 font-bold text-xs">🛰️ 轨道类型</div>
                  <div className="flex-1 text-blue-300 text-xs">{satelliteInfo.orbit}</div>
                </div>

                {satelliteInfo.altitude && (
                  <div className="flex items-center">
                    <div className="flex-none w-28 text-purple-300 font-bold text-xs">📏 轨道高度</div>
                    <div className="flex-1 text-yellow-300 text-xs font-medium">{satelliteInfo.altitude}</div>
                  </div>
                )}

                {satelliteInfo.period && (
                  <div className="flex items-center">
                    <div className="flex-none w-28 text-purple-300 font-bold text-xs">⏱️ 轨道周期</div>
                    <div className="flex-1 text-orange-300 text-xs">{satelliteInfo.period}</div>
                  </div>
                )}

                {satelliteInfo.inclination && (
                  <div className="flex items-center">
                    <div className="flex-none w-28 text-purple-300 font-bold text-xs">📐 轨道倾角</div>
                    <div className="flex-1 text-orange-300 text-xs">{satelliteInfo.inclination}</div>
                  </div>
                )}

                {satelliteInfo.resolution && (
                  <div className="flex items-center">
                    <div className="flex-none w-28 text-purple-300 font-bold text-xs">🔍 分辨率</div>
                    <div className="flex-1 text-cyan-300 text-xs">{satelliteInfo.resolution}</div>
                  </div>
                )}

                {satelliteInfo.applications && (
                  <div className="mt-4 pt-3 border-t border-purple-400">
                    <div className="text-purple-300 font-bold mb-2 text-xs">🎯 应用领域</div>
                    <div className="text-xs text-white bg-purple-800 bg-opacity-50 p-2 rounded-lg">{satelliteInfo.applications}</div>
                  </div>
                )}

                {satelliteInfo.description && (
                  <div className="mt-4 pt-3 border-t border-purple-400">
                    <div className="text-purple-300 font-bold mb-2 text-xs">📋 卫星简介</div>
                    <div className="text-xs text-gray-200 bg-slate-800 bg-opacity-60 p-3 rounded-lg leading-relaxed">{satelliteInfo.description}</div>
                  </div>
                )}
              </>
            )}
          </div>

          <button
            className="absolute top-3 right-3 text-gray-400 hover:text-yellow-300 transition-colors duration-200"
            onClick={() => setShowPopup(false)}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
};

export default EnhancedCesiumMap;