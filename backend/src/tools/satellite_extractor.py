# backend/src/tools/satellite_extractor.py
import re
import logging
from typing import List, Set, Optional, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)

# 与前端保持一致的卫星列表
COMMON_SATELLITES = [
    # 中国卫星
    '风云一号', '风云二号', '风云三号', '风云四号',
    '高分一号', '高分二号', '高分三号', '高分四号', '高分五号', '高分六号', '高分七号', '高分八号', '高分九号',
    '高分十号', '高分十一号', '高分十二号', '高分十三号', '高分十四号',
    'GF-1', 'GF-2', 'GF-3', 'GF-4', 'GF-5', 'GF-6', 'GF-7',
    '海洋一号', '海洋二号', '海洋三号', '资源一号', '资源二号', '资源三号',
    '环境一号', 'HJ-1A',

    # 国际卫星
    'Landsat-1', 'Landsat-2', 'Landsat-3', 'Landsat-4', 'Landsat-5', 'Landsat-6', 'Landsat-7', 'Landsat-8', 'Landsat-9',
    'Landsat 1', 'Landsat 2', 'Landsat 3', 'Landsat 4', 'Landsat 5', 'Landsat 6', 'Landsat 7', 'Landsat 8', 'Landsat 9',
    'Sentinel-1', 'Sentinel-2', 'Sentinel-3', 'Sentinel-5P', 'Sentinel-6',
    'Sentinel 1', 'Sentinel 2', 'Sentinel 3', 'Sentinel 6',
    '哨兵-1号', '哨兵-2号', '哨兵-3号',
    'MODIS', 'WorldView', 'QuickBird', 'IKONOS', 'Pleiades',
    'SPOT', 'TerraSAR-X', 'RADARSAT', 'ALOS', 'Himawari',
    '葵花8号', '葵花9号', 'GOES', 'Meteosat', 'NOAA',

    # 商业小卫星星座
    'PlanetScope', 'Planet', 'Dove', 'SkySat', 'RapidEye',
    'BlackSky', 'ICEYE', 'Capella', 'SuperView', 'Jilin-1', '吉林一号',

    # 更多卫星（从前端代码复制）
    'WORLDVIEW-1', 'WORLDVIEW-2', 'WORLDVIEW-3', 'WORLDVIEW-4',
    'WorldView-1', 'WorldView-2', 'WorldView-3', 'WorldView-4',
    'STARLETTE', 'LAGEOS-1', 'LAGEOS 1', 'AJISAI', 'LAGEOS 2',
    'TERRA', 'AQUA', 'AURA', 'ODIN', 'SCISAT 1',
    'PROBA-1', 'XMM-NEWTON', 'BEIJING 1', 'EROS B', 'KOMPSAT-2',
    'HINODE', 'DMSP F17', 'SAR-LUPE 1', 'TERRASAR-X', 'COSMO-SKYMED 1',
    'RADARSAT-2', 'CARTOSAT-2A', 'GEOEYE 1', 'THEOS', 'COSMO-SKYMED 2',
    'COSMO-SKYMED 3', 'CBERS-4', 'TANDEM-X', 'OFEQ 9', 'CARTOSAT-2B',
    'AISSAT 1', 'ALSAT 2A', 'YAOGAN-10', 'YAOGAN-11', '天绘一号',
    '实践六号04A', 'SHIJIAN-6 04B', 'COSMO-SKYMED 4', 'DMSP F18',
    'SMOS', 'PROBA-2', 'COSMOS 2455', 'IGS 5A', 'YAOGAN-7', 'YAOGAN-8',
    'SDO', 'YAOGAN-9A', 'YAOGAN-9B', 'YAOGAN-9C', 'CRYOSAT-2',

    # 继续添加更多卫星...
    'USA 223', 'USA 224', 'USA 217', 'USA 229', 'USA 230', 'USA 234', 'USA 237',
    'HAIYANG-2A', '海洋二号A', 'ZY 1-02C', '资源一号02', 'ZY 3-1', 'YAOGAN-15',
    '资源三号01', 'SJ-11-02', '实践十一号02', 'CHUANGXIN 1-03', 'SHIYAN 4',
    'YAOGAN-12', 'YAOGAN-13', 'YAOGAN-14', '天绘一号02', '风云二号F',
    'PLEIADES 1A', 'PLEIADES 1B', 'SPOT 1', 'SPOT 2', 'SPOT 3', 'SPOT 4', 'SPOT 5', 'SPOT 6', 'SPOT 7',
    'RESOURCESAT-2', 'YOUTHSAT', 'JUGNU', 'SRMSAT', 'GSAT-12', 'RISAT-1', 'MEGHA-TROPIQUES',
    'IGS 6A', 'IGS 7A', 'GCOM-W1', '向日葵1号', '向日葵2号', '向日葵3号', '向日葵4号',
    '向日葵5号', '向日葵6号', '向日葵7号', '向日葵8号', '向日葵9号', 'ALOS-2',
    'ARIRANG-3', 'ARIRANG-5', 'SUOMI NPP', 'METOP-B', 'PROBA-V', 'SWARM A',
    'SARAL', 'SKYSAT-A', 'ELEKTRO-L 1', 'SAC-D', 'NIGERIASAT-2', 'RASAT',
    'SICH-2', 'LARES', 'NIGERIASAT-X', 'SSOT',

    # 更多中国卫星
    '遥感二十号01A', '遥感二十号01B', '遥感二十号01C', '遥感二十一号', '遥感二十二号',
    '遥感二十三号', '遥感二十四号', '遥感二十五号01A', '遥感二十五号01B', '遥感二十五号01C',
    '遥感二十六号', '遥感二十七号', '遥感二十八号', '遥感二十九号', '遥感三十号',
    '风云二号G', '高分八号', '高分九号', '吉林一号', '天拓二号', '天绘一号', '天绘二号', '天绘四号',
    'CBERS 4', '创新一号04',

    # 更多美国卫星
    'GPM-CORE', 'OCO 2', 'JASON-3', 'DSCOVR', 'MMS 1', 'MMS 2', 'MMS 3', 'MMS 4',
    'USA 250', 'USA 259', 'USA 264', 'USA 267',

    # 日本卫星
    'UNIFORM 1', 'RISING 2', 'HODOYOSHI-3', 'HODOYOSHI-4', 'HIMAWARI-8',
    'ASNARO', 'HODOYOSHI-1', 'CHUBUSAT-1', 'QSAT-EOS', 'TSUBAME', 'IGS 9A', 'IGS O-5',

    # 欧洲卫星
    'SENTINEL-1A', 'SENTINEL-2A', 'SENTINEL-3A', 'SENTINEL-1B',

    # 其他国家卫星
    'DMSP 5D-3 F19', 'OFEQ 10', 'EGYPTSAT 2', 'KAZEOSAT 1', 'KAZEOSAT 2',
    'DEIMOS-2', 'BUGSAT-1', 'TABLETSAT-AURORA', 'TIGRISAT', 'LEMUR-1',
    'METEOR-M 2', 'MKA-PN 2', 'SKYSAT-B', 'AISSAT 2', 'TECHDEMOSAT-1',
    'RESURS-P 2', 'COSMOS 2502', 'COSMOS 2503', 'COSMOS 2506', 'COSMOS 2510',
    'COSMOS 2511', 'COSMOS 2515', 'ELEKTRO-L 2', 'KOMPSAT-3A', 'DMC3-FM1',
    'DMC3-FM2', 'DMC3-FM3', 'CARBONITE 1', 'LAPAN-A2', 'LEMUR-2-JOEL',
    'LEMUR-2-CHRIS', 'LEMUR-2-JEROEN', 'LEMUR-2-PETER', 'LQSAT',
    'LINGQIAO VIDEO A', 'LINGQIAO VIDEO B', 'TELEOS-1', 'KENT RIDGE 1',
    'VELOX-CI', 'KMS 4', 'RESURS-P 3', 'KONDOR-E', 'DIWATA-1'
]

# 卫星名称映射（与前端保持一致）
SATELLITE_MAPPING = {
    # 高分系列
    'gf-1': '高分一号', 'gf-2': '高分二号', 'gf-3': '高分三号', 'gf-4': '高分四号',
    'gf-5': '高分五号', 'gf-6': '高分六号', 'gf-7': '高分七号', 'gf-8': '高分八号',
    'gf-9': '高分九号', 'gf-10': '高分十号', 'gf-11': '高分十一号', 'gf-12': '高分十二号',
    'gf-13': '高分十三号', 'gf-14': '高分十四号',
    'gf1': '高分一号', 'gf2': '高分二号', 'gf3': '高分三号', 'gf4': '高分四号',
    'gf5': '高分五号', 'gf6': '高分六号', 'gf7': '高分七号', 'gf8': '高分八号',
    'gf9': '高分九号', 'gf10': '高分十号', 'gf11': '高分十一号', 'gf12': '高分十二号',
    'gf13': '高分十三号', 'gf14': '高分十四号',

    # 风云系列
    'fy-1': '风云一号', 'fy-2': '风云二号', 'fy-3': '风云三号', 'fy-4': '风云四号',
    'fy1': '风云一号', 'fy2': '风云二号', 'fy3': '风云三号', 'fy4': '风云四号',
    'fy-2f': '风云二号F', 'fy-2g': '风云二号G', 'fy2f': '风云二号F', 'fy2g': '风云二号G',

    # 哨兵系列
    'sentinel-1': '哨兵-1号', 'sentinel-2': '哨兵-2号', 'sentinel-3': '哨兵-3号',
    'sentinel-5p': 'Sentinel-5P', 'sentinel-6': '哨兵-6号',
    'sentinel1': '哨兵-1号', 'sentinel2': '哨兵-2号', 'sentinel3': '哨兵-3号',
    'sentinel5p': 'Sentinel-5P', 'sentinel6': '哨兵-6号',
    '哨兵1号': '哨兵-1号', '哨兵2号': '哨兵-2号', '哨兵3号': '哨兵-3号',
    'sentinel-1a': 'Sentinel-1A', 'sentinel-1b': 'Sentinel-1B',
    'sentinel-2a': 'Sentinel-2A', 'sentinel-2b': 'Sentinel-2B',
    'sentinel-3a': 'Sentinel-3A',

    # Landsat系列
    'landsat-1': 'Landsat-1', 'landsat-2': 'Landsat-2', 'landsat-3': 'Landsat-3',
    'landsat-4': 'Landsat-4', 'landsat-5': 'Landsat-5', 'landsat-6': 'Landsat-6',
    'landsat-7': 'Landsat-7', 'landsat-8': 'Landsat-8', 'landsat-9': 'Landsat-9',
    'landsat1': 'Landsat-1', 'landsat2': 'Landsat-2', 'landsat3': 'Landsat-3',
    'landsat4': 'Landsat-4', 'landsat5': 'Landsat-5', 'landsat6': 'Landsat-6',
    'landsat7': 'Landsat-7', 'landsat8': 'Landsat-8', 'landsat9': 'Landsat-9',

    # 添加更多映射...
    'hy-1': '海洋一号', 'hy-2': '海洋二号', 'hy-3': '海洋三号',
    'hy1': '海洋一号', 'hy2': '海洋二号', 'hy3': '海洋三号',
    'hy-2a': '海洋二号A', 'haiyang-2a': '海洋二号A',

    'zy-1': '资源一号', 'zy-2': '资源二号', 'zy-3': '资源三号',
    'zy1': '资源一号', 'zy2': '资源二号', 'zy3': '资源三号',

    'hj-1': '环境一号', 'hj1': '环境一号',

    # WorldView系列
    'worldview-1': 'WorldView-1', 'worldview-2': 'WorldView-2',
    'worldview-3': 'WorldView-3', 'worldview-4': 'WorldView-4',
    'worldview1': 'WorldView-1', 'worldview2': 'WorldView-2',
    'worldview3': 'WorldView-3', 'worldview4': 'WorldView-4',

    # 其他卫星
    'himawari': '向日葵8号', 'himawari-8': '向日葵8号', 'himawari-9': '向日葵9号',
    'planet': 'PlanetScope', 'planetscope': 'PlanetScope', 'dove': 'PlanetScope',
    'skysat': 'SkySat', 'jilin-1': '吉林一号', 'jilin1': '吉林一号',
}


def normalize_satellite_name(name: str) -> str:
    """标准化卫星名称"""
    if not name:
        return ""

    # 去除首尾空格
    name = name.strip()

    # 转换为小写进行映射查找
    lower_name = name.lower().replace(' ', '').replace('-', '')

    # 查找映射
    if lower_name in SATELLITE_MAPPING:
        return SATELLITE_MAPPING[lower_name]

    # 如果没有找到映射，返回原名称
    return name


@lru_cache(maxsize=128)
def create_satellite_regex() -> re.Pattern:
    """创建卫星名称的正则表达式（带缓存）"""
    # 转义特殊字符
    patterns = []
    for sat in COMMON_SATELLITES:
        escaped = re.escape(sat)
        patterns.append(escaped)

    # 创建正则表达式
    pattern = '|'.join(f'({p})' for p in patterns)
    return re.compile(pattern, re.IGNORECASE)


def extract_satellites_locally(text: str) -> List[str]:
    """快速本地提取卫星名称"""
    if not text:
        return []

    found_satellites = set()
    satellite_regex = create_satellite_regex()

    matches = satellite_regex.findall(text)

    for match_groups in matches:
        for match in match_groups:
            if match:
                normalized = normalize_satellite_name(match.strip())
                if normalized:
                    found_satellites.add(normalized)

    return list(found_satellites)


def extract_satellites_from_composition(content: str) -> List[str]:
    """从卫星组成部分精确提取卫星 - 优先从推荐卫星列表提取"""
    logger.info("🛰️ 从卫星组成部分提取卫星...")

    satellites = set()

    # 🆕 优先查找"推荐卫星"列表
    # 匹配模式：推荐卫星：卫星A、卫星B、卫星C
    recommend_patterns = [
        r'推荐卫星[：:]\s*([^\n]+)',
        r'推荐的卫星[：:]\s*([^\n]+)',
        r'建议卫星[：:]\s*([^\n]+)',
        r'卫星列表[：:]\s*([^\n]+)'
    ]

    for pattern in recommend_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            satellite_list_str = match.group(1)
            logger.info(f"📋 找到推荐卫星列表: {satellite_list_str}")

            # 分割卫星列表（支持中文顿号、英文逗号、"和"、"以及"等分隔符）
            separators = ['、', ',', '，', '和', '以及', '及']

            # 使用正则表达式分割
            separator_pattern = '|'.join(map(re.escape, separators))
            satellite_names = re.split(separator_pattern, satellite_list_str)

            # 提取并标准化每个卫星名称
            for sat_name in satellite_names:
                sat_name = sat_name.strip()
                if sat_name:
                    # 使用本地快速提取来验证是否是有效卫星名
                    local_satellites = extract_satellites_locally(sat_name)
                    if local_satellites:
                        for sat in local_satellites:
                            normalized = normalize_satellite_name(sat)
                            satellites.add(normalized)
                            logger.info(f"✅ 从推荐列表提取到卫星: {normalized}")
                    else:
                        # 直接尝试标准化
                        normalized = normalize_satellite_name(sat_name)
                        if normalized in COMMON_SATELLITES:
                            satellites.add(normalized)
                            logger.info(f"✅ 从推荐列表提取到卫星: {normalized}")

            # 如果从推荐列表中成功提取到卫星，直接返回
            if satellites:
                result = list(satellites)
                logger.info(f"🎯 成功从推荐卫星列表提取: {result}")
                return result

    # 如果没有找到推荐卫星列表，再尝试其他方法
    logger.info("⚠️ 未找到推荐卫星列表，尝试其他提取方法...")

    # 查找"卫星组成"部分
    composition_patterns = [
        r'(?:卫星组成|卫星列表|卫星配置|组成卫星|卫星组)[：:]*\s*\n([\s\S]*?)(?=\n(?:##|###|\d+\.|[三四五六七八九十]、)|$)',
        r'\*\*(?:\d+\.?\s*)?卫星组成\*\*[：:]*\s*\n([\s\S]*?)(?=\n\*\*|\n#{2,3}|\n\d+\.|$)',
    ]

    for pattern in composition_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            composition_section = match.group(1)
            logger.info(f"📄 找到卫星组成部分: {composition_section[:200]}...")

            # 在组成部分中再次查找推荐卫星列表
            for rec_pattern in recommend_patterns:
                rec_match = re.search(rec_pattern, composition_section, re.IGNORECASE)
                if rec_match:
                    satellite_list_str = rec_match.group(1)
                    # 使用相同的逻辑提取卫星
                    separators = ['、', ',', '，', '和', '以及', '及']
                    separator_pattern = '|'.join(map(re.escape, separators))
                    satellite_names = re.split(separator_pattern, satellite_list_str)

                    for sat_name in satellite_names:
                        sat_name = sat_name.strip()
                        if sat_name:
                            local_satellites = extract_satellites_locally(sat_name)
                            if local_satellites:
                                for sat in local_satellites:
                                    normalized = normalize_satellite_name(sat)
                                    satellites.add(normalized)
                            else:
                                normalized = normalize_satellite_name(sat_name)
                                if normalized in COMMON_SATELLITES:
                                    satellites.add(normalized)

                    if satellites:
                        result = list(satellites)
                        logger.info(f"🎯 从卫星组成部分的推荐列表提取: {result}")
                        return result

            # 如果仍然没有找到，使用原有的逻辑提取
            lines = composition_section.split('\n')
            for line in lines:
                if not line.strip():
                    continue

                local_satellites = extract_satellites_locally(line)
                for sat in local_satellites:
                    satellites.add(sat)
                    logger.info(f"✅ 找到卫星: {sat}")

            break

    # 备用方法保持不变
    if not satellites:
        logger.warning("⚠️ 未找到明确的卫星组成部分，尝试备用提取方法")
        alt_patterns = [
            r'(?:包含|包括|选择了?|组合了?|采用了?)[：:]*\s*([^\n]*(?:、|,|和|以及)[^\n]*)',
            r'卫星[:：]\s*([^\n]+)',
        ]

        for pattern in alt_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                satellite_list = match.group(1)
                found_sats = extract_satellites_locally(satellite_list)
                satellites.update(found_sats)

    result = list(satellites)
    logger.info(f"🛰️ 最终提取到的卫星: {result}")
    return result


def extract_satellites_from_table(content: str) -> List[str]:
    """从表格中提取卫星"""
    logger.info("🔍 从表格中提取卫星...")

    satellites = set()

    # 匹配表格行
    table_patterns = [
        r'\|\s*([^|]+?)\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|',
        r'\|\s*([^|]+?)\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|',
        r'\|\s*([^|]+?)\s*\|[^|]*\|[^|]*\|'
    ]

    for pattern in table_patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            cell_content = match.group(1).strip()
            # 跳过表头和分隔行
            if cell_content and '卫星名称' not in cell_content and '---' not in cell_content:
                normalized = normalize_satellite_name(cell_content)
                if normalized and normalized in COMMON_SATELLITES:
                    satellites.add(normalized)
                    logger.info(f"✅ 从表格提取到卫星: {normalized}")

    return list(satellites)


async def extract_satellite_names(text: str) -> List[str]:
    """提取卫星名称 - 主函数"""
    try:
        logger.info("开始提取卫星名称...")

        # 优先从卫星组成部分提取
        composition_satellites = extract_satellites_from_composition(text)
        if composition_satellites:
            return composition_satellites

        # 如果没找到，使用本地快速提取
        local_results = extract_satellites_locally(text)

        if local_results:
            logger.info(f"本地快速提取到卫星: {local_results}")
            return local_results

        # 如果文本较短，直接返回空结果
        if len(text) < 50:
            return []

        # 尝试从表格提取
        table_satellites = extract_satellites_from_table(text)
        if table_satellites:
            return table_satellites

        return []

    except Exception as e:
        logger.error(f'卫星名称提取过程出错: {e}')
        return []


async def extract_satellite_names_from_messages(messages: List[Dict]) -> List[str]:
    """批量提取消息中的卫星名称"""
    all_satellite_names = set()

    # 只从assistant的消息中提取
    assistant_messages = [msg for msg in messages if msg.get('role') == 'assistant']

    # 查找最新的包含方案的消息
    latest_plan_message = None
    for msg in reversed(assistant_messages):
        content = msg.get('content', '')
        if content and any(keyword in content for keyword in ['卫星组成', '## 2.', '###', '方案']):
            latest_plan_message = msg
            break

    # 如果找到方案消息，只从这条消息中提取
    if latest_plan_message:
        logger.info('🛰️ 找到最新方案消息，从中提取卫星...')
        satellites = extract_satellites_from_composition(latest_plan_message['content'])
        for name in satellites:
            normalized = normalize_satellite_name(name)
            all_satellite_names.add(normalized)
    else:
        # 如果没有找到方案消息，从最新的助手消息中提取
        logger.info('🛰️ 未找到方案消息，从最新消息中提取...')
        if assistant_messages:
            latest_msg = assistant_messages[-1]
            satellites = extract_satellites_locally(latest_msg.get('content', ''))
            for name in satellites:
                normalized = normalize_satellite_name(name)
                all_satellite_names.add(normalized)

    # 去重处理
    final_satellites = list(all_satellite_names)
    unique_satellites = []
    seen = set()

    for sat in final_satellites:
        key = sat.lower().replace('-', '').replace(' ', '')
        if key not in seen:
            seen.add(key)
            unique_satellites.append(sat)

    logger.info(f'🛰️ 提取并去重后的卫星: {unique_satellites}')
    return unique_satellites


# 缓存提取结果
extraction_cache = {}


async def extract_satellite_names_with_cache(text: str) -> List[str]:
    """带缓存的卫星名称提取"""
    # 生成文本的简单哈希作为缓存键
    cache_key = f"{text[:100]}_{len(text)}"

    if cache_key in extraction_cache:
        logger.info("使用缓存的卫星提取结果")
        return extraction_cache[cache_key]

    result = await extract_satellite_names(text)
    extraction_cache[cache_key] = result

    # 限制缓存大小
    if len(extraction_cache) > 100:
        # 删除最旧的缓存项
        first_key = next(iter(extraction_cache))
        del extraction_cache[first_key]

    return result


async def extract_satellites_two_phase(content: str) -> List[str]:
    """两阶段提取策略"""
    logger.info("🚀 开始两阶段卫星提取...")

    # 第一阶段：快速本地提取
    phase1_results = extract_satellites_from_composition(content)
    logger.info(f"📊 第一阶段提取结果: {phase1_results}")

    # 第二阶段：表格精确提取
    phase2_results = extract_satellites_from_table(content)
    logger.info(f"📊 第二阶段提取结果: {phase2_results}")

    # 合并结果并去重
    combined = set(phase1_results + phase2_results)
    final_results = list(combined)

    logger.info(f"✅ 两阶段提取完成，最终结果: {final_results}")
    return final_results