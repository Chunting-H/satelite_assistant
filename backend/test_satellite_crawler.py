# test_satellite_crawler.py

import os
import sys
import asyncio
import json
from pathlib import Path

# 确保项目根目录在sys.path中
current_file = Path(__file__).resolve()
project_root = current_file.parent
sys.path.append(str(project_root))

# 添加backend目录到sys.path
backend_dir = project_root / "backend"
sys.path.append(str(backend_dir))

try:
    from backend.src.tools.satellite_crawler import SatelliteCrawler
    from backend.src.tools.satellite_data_processor import SatelliteDataProcessor
    print("✅ 成功导入爬虫模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)


async def test_crawler():
    """测试卫星爬虫功能"""
    print("=" * 60)
    print("🚀 开始测试卫星爬虫功能")
    print("=" * 60)
    
    try:
        # 1. 测试爬虫初始化
        print("\n1️⃣ 测试爬虫初始化...")
        crawler = SatelliteCrawler()
        print("✅ 爬虫初始化成功")
        
        # 2. 测试获取主页内容
        print("\n2️⃣ 测试获取主页内容...")
        main_page_content = await crawler.fetch_page(crawler.base_url)
        if main_page_content:
            print(f"✅ 成功获取主页内容，长度: {len(main_page_content)} 字符")
        else:
            print("❌ 获取主页内容失败")
            return
        
        # 3. 测试解析最近发射列表
        print("\n3️⃣ 测试解析最近发射列表...")
        recent_satellites = crawler.parse_recent_launches(main_page_content)
        print(f"✅ 解析到 {len(recent_satellites)} 个最近发射的卫星")
        
        if recent_satellites:
            print("\n📡 最近发射的卫星列表（前5个）:")
            for i, sat in enumerate(recent_satellites[:5], 1):
                print(f"  {i}. {sat['satellite_name']} ({sat['launch_date']})")
                print(f"     发射载具: {sat['vehicle']}")
                print(f"     发射场: {sat['site']}")
                print(f"     详情链接: {sat['satellite_url']}")
                print()
        
        # 4. 测试爬取单个卫星详情
        if recent_satellites:
            print("\n4️⃣ 测试爬取单个卫星详情...")
            first_satellite = recent_satellites[0]
            detail_info = await crawler.crawl_satellite_detail(
                first_satellite['satellite_url'], 
                first_satellite['satellite_name']
            )
            
            if detail_info:
                print(f"✅ 成功爬取卫星详情: {first_satellite['satellite_name']}")
                print(f"📊 详情信息键值对数量: {len(detail_info)}")
                
                # 显示详情信息
                print("\n🔍 卫星详情信息:")
                for key, value in detail_info.items():
                    if key not in ['raw_content']:  # 跳过原始内容
                        print(f"  {key}: {value}")
            else:
                print(f"❌ 爬取卫星详情失败: {first_satellite['satellite_name']}")
        
        # 5. 测试数据处理器
        print("\n5️⃣ 测试数据处理器...")
        processor = SatelliteDataProcessor()
        
        if recent_satellites:
            # 取前2个卫星进行格式化测试
            test_data = recent_satellites[:2]
            
            print(f"🔄 开始格式化 {len(test_data)} 个卫星数据...")
            formatted_data = await processor.clean_and_format_data(test_data)
            
            if formatted_data:
                print(f"✅ 成功格式化 {len(formatted_data)} 个卫星数据")
                
                # 显示格式化后的第一个卫星信息
                if len(formatted_data) > 0:
                    first_formatted = formatted_data[0]
                    print(f"\n📋 格式化后的卫星信息示例 ({first_formatted.get('satelliteName', 'Unknown')}):")
                    for key, value in first_formatted.items():
                        if key not in ['_crawl_metadata']:
                            print(f"  {key}: {value}")
            else:
                print("❌ 数据格式化失败")
        
        print("\n🎉 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 确保关闭会话
        await crawler.close_session()


async def test_api_endpoints():
    """测试API端点（模拟请求）"""
    print("\n" + "=" * 60)
    print("🌐 API端点功能说明")
    print("=" * 60)
    
    endpoints = [
        {
            "method": "POST",
            "path": "/api/satellite/crawl",
            "description": "执行卫星爬虫任务",
            "example_request": {
                "mode": "recent",
                "max_satellites": 5
            }
        },
        {
            "method": "POST", 
            "path": "/api/satellite/crawl",
            "description": "搜索单个卫星",
            "example_request": {
                "mode": "single",
                "satellite_name": "Starlink"
            }
        },
        {
            "method": "GET",
            "path": "/api/satellite/crawl/logs",
            "description": "获取爬虫日志列表",
            "example_params": "?limit=10&offset=0"
        },
        {
            "method": "GET",
            "path": "/api/satellite/crawl/logs/{filename}",
            "description": "获取爬虫日志详情",
            "example": "/api/satellite/crawl/logs/satellite_crawl_20250129_143022.json"
        },
        {
            "method": "GET",
            "path": "/api/satellite/data/stats",
            "description": "获取卫星数据统计信息",
            "returns": "文件大小、卫星总数、最后修改时间等"
        }
    ]
    
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n{i}️⃣ {endpoint['method']} {endpoint['path']}")
        print(f"   📝 {endpoint['description']}")
        
        if 'example_request' in endpoint:
            print(f"   📤 请求示例: {json.dumps(endpoint['example_request'], ensure_ascii=False)}")
        
        if 'example_params' in endpoint:
            print(f"   🔗 参数示例: {endpoint['example_params']}")
        
        if 'example' in endpoint:
            print(f"   🌐 路径示例: {endpoint['example']}")
        
        if 'returns' in endpoint:
            print(f"   📥 返回内容: {endpoint['returns']}")


if __name__ == "__main__":
    print("🤖 卫星管理助手爬虫测试程序")
    print("🌐 目标网站: https://space.skyrocket.de")
    print("📊 数据格式: 符合agent.md中定义的JSON格式")
    print("🎯 功能: 爬取最近发射卫星 + 单卫星搜索 + 数据格式化 + 存储")
    
    # 运行爬虫测试
    asyncio.run(test_crawler())
    
    # 显示API端点信息
    asyncio.run(test_api_endpoints())
    
    print("\n" + "=" * 60)
    print("✨ 爬虫智能体开发完成！")
    print("=" * 60)
    print("🚀 启动方式: python -m backend.main")
    print("📚 API文档: http://localhost:2025/docs")
    print("🔗 爬虫端点: POST /api/satellite/crawl")
    print("📊 数据统计: GET /api/satellite/data/stats")
    print("📝 爬虫日志: GET /api/satellite/crawl/logs")
    print("=" * 60)
