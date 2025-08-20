**开发目标**
为项目新增 **卫星管理助手**，该助手与 **主助手** 完全独立，二者的对话内容互不影响。
本次任务是构建一个 **搜索智能体（Agent）**，帮助用户查询卫星信息。

**功能需求**

1. **新增路由**

   * 在 `routes.py` 中添加 `POST` 路径，用于接收用户的卫星查询请求。

2. **对话逻辑**

   * 参考 `graph/state.py` 和 `graph/workflow_streaming.py` 的结构与风格，重新编写卫星管理助手的对话逻辑。
   * 使用 **DeepSeek 大模型** 处理对话与结果格式化。

3. **检索与搜索流程**

   1. 用户输入卫星名称或相关信息后，智能体先在 **本地数据库** 检索是否已有记录。目前没有数据库，只有存储卫星的eo_satellite.json文件，卫星结构实例如下：
   ```json
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
      * 若有 → 直接返回数据库中的卫星信息。
      * 若无 → 启动 **网络搜索**（搜索工具代码放在 `tools` 文件夹）。
   2. 网络搜索完成后，由 **大模型** 对结果进行格式化,要求符合我们存储在json文件中的卫星数据格式，并返回给用户。
   3. 返回结果后，向用户确认是否将该卫星信息保存到本地数据库（需按标准化格式存储）。

4. **数据库操作**

   * 数据保存需遵循既定的卫星信息标准化格式。

5. **测试方式**

   * 在后端直接使用 Python 脚本连接测试，方便调试和验证功能。

6. **开发语言**
    * Langchain和LangGraph。