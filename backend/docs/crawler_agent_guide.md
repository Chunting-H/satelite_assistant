# 爬虫智能体使用指南

## 🎯 概述

爬虫智能体是一个基于LangGraph的自动化卫星信息收集系统，可以定期从指定网站爬取最新的卫星数据，使用大模型进行数据结构化，并存储到本地数据库中。

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   后端API       │    │   爬虫智能体    │
│                 │    │                 │    │                 │
│ - 数据更新按钮  │───▶│ - 任务管理      │───▶│ - 网页爬取      │
│ - 统计图表      │    │ - 状态查询      │    │ - 数据清洗      │
│ - 详细日志      │    │ - 日志获取      │    │ - 存储管理      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲                       │
                                │                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   数据库文件    │    │   大模型API     │
                       │                 │    │                 │
                       │ - eo_satellite  │    │ - DeepSeek      │
                       │ - crawlLogs     │    │ - ChatGPT       │
                       └─────────────────┘    └─────────────────┘
```

## 🔧 核心组件

### 1. LangGraph工作流节点

| 节点名称 | 功能描述 | 输入 | 输出 |
|---------|----------|------|------|
| ParameterParsingNode | 解析任务参数 | 前端请求参数 | 站点列表、关键词 |
| WebCrawlerNode | 爬取卫星数据 | 站点列表、关键词 | 原始HTML/JSON数据 |
| DataCleaningNode | 数据结构化 | 原始数据 | 标准化JSON数据 |
| DuplicateCheckNode | 检查重复数据 | 新数据 | 新增/更新数据 |
| FileWriteNode | 写入数据文件 | 新增/更新数据 | 更新后的文件 |
| LoggingNode | 记录日志 | 执行结果 | 日志文件 |

### 2. 数据流转

```
用户请求 → 参数解析 → 网页爬取 → 数据清洗 → 重复检查 → 文件写入 → 日志记录 → 完成
```

## 🚀 使用方法

### 前端操作

1. **访问卫星管理页面**
   ```
   前端地址: http://localhost:5173
   路径: 主页 → 卫星管理
   ```

2. **打开数据更新界面**
   - 点击卫星管理页面右上角的"数据更新"按钮
   - 弹出数据更新记录窗口

3. **查看统计信息**
   - 统计概览：显示爬取次数、新增卫星数等
   - 图表分析：每日数据趋势、来源分布等
   - 详细日志：每次爬取的具体信息

4. **手动触发爬取**
   - 点击"手动更新"按钮
   - 系统自动开始爬取最新卫星数据
   - 实时显示任务状态和进度

### API调用

1. **启动爬取任务**
   ```bash
   POST /api/crawl/start
   Content-Type: application/json
   
   {
     "target_sites": ["Gunter's Space Page"],
     "keywords": [],
     "max_satellites": 10
   }
   ```

2. **查询任务状态**
   ```bash
   GET /api/crawl/status/{job_id}
   ```

3. **获取爬取日志**
   ```bash
   GET /api/crawl/logs?limit=50
   ```

4. **获取统计信息**
   ```bash
   GET /api/crawl/statistics?days=30
   ```

## 📊 数据结构

### eo_satellite.json 格式

```json
{
  "satelliteName": "EXPLORER 7",
  "alternateNames": ["Explorer 7", "NASA S-1A"],
  "COSPARId": "1959-009A",
  "NORADId": 22,
  "operStatusCode": "Unknown",
  "satelliteAgencies": "NASA",
  "owner": "United States",
  "launchDate": "1959-10-13",
  "launchSite": "Air Force Eastern Test Range",
  "applications": ["Earth observation"],
  "period": 95.46,
  "inclination": 50.28,
  "apogee": 617.0,
  "perigee": 465.0,
  "dryMass": 41.0,
  "launchMass": 41.0,
  "orbitType": "LEO_I"
}
```

### crawlLogs.json 格式

```json
[
  {
    "crawlTime": "2025-01-27T09:00:00Z",
    "targetSites": ["Gunter's Space Page"],
    "newDataCount": 5,
    "updatedDataCount": 0,
    "failedCount": 0,
    "dataList": ["Satellite A", "Satellite B"],
    "executionTime": 45.2,
    "totalProcessed": 5
  }
]
```

## ⚙️ 配置选项

### 环境变量

```bash
# DeepSeek API配置（用于数据结构化）
DEEPSEEK_API_KEY=your_deepseek_api_key

# 其他模型API（可选）
OPENAI_API_KEY=your_openai_api_key
QWEN_API_KEY=your_qwen_api_key
```

### 爬取参数

- **target_sites**: 目标网站列表，当前支持 "Gunter's Space Page"
- **keywords**: 搜索关键词（暂未实现）
- **max_satellites**: 最大爬取数量（1-50）

## 🔍 监控和调试

### 日志级别

- **INFO**: 基本执行信息
- **ERROR**: 错误信息
- **DEBUG**: 详细调试信息

### 常见问题

1. **爬取失败**
   - 检查网络连接
   - 验证目标网站可访问性
   - 查看错误日志

2. **数据格式化失败**
   - 检查DeepSeek API密钥
   - 验证API配额
   - 查看模型响应

3. **存储失败**
   - 检查磁盘空间
   - 验证文件权限
   - 查看数据目录路径

## 📈 性能优化

### 爬取策略

- **并发控制**: 限制同时爬取的页面数量
- **请求延迟**: 避免对目标网站造成压力
- **重试机制**: 处理网络异常和临时错误

### 数据处理

- **批量处理**: 分批调用大模型API
- **缓存机制**: 避免重复处理相同数据
- **增量更新**: 只处理新增和变更的数据

## 🎯 未来扩展

### 计划功能

1. **多网站支持**: 添加NASA EO Portal等数据源
2. **智能调度**: 基于数据更新频率自动调整爬取间隔
3. **数据质量检查**: 自动验证爬取数据的完整性和准确性
4. **增量同步**: 支持增量数据更新而非全量替换

### 扩展方向

1. **更多数据源**: ESA、JAXA等其他空间机构
2. **实时通知**: 新卫星发射的实时提醒
3. **数据分析**: 卫星发射趋势分析
4. **API集成**: 对接第三方卫星数据API

## 📞 技术支持

如遇到问题，请：

1. 查看系统日志文件
2. 运行测试脚本: `python backend/test_crawler_agent.py`
3. 检查API响应状态
4. 联系技术支持团队
