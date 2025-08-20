
## **任务目标**
构建一个**网页信息爬取智能体**，为**卫星查询助手**提供最新的卫星数据。
 该智能体需每日定期自动爬取卫星信息网站，使用**大模型对爬取结果进行结构化**，将结果存入本地 `eo_satellite.json`，并在前端可视化展示每日、每周、每月的爬取成果。

该功能是“智慧星座虚拟助手”系统的一个子模块，属于**卫星管理**页面的功能。

##  **功能逻辑与数据流**

#### **逻辑闭环**

1. **数据采集（后端）**
   - 定时触发爬虫 → 访问指定卫星信息网站 → 获取非结构化原始数据（HTML/文本/API JSON）。
   - 该功能已经通过tools/sate_search中的satellite_crawler.py和satellite_data_processor.py实现指定网页的爬取和卫星数据的格式化
2. **数据结构化（后端）**
   - 使用大模型 API（DeepSeek等）将原始数据转换为统一结构化格式（JSON）。
   - 检查 `eo_satellite.json` 是否已存在该卫星（匹配 `englishName + launchDate`）。
   - 新数据追加到 `eo_satellite.json`。
3. **日志记录（后端）**
   - 每次爬取生成日志（时间、来源、数据量、成功/失败数、失败原因）。
   - 日志存到 `crawlLogs.json`（供前端展示）。
4. **数据展示（前端）**
   - 前端读取 `crawlLogs.json`，统计每日、每周、每月的数据量（图表+列表）。
   - 用户可点击查看每次爬取的具体数据。
5. **卫星查询助手（前端+后端）**
   - 用户输入查询条件 → 前端发起请求 → 后端检索 `eo_satellite.json` → 返回结果列表。
   - 用户可查看卫星详情。

## 数据结构

### `backend/data/eo_satellite.json`（主数据文件）

``` json
    {
        "satelliteName": "EXPLORER 7",
        "alternateNames": [
            "Explorer 7",
            "NASA S-1A",
            "Explorer-VII"
        ],
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
        "applications": [
            "OSCAR description: "
        ],
        "webInfo": [],
        "dataPortal": [],
        "instrumentNames": [
            "FPR"
        ],
        "instrumentIds": [
            "OSCAR:fpr"
        ],
        "isEO": "Earth observation",
        "relatedSatIds": [
            "OSCAR:explorer_vii"
        ],
        "eoPortal": "",
        "hasInstrumentId": [
            "3dacd70d-ff7a-488a-9421-37e7bd5feae7"
        ]
    },
```

### `crawlLogs.json`（爬取日志）

``` json
[
  {
    "crawlTime": "2025-08-12T09:00:00Z",
    "targetSites": ["Gunter's Space Page", "NASA EO Portal"],
    "newDataCount": 12,
    "updatedDataCount": 3,
    "failedCount": 1,
    "failReasons": ["Timeout on ESA site"],
    "dataList": ["GF-1", "Sentinel-3", "Landsat-9"]
  }
]
```

## 后端开发需求

### Langgraph节点设计

| 节点                 | 功能                                       | 输入             | 输出                  |
| -------------------- | ------------------------------------------ | ---------------- | --------------------- |
| ParameterParsingNode | 解析任务参数（来源站点、关键词）           | 前端请求参数     | 站点列表、关键词      |
| WebCrawlerNode       | 爬取卫星数据（支持多站点、动态渲染）       | 站点列表、关键词 | 原始数据（HTML/JSON） |
| DataCleaningNode     | 调用大模型进行结构化                       | 原始数据         | 标准化 JSON 数据      |
| DuplicateCheckNode   | 检查 `eo_satellite.json` 是否已有记录 | 新数据           | 新增数据 / 更新数据   |
| FileWriteNode        | 将数据写入 `eo_satellite.json`        | 新增/更新数据    | 更新后的文件          |
| LoggingNode          | 写入 `crawlLogs.json`                      | 本次执行结果     | 日志文件              |
| SchedulerNode        | 定时触发爬取任务                           | 定时规则         | 启动爬取流程          |

### 爬取逻辑

**调度方式**：每周执行一次，现在开发阶段可作为指定运行


## 前端开发需求

#### 数据可视化放置位置建议

- 在“卫星管理”页面右侧栏，卫星查询助手上方新增“数据更新记录”卡片，点击可弹出卡片查看卫星数据更新情况。

#### 可视化内容

每日信息获取统计

- 折线图：每日爬取数据数量（按天/周/月切换），当日总爬取数、成功数、失败数。
- 按来源网站统计数量（饼图/柱状图）。
- 表格：显示每次爬取的详细数据（来源、数量、失败原因、数据列表）。
- 点击卫星名称可跳转到卫星详情。

## 任务分解与实施步骤

### **后端**

1.新建 `crawler` 模块（包含爬虫、结构化处理、文件写入、日志记录）。

2.编写 LangGraph 流程（7个节点）。


3.设计 API：

- `POST /crawl` → 手动触发爬取
- `GET /crawl/logs` → 获取爬取日志
- `GET /satellites/search` → 查询卫星数据

### **前端**

1.新增“数据更新”组件（折线图 + 表格）。
2.接口调用 `/crawl/logs` 渲染统计。
3.点击表格卫星名 → 调用 `/satellites/search` 展示详情。

## **注意事项**

- 我所提供的tools/sate_search中的satellite_crawler.py和satellite_data_processor.py完成了网页爬取和数据格式化内容，你可以查看
- 同时可以改我的提供的文件中的数据库操作（如果错的话），我的这两个文件可以选择保留，也可以重新写新的文件来整合，这两个文件一定要按照这个文档来重新编写。
- 前端的可视化用echarts
- LangGraph的节点设计仅供参考，不一定需要严格按照，按照你对整个流程的理解以及先前代码风格来决定代码如何书写。

## **参考网站**
**Gunter’s Space Page**（权威卫星百科）
- 网站：[https://space.skyrocket.de/](https://space.skyrocket.de/)
- 用途：几乎涵盖全球所有卫星的详细参数与历史任务。
- 该网站的爬取代码已经写好，可以直接使用。

## 可能涉及代码文件

- backend/src/api/routes.py
- backend/tools/sate_search/
- frontend/src/components/Satellite/