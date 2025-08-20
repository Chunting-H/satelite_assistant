# 卫星管理助手爬虫智能体

## 概述

根据 `agent.md` 的要求，本系统实现了一个面向"卫星管理助手"的爬虫智能体，能够自动化地收集、格式化、入库及记录卫星信息。

## 主要功能

### 1. 数据获取（增强版）
- **目标网站**: [Gunter's Space Page](https://space.skyrocket.de/)
- **爬取模式**:
  - `recent`: 爬取最近发射的所有卫星数据
  - `single`: 搜索指定的单个卫星
- **深度爬取**: 
  - 自动进入每个卫星的详情页面
  - 解析 `<div id="satdescription">` 卫星描述信息
  - 解析 `<table id="satdata">` 详细技术规格表
  - 提取完整的轨道参数、质量、应用类型等

### 2. 数据清洗与结构化（增强版）
- 使用 **DeepSeek 大模型** 进行智能数据格式化
- **丰富的输入数据**：详情页面的完整技术规格
- **智能参数解析**：轨道参数、应用分类、技术规格
- 生成符合既定JSON格式的结构化卫星信息
- 包含字段：卫星名称、别名、发射时间、轨道类型、用途、制造商、运营商、技术规格等

### 3. 数据库检查与存储
- 存储位置：`data/eo_satellite.json`
- 自动检查重复记录（基于卫星名称和别名）
- 保证数据完整性与字段一致性
- 自动备份机制

### 4. 日志记录
- 记录执行时间、目标网站、数据量、结果状态
- 日志保存在：`data/logs/satellite_crawl_*.json`
- 详细的错误处理和调试信息

## API 接口

### 爬虫执行接口
```http
POST /api/satellite/crawl
Content-Type: application/json

{
  "mode": "recent",              // 爬取模式：recent 或 single
  "satellite_name": "Starlink",  // 单卫星搜索时的卫星名称（mode=single时必需）
  "max_satellites": 10           // 最大爬取数量（mode=recent时有效）
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "成功爬取并处理 5 个卫星，其中新增 3 个",
  "satellites_count": 5,
  "new_satellites_count": 3,
  "execution_time": 12.34,
  "target_website": "https://space.skyrocket.de",
  "crawl_results": [...],
  "log_file": "data/logs/satellite_crawl_20250129_143022.json"
}
```

### 日志查询接口
```http
GET /api/satellite/crawl/logs?limit=10&offset=0
```

### 数据统计接口
```http
GET /api/satellite/data/stats
```

## 数据格式

输出的卫星数据严格按照 `agent.md` 中定义的JSON格式：

```json
{
  "satelliteName": "EXPLORER 7",
  "alternateNames": ["Explorer 7", "NASA S-1A"],
  "COSPARId": "1959-009A",
  "NORADId": 22,
  "objectType": "PAY",
  "operStatusCode": "Unknown",
  "satelliteAgencies": "NASA",
  "owner": "United States",
  "launchDate": "1959-10-13",
  "launchSite": "Air Force Eastern Test Range, Florida, USA",
  "eolDate": "1961-08-24",
  "period": 95.46,
  "inclination": 50.28,
  "apogee": 617.0,
  "perigee": 465.0,
  "rcs": 0.5003,
  "dryMass": 41.0,
  "launchMass": 41.0,
  "orbitCenter": "EA",
  "orbitType": "LEO_I (Upper LEO/Intermediate)",
  "orbitAltitude": "722",
  "repeatCycle": "",
  "ect": "",
  "orbitLongitude": "",
  "orbitSense": "",
  "applications": ["OSCAR description: "],
  "webInfo": [],
  "dataPortal": [],
  "instrumentNames": ["FPR"],
  "instrumentIds": ["OSCAR:fpr"],
  "isEO": "Earth observation",
  "relatedSatIds": ["OSCAR:explorer_vii"],
  "eoPortal": "",
  "hasInstrumentId": ["3dacd70d-ff7a-488a-9421-37e7bd5feae7"]
}
```

## 环境配置

### 必需配置
1. **DeepSeek API密钥** (可选，用于高质量数据格式化):
   ```bash
   export DEEPSEEK_API_KEY="your_deepseek_api_key"
   ```

### 可选配置 (用于网络搜索补充)
- `TAVILY_API_KEY`: Tavily搜索API
- `SERP_API_KEY`: SerpAPI
- `BING_API_KEY`: Bing搜索API

## 使用方式

### 1. 启动服务
```bash
cd backend
python main.py
```

### 2. 访问API文档
```
http://localhost:2025/docs
```

### 3. 执行爬虫任务
```bash
# 爬取最近发射的10个卫星
curl -X POST "http://localhost:2025/api/satellite/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "recent",
    "max_satellites": 10
  }'

# 搜索单个卫星
curl -X POST "http://localhost:2025/api/satellite/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "single",
    "satellite_name": "Starlink v2-Mini"
  }'
```

### 4. 查看结果
- **数据文件**: `data/eo_satellite.json`
- **日志文件**: `data/logs/satellite_crawl_*.json`
- **统计信息**: `GET /api/satellite/data/stats`

## 测试程序

运行测试程序验证功能：
```bash
python test_satellite_crawler.py
```

## 技术架构

```
src/tools/
├── satellite_crawler.py        # 爬虫核心逻辑
├── satellite_data_processor.py # 数据处理和存储
└── web_search_tools.py         # 网络搜索工具（已有）

src/api/
└── routes.py                   # API路由定义

data/
├── eo_satellite.json           # 卫星数据存储
└── logs/                       # 爬虫日志
    └── satellite_crawl_*.json
```

## 特性

- ✅ **深度爬取**: 自动进入详情页面获取完整技术规格
- ✅ **智能解析**: 解析 satdescription 和 satdata 结构化信息
- ✅ **编码兼容**: 支持多种字符编码的自动检测和处理
- ✅ **轨道参数**: 智能提取和解析轨道参数（倾角、周期、高度等）
- ✅ **应用分类**: 自动分类卫星应用类型
- ✅ **数据丰富**: 提取卫星全名、别名、制造商、运营商等详细信息
- ✅ **智能格式化**: 使用大模型清洗和标准化丰富的数据
- ✅ **重复检测**: 避免重复存储相同卫星（支持别名检测）
- ✅ **完整日志**: 详细记录每次爬取的执行情况
- ✅ **RESTful API**: 标准HTTP接口，易于集成
- ✅ **错误处理**: 完善的异常处理和降级策略
- ✅ **数据备份**: 自动创建数据备份避免丢失
- ✅ **重试机制**: 网络错误时自动重试

## 监控和维护

### 日志监控
- 检查日志文件了解爬取状态
- 监控新增卫星数量和错误率

### 数据维护
- 定期备份 `eo_satellite.json`
- 清理过期的日志文件

### 错误处理
- 网络错误：自动重试和降级
- API限制：适当延迟和批量处理
- 数据解析错误：默认格式化策略

## 后续优化

1. **增量更新**: 只爬取新发射的卫星
2. **多源聚合**: 集成更多卫星信息网站
3. **实时监控**: 设置定时任务自动执行
4. **数据验证**: 增强数据质量检查
5. **性能优化**: 并发爬取和缓存机制
