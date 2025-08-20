import requests
import json
import asyncio
import aiohttp
import time
from typing import Dict, Any


class JiuzhouAPITester:
    """九州API测试类"""

    def __init__(self):
        self.base_url = "https://wisemodel.cn/apiserving/"
        self.headers = {
            'publisher-name': 'wwzc3',
            'api-key': 'wisemodel-xoyfywrtbialazhnrvvh',  # 从你的配置中获取
            'serving-name-en': 'bxgiytas',
            'Content-Type': 'application/json'
        }
        self.model = "Mistral"

    def test_sync_non_stream(self):
        """测试同步非流式请求"""
        print("\n" + "=" * 50)
        print("测试1: 同步非流式请求")
        print("=" * 50)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的地理信息和遥感专家，擅长分析用户的卫星监测需求并提供专业建议。请用中文回答。"
                },
                {
                    "role": "user",
                    "content": "你好，请介绍一下你自己"
                }
            ],
            "stream": False,
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            start_time = time.time()
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            end_time = time.time()

            print(f"状态码: {response.status_code}")
            print(f"耗时: {end_time - start_time:.2f}秒")
            print(f"响应头: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"响应JSON结构: {list(result.keys())}")
                    if 'choices' in result and result['choices']:
                        content = result['choices'][0]['message']['content']
                        print(f"AI回复: {content[:200]}...")
                    else:
                        print(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    print(f"原始响应: {response.text[:500]}")
            else:
                print(f"错误响应: {response.text}")

        except requests.exceptions.Timeout:
            print("请求超时")
        except requests.exceptions.ConnectionError as e:
            print(f"连接错误: {e}")
        except Exception as e:
            print(f"未知错误: {type(e).__name__}: {e}")

    def test_sync_stream(self):
        """测试同步流式请求"""
        print("\n" + "=" * 50)
        print("测试2: 同步流式请求")
        print("=" * 50)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": "简单说说什么是遥感卫星"
                }
            ],
            "stream": True,
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30,
                stream=True
            )

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                full_content = ""
                chunk_count = 0

                for line in response.iter_lines():
                    if line:
                        chunk_count += 1
                        line_str = line.decode('utf-8')
                        print(f"Chunk {chunk_count}: {line_str[:100]}...")

                        if line_str.startswith('data: '):
                            if line_str == 'data: [DONE]':
                                break
                            try:
                                data = json.loads(line_str[6:])
                                if 'choices' in data and data['choices']:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        full_content += delta['content']
                            except json.JSONDecodeError:
                                pass

                print(f"\n总块数: {chunk_count}")
                print(f"完整内容: {full_content[:200]}...")
            else:
                print(f"错误响应: {response.text}")

        except Exception as e:
            print(f"错误: {type(e).__name__}: {e}")

    async def test_async_non_stream(self):
        """测试异步非流式请求"""
        print("\n" + "=" * 50)
        print("测试3: 异步非流式请求")
        print("=" * 50)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": "卫星监测水质需要什么参数？"
                }
            ],
            "stream": False,
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9
        }

        timeout = aiohttp.ClientTimeout(total=30)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start_time = time.time()
                async with session.post(
                        self.base_url,
                        headers=self.headers,
                        json=payload
                ) as response:
                    end_time = time.time()

                    print(f"状态码: {response.status}")
                    print(f"耗时: {end_time - start_time:.2f}秒")

                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            result = json.loads(response_text)
                            print(f"响应JSON结构: {list(result.keys())}")
                            if 'choices' in result and result['choices']:
                                content = result['choices'][0]['message']['content']
                                print(f"AI回复: {content[:200]}...")
                            else:
                                print(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        except json.JSONDecodeError as e:
                            print(f"JSON解析错误: {e}")
                            print(f"原始响应: {response_text[:500]}")
                    else:
                        print(f"错误响应: {response_text}")

        except asyncio.TimeoutError:
            print("异步请求超时")
        except aiohttp.ClientError as e:
            print(f"异步客户端错误: {e}")
        except Exception as e:
            print(f"异步未知错误: {type(e).__name__}: {e}")

    async def test_async_stream(self):
        """测试异步流式请求（模拟你代码中的调用方式）"""
        print("\n" + "=" * 50)
        print("测试4: 异步流式请求（模拟实际调用）")
        print("=" * 50)

        # 模拟你的参数澄清提示词
        prompt = """深度分析用户的卫星监测需求，识别所有参数需求（显式和隐含）。

用户输入：我需要监测青海湖的水质变化

请分析：
1. 用户的核心监测意图
2. 已明确提供的参数
3. 可以推断的隐含参数

返回JSON格式：
{
    "intent": {
        "primary": "主要意图",
        "domain": "应用领域"
    },
    "provided_params": {
        "参数名": {
            "value": "参数值",
            "confidence": 0.9
        }
    },
    "missing_params": {
        "参数名": {
            "importance": "high/medium/low",
            "reason": "为什么需要"
        }
    }
}"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的地理信息和遥感专家，擅长分析用户的卫星监测需求并提供专业建议。请用中文回答。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": True,
            "max_tokens": 2000,
            "temperature": 0.35,  # 使用更低的温度
            "top_p": 0.9
        }

        timeout = aiohttp.ClientTimeout(total=30)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                        self.base_url,
                        headers=self.headers,
                        json=payload
                ) as response:
                    print(f"状态码: {response.status}")
                    response_text = await response.text()

                    if response.status != 200:
                        print(f"错误状态码: {response.status}")
                        print(f"错误响应: {response_text}")
                        return

                    # 处理流式响应
                    full_content = ""
                    lines = response_text.strip().split('\n')

                    for line in lines:
                        line = line.strip()
                        if line.startswith('data: '):
                            try:
                                if line == 'data: [DONE]':
                                    break

                                data = json.loads(line[6:])
                                if 'choices' in data and data['choices']:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        full_content += delta['content']
                            except json.JSONDecodeError as e:
                                print(f"解析流式响应行失败: {line}, 错误: {e}")
                                continue

                    print(f"\n完整响应内容:\n{full_content}")

                    # 尝试解析JSON
                    try:
                        json_start = full_content.find('{')
                        json_end = full_content.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = full_content[json_start:json_end]
                            parsed_result = json.loads(json_str)
                            print(f"\n解析后的JSON:\n{json.dumps(parsed_result, ensure_ascii=False, indent=2)}")
                    except Exception as e:
                        print(f"\nJSON解析失败: {e}")

        except Exception as e:
            print(f"异步流式请求错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    def test_error_cases(self):
        """测试错误情况"""
        print("\n" + "=" * 50)
        print("测试5: 错误情况测试")
        print("=" * 50)

        # 测试1: 错误的API密钥
        print("\n子测试1: 错误的API密钥")
        headers_wrong_key = self.headers.copy()
        headers_wrong_key['api-key'] = 'wrong-key'

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "test"}],
            "stream": False
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers_wrong_key,
                json=payload,
                timeout=10
            )
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text[:200]}")
        except Exception as e:
            print(f"错误: {e}")

        # 测试2: 错误的模型名
        print("\n子测试2: 错误的模型名")
        payload_wrong_model = payload.copy()
        payload_wrong_model['model'] = 'WrongModel'

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload_wrong_model,
                timeout=10
            )
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text[:200]}")
        except Exception as e:
            print(f"错误: {e}")


async def main():
    """主测试函数"""
    tester = JiuzhouAPITester()

    # 1. 同步测试
    tester.test_sync_non_stream()
    tester.test_sync_stream()

    # 2. 异步测试
    await tester.test_async_non_stream()
    await tester.test_async_stream()

    # 3. 错误测试
    tester.test_error_cases()

    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    # 对于Python 3.7+
    asyncio.run(main())

    # 如果上面的不工作，使用这个：
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())