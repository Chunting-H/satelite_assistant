
## **任务目标**
构建一个面向“卫星管理助手”的爬虫智能体，实现自动化的卫星信息收集、格式化、入库及日志记录。

##  **功能流程**

1. **路由定义**：在 `routes.py` 中添加 POST 路由，用于接收爬虫请求。
2. **数据获取**：根据请求参数执行网页搜索与爬虫任务，自动访问指定的卫星信息网站（爬取下面的指定网站即可），采集该网页记录的最近发射所有卫星数据，也可以执行单卫星搜索。
3. **数据清洗与结构化**：将原始爬取数据(单个卫星要单独进入其网页爬取该卫星的相关信息，网页结构在下方代码中)输入 DeepSeek 大模型（API 调用），在特定的 Prompt 约束下，执行格式化、标准化和噪声清理，生成统一的结构化卫星信息（如卫星名称、发射时间、轨道类型、用途、制造商、运营商等字段）。
4. **数据库检查与存储**：查询数据库中是否已存在相同卫星记录；若不存在，则将新数据写入数据库，并保证数据完整性与字段一致性。
5. **日志记录**：记录本次爬取的执行时间、目标网站、数据量及结果状态，便于后续溯源与监控。

## **注意事项**

- 目前我们没有数据库，是存储在json文件中：data/eosatellite.json。
- 爬取网站的更新频率较低，需要定期更新数据。

## 数据格式

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

## **爬取网站**

**Gunter’s Space Page**（权威卫星百科）
- 网站：[https://space.skyrocket.de/](https://space.skyrocket.de/)
- 用途：几乎涵盖全球所有卫星的详细参数与历史任务。

我进入网站后发现这里面是最近发射的卫星，进入herf网站是该卫星的详细信息，可以爬取这些数据。
``` html
<table class="hplist">
  <!--  <colgroup>
    <col style="width:5%">
    <col style="width:5%">
	<col style="width:40%">
	<col style="width:23%">
	<col style="width:10%">
	<col style="width:17%">
  </colgroup>-->
  <colgroup>
    <col style="width:5%">
    <col style="width:5%">
	<col style="width:56%">
	<col style="width:14%">
	<col style="width:10%">
	<col style="width:10%">
  </colgroup>
  <tr>
    <th>ID</th>
    <th>Date</th>
    <th>Payload(s)</th>
    <th>Vehicle</th>
    <th>Site</th>
    <th>Remark</th>
  </tr>
  <tr>
    <td>2025-169</td>
    <td>05.08.2025</td>
    <td><a href="doc_sdat/qps-sar-3.htm">QPS-SAR 12 (Kushinada 1)</a></td>
    <td><a href="doc_lau_det/electron_ks.htm">Electron KS</a></td>
    <td>OnS LC-1B</td>
    <td></td>
  </tr>
  <tr>
    <td>2025-168</td>
    <td>04.08.2025</td>
    <td><a href="doc_sdat/hwd-07.htm">HWD L7-01, ..., L07-09 (Hulianwang 49, ..., 57)</a></td>
    <td><a href="doc_lau/cz-12.htm">CZ-12</a></td>
    <td>HCS LP-2</td>
    <td></td>
  </tr>
  <tr>
    <td>2025-167</td>
    <td>04.08.2025</td>
    <td><a href="doc_sdat/starlink-v2-mini.htm">Starlink v2-Mini G10-23-1, ..., G10-23-28</a></td>
    <td><a href="doc_lau_det/falcon-9_v1-2_b5.htm">Falcon-9 v1.2 (Block 5)</a></td>
    <td>CC SLC-40</td>
    <td></td>
  </tr>
  <tr>
    <td>2025-166</td>
    <td>01.08.2025</td>
    <td><a href="doc_sdat/dragon-v2.htm">Dragon Crew 11 (Endeavour F6)</a></td>
    <td><a href="doc_lau_det/falcon-9_v1-2_b5.htm">Falcon-9 v1.2 (Block 5)</a></td>
    <td>CCK LC-39A</td>
    <td></td>
  </tr>
  <tr>
    <td>2025-165</td>
    <td>31.07.2025</td>
    <td><a href="doc_sdat/starlink-v2-mini.htm">Starlink v2-Mini G13-4-1, ..., G13-4-19</a> / <a href="doc_sdat/usa-350.htm">USA 549, 550 ?</a></td>
    <td><a href="doc_lau_det/falcon-9_v1-2_b5.htm">Falcon-9 v1.2 (Block 5)</a></td>
    <td>Va SLC-4E</td>
    <td></td>
  </tr>
 </table>
```

单个卫星的详细页面：
``` html
<div id="satdescription">

<!--<div id="contimg" class="ibox"><img src="../img_sat/whwd__1.jpg" alt="" width="208" height="300" border="0"><p>HWD  []</p></div>-->

<p><strong>HWD</strong> (<strong>Huliangwang Weixing Digui</strong>)</p>

</div>


<div class="clearall"></div>

<table id="satdata" class="data">
  <tr>
    <th class="lhead">Nation:</th>
    <td class="rcont" id="sdnat">China</td>
  </tr>
  <tr>
    <th class="lhead">Type / Application:</th>
    <td class="rcont" id="sdtyp">Communication</td>
  </tr>
  <tr>
    <th class="lhead">Operator:</th>
    <td class="rcont" id="sdope">China Satnet</td>
  </tr>
  <tr>
    <th class="lhead">Contractors:</th>
    <td class="rcont" id="sdcon">Yinhe (Galaxy Space)</td>
  </tr>
  <tr>
    <th class="lhead">Equipment:</th>
    <td class="rcont" id="sdequ"></td>
  </tr>
  <tr>
    <th class="lhead">Configuration:</th>
    <td class="rcont" id="sdcnf"></td>
  </tr>
  <tr>
    <th class="lhead">Propulsion:</th>
    <td class="rcont" id="sdpro"></td>
  </tr>
  <tr>
    <th class="lhead">Power:</th>
    <td class="rcont" id="sdpow">Solar array, batteries</td>
  </tr>
  <tr>
    <th class="lhead">Lifetime:</th>
    <td class="rcont" id="sdlif"></td>
  </tr>
  <tr>
    <th class="lhead">Mass:</th>
    <td class="rcont" id="sdmas"></td>
  </tr>
  <tr>
    <th class="lhead">Orbit:</th>
    <td class="rcont" id="sdorb"></td>
  </tr>
</table>
```