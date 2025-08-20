# backend/test_crawler_agent.py - 爬虫智能体集成测试

import os
import sys
import json
import asyncio
import logging
from pathlib import Path

# 确保项目根目录在sys.path中
current_file = Path(__file__).resolve()
project_root = current_file.parent
sys.path.append(str(project_root))

from backend.src.tools.crawler_agent.crawler_workflow import crawler_workflow
from backend.src.tools.sate_search.satellite_crawler import SatelliteCrawler
from backend.src.tools.sate_search.satellite_data_processor import SatelliteDataProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def test_crawler_workflow():
    """测试完整的爬虫工作流"""
    print("=" * 60)
    print("🧪 测试爬虫智能体工作流")
    print("=" * 60)
    
    try:
        # 1. 创建爬取任务
        print("\n📋 创建爬取任务...")
        job_id = await crawler_workflow.create_crawl_job(
            target_sites=["Gunter's Space Page"],
            keywords=[],
            max_satellites=3  # 限制为3个，加快测试速度
        )
        print(f"✅ 任务创建成功: {job_id}")
        
        # 2. 执行爬取任务
        print("\n🚀 执行爬取任务...")
        result = await crawler_workflow.execute_crawl_job(job_id)
        print(f"✅ 任务执行完成: {result}")
        
        # 3. 获取爬取日志
        print("\n📝 获取爬取日志...")
        logs = await crawler_workflow.get_crawl_logs(limit=5)
        print(f"✅ 获取到 {len(logs)} 条日志")
        if logs:
            latest_log = logs[0]
            print(f"最新日志: 新增{latest_log.get('newDataCount', 0)}个卫星")
        
        # 4. 获取统计信息
        print("\n📊 获取统计信息...")
        stats = await crawler_workflow.get_crawl_statistics(days=7)
        print(f"✅ 统计信息: 总爬取{stats['total_crawls']}次, 新增{stats['total_new_satellites']}个卫星")
        
        print("\n🎉 爬虫工作流测试完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 爬虫工作流测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_satellite_crawler():
    """测试卫星爬虫"""
    print("\n=" * 60)
    print("🕷️ 测试卫星爬虫")
    print("=" * 60)
    
    try:
        crawler = SatelliteCrawler()
        
        print("\n📡 爬取最近发射的卫星...")
        satellites = await crawler.crawl_recent_satellites(max_satellites=2)
        
        print(f"✅ 成功爬取 {len(satellites)} 个卫星")
        for sat in satellites:
            print(f"  - {sat.get('satellite_name', 'Unknown')}: {sat.get('launch_date', 'Unknown')}")
        
        return len(satellites) > 0
        
    except Exception as e:
        print(f"\n❌ 卫星爬虫测试失败: {str(e)}")
        return False


async def test_data_processor():
    """测试数据处理器"""
    print("\n=" * 60)
    print("🧹 测试数据处理器")
    print("=" * 60)
    
    try:
        processor = SatelliteDataProcessor()
        
        # 模拟原始数据
        raw_data = [
            {
                "satellite_name": "测试卫星-001",
                "launch_date": "05.08.2025",
                "site": "Test Launch Site",
                "vehicle": "Test Rocket",
                "detailed_specs": {
                    "nation": "Test Country",
                    "type_application": "Earth observation",
                    "mass": "500 kg"
                },
                "source_url": "https://test.example.com"
            }
        ]
        
        print("\n🔄 格式化数据...")
        formatted_data = await processor.clean_and_format_data(raw_data)
        print(f"✅ 成功格式化 {len(formatted_data)} 个卫星")
        
        if formatted_data:
            sat = formatted_data[0]
            print(f"  - 卫星名称: {sat.get('satelliteName', 'Unknown')}")
            print(f"  - 所有者: {sat.get('owner', 'Unknown')}")
            print(f"  - 应用类型: {sat.get('applications', [])}")
        
        print("\n💾 检查并存储数据...")
        storage_stats = await processor.check_and_store_satellites(formatted_data)
        print(f"✅ 存储统计: {storage_stats}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 数据处理器测试失败: {str(e)}")
        return False


async def test_api_endpoints():
    """测试API端点（模拟测试）"""
    print("\n=" * 60)
    print("🌐 测试API端点")
    print("=" * 60)
    
    try:
        # 测试爬虫工作流管理器的核心功能
        print("\n📋 测试任务管理...")
        
        # 创建任务
        job_id = await crawler_workflow.create_crawl_job(
            target_sites=["Gunter's Space Page"],
            max_satellites=1
        )
        print(f"✅ 任务创建: {job_id}")
        
        # 获取任务状态
        status = crawler_workflow.get_job_status(job_id)
        print(f"✅ 任务状态: {status['status'] if status else 'Not found'}")
        
        # 列出任务
        jobs = crawler_workflow.list_jobs()
        print(f"✅ 任务列表: {len(jobs)} 个任务")
        
        return True
        
    except Exception as e:
        print(f"\n❌ API端点测试失败: {str(e)}")
        return False


async def main():
    """主测试函数"""
    print("🎯 开始爬虫智能体集成测试")
    print("⏰ 注意: 完整测试可能需要几分钟时间...")
    
    test_results = {}
    
    # 运行测试
    test_results['crawler'] = await test_satellite_crawler()
    test_results['processor'] = await test_data_processor()
    test_results['api'] = await test_api_endpoints()
    test_results['workflow'] = await test_crawler_workflow()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📋 测试结果汇总")
    print("=" * 60)
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name.upper():<15} {status}")
    
    passed = sum(test_results.values())
    total = len(test_results)
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过! 爬虫智能体已准备就绪!")
    else:
        print(f"\n⚠️ 有 {total - passed} 项测试失败，请检查相关功能")
    
    return passed == total


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())
    
    if success:
        print("\n🚀 可以通过以下方式使用爬虫智能体:")
        print("1. 启动后端服务: python backend/main.py")
        print("2. 启动前端服务: cd frontend && npm run dev")
        print("3. 在卫星管理页面点击'数据更新'按钮")
        print("4. 或直接调用API: POST /api/crawl/start")
    else:
        print("\n❌ 测试失败，请检查错误信息并修复相关问题")
        sys.exit(1)
