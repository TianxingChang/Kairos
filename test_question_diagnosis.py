#!/usr/bin/env python3
"""
测试同步JSON诊断API的脚本
"""

import asyncio
import json
import aiohttp
from typing import Dict, Any


async def test_sync_json_api():
    """测试同步JSON API端点"""
    print("🚀 Testing Sync JSON Diagnosis API")
    print("=" * 50)
    
    # API配置
    base_url = "http://localhost:8000"
    endpoint = "/v1/questions/diagnose/sync"
    url = f"{base_url}{endpoint}"
    
    # 测试用例
    test_cases = [
        {
            "user_question": "为什么PPO算法里要用clip函数来限制策略更新的幅度？",
            "context_resource_id": 51,
            "expected_topics": ["PPO", "策略", "强化学习"]
        },
        {
            "user_question": "什么是梯度下降算法的学习率？",
            "context_resource_id": 51,
            "expected_topics": ["梯度下降", "学习率", "机器学习"]
        },
        {
            "user_question": "卷积神经网络中的池化层有什么作用？",
            "context_resource_id": 51,
            "expected_topics": ["CNN", "池化", "神经网络"]
        },
        {
            "user_question": "Transformer中的注意力机制是如何工作的？",
            "context_resource_id": 51,
            "expected_topics": ["Transformer", "注意力", "机制"]
        }
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}/{len(test_cases)}: {test_case['user_question'][:50]}...")
            
            payload = {
                "user_question": test_case["user_question"],
                "context_resource_id": test_case["context_resource_id"]
            }
            
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        print(f"   ✅ Status: {response.status}")
                        print(f"   📊 Results:")
                        print(f"      Success: {result.get('success', False)}")
                        print(f"      Diagnosed Points: {result['summary']['total_diagnosed']}")
                        print(f"      Contextual Points: {result['summary']['total_contextual']}")
                        print(f"      Max Relevance: {result['summary']['max_relevance_score']:.2f}")
                        print(f"      Used Global Search: {result.get('used_global_search', False)}")
                        
                        # 显示诊断出的知识点
                        diagnosed = result.get('diagnosed_knowledge_points', [])
                        if diagnosed:
                            print(f"      🎯 Diagnosed Knowledge Points:")
                            for j, point in enumerate(diagnosed[:3], 1):
                                title = point.get('title', 'Unknown')
                                score = point.get('relevance_score', 0)
                                explanation = point.get('explanation', 'No explanation')[:100]
                                print(f"         {j}. {title} (score: {score:.2f})")
                                print(f"            {explanation}...")
                        
                        # 显示上下文候选
                        contextual = result.get('contextual_candidate_knowledge_points', [])
                        if contextual:
                            print(f"      🔍 Contextual Candidates:")
                            for j, point in enumerate(contextual[:3], 1):
                                title = point.get('title', 'Unknown')
                                print(f"         {j}. {title}")
                        
                        results.append({
                            "test_case": test_case,
                            "success": True,
                            "result": result
                        })
                        
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Status: {response.status}")
                        print(f"   Error: {error_text}")
                        
                        results.append({
                            "test_case": test_case,
                            "success": False,
                            "error": error_text
                        })
                        
            except Exception as e:
                print(f"   💥 Exception: {str(e)}")
                results.append({
                    "test_case": test_case,
                    "success": False,
                    "error": str(e)
                })
            
            print("   " + "-" * 40)
    
    # 总结
    print(f"\n📊 Test Summary:")
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"   ✅ Successful: {successful}/{total}")
    print(f"   📈 Success rate: {(successful/total)*100:.1f}%")
    
    # 详细统计
    total_diagnosed = 0
    total_contextual = 0
    
    for result in results:
        if result["success"] and "result" in result:
            api_result = result["result"]
            total_diagnosed += api_result["summary"]["total_diagnosed"]
            total_contextual += api_result["summary"]["total_contextual"]
    
    print(f"   🎯 Total diagnosed points found: {total_diagnosed}")
    print(f"   🔍 Total contextual points found: {total_contextual}")
    
    if total_diagnosed > 0:
        print(f"   🎉 Great! The API is successfully finding relevant knowledge points.")
    else:
        print(f"   ⚠️  No diagnosed points found. The API needs further optimization.")
    
    return results


async def test_single_question():
    """快速单个问题测试"""
    print("🎯 Quick Single Question Test")
    print("=" * 30)
    
    url = "http://localhost:8000/v1/questions/diagnose/sync"
    payload = {
        "user_question": "为什么PPO算法里要用clip函数来限制策略更新的幅度？",
        "context_resource_id": 51
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    print("\n📋 Raw JSON Response:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    return result
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return None
        except Exception as e:
            print(f"💥 Exception: {str(e)}")
            return None


if __name__ == "__main__":
    print("🔧 Sync JSON Diagnosis API Tester")
    print("Choose test mode:")
    print("1. Single question test (with raw JSON)")
    print("2. Multiple questions test (comprehensive)")
    
    try:
        choice = input("\nEnter your choice (1 or 2): ").strip()
    except EOFError:
        choice = "1"
        print("\nRunning single question test (default)")
    
    if choice == "1":
        asyncio.run(test_single_question())
    elif choice == "2":
        asyncio.run(test_sync_json_api())
    else:
        print("Invalid choice. Running single question test by default.")
        asyncio.run(test_single_question())