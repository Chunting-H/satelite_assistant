## 后端部分
- backend/src/api/routes.py中加了智能体爬虫、调用工具的路由
- backend/src/tools中两个文件夹crawler_agent，sate_search、data_processor.py
- backend/src/graph/state.py
- backend/config/config.py你们如果没改的话可以直接覆盖
- backend\main.py
- 
## data部分

- data/logs存储爬取记录
- data/samples存储图像处理
- data/crawlLogs存储爬取总结记录
- data/eo_satelite.zh.json存储卫星数据库

## 前端部分
- frontend/src/App.jsx应该修改了
- frontend/src/components/chat/ProcessingResultViewer.jsx
- frontend/src/components/UI/ProcessingProgressBar.jsx
- frontend/src/components/Chat/DataProcessingDialog.jsx
- frontend/src/components/Chat/EnhancedStreamingMessage.jsx
- frontend/src/components/Chat/.ipynb_checkpoints/EnhancedStreamingMessage-checkpoint.jsx
- frontend/src/components/satellite/DataupdateRecords.jsx
- frontend/src/components/satellite/SatelliteManagement.jsx 引入dataupdateRecords.jsx
