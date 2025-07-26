#!/usr/bin/env python3
"""
测试视频答案API (API 5) 的脚本
基于问题拆解和视频片段检索的智能问答系统
"""

import asyncio
import aiohttp
import time


async def test_sync_video_answer():
    """测试同步视频答案API"""
    print("🚀 Testing Sync Video Answer API (API 5)")
    print("=" * 60)
    
    # API配置
    base_url = "http://localhost:8000"
    endpoint = "/v1/video-answers/sync"
    url = f"{base_url}{endpoint}"
    
    # 测试用例
    test_cases = [
        {
            "user_question": "为什么PPO算法里要用clip函数来限制策略更新的幅度？",
            "context_resource_id": 298,  # 可选：特定视频资源ID
            "max_video_segments": 5,
            "enable_global_search": True
        },
        {
            "user_question": "什么是卷积神经网络中的池化层，它有什么作用？",
            "context_resource_id": None,  # 全局搜索
            "max_video_segments": 3,
            "enable_global_search": True
        },
        {
            "user_question": "Transformer中的注意力机制是如何工作的？请详细解释其计算过程。",
            "context_resource_id": None,
            "max_video_segments": 6,
            "enable_global_search": True
        }
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}/{len(test_cases)}: {test_case['user_question'][:60]}...")
            
            try:
                start_time = time.time()
                
                async with session.post(url, json=test_case) as response:
                    elapsed_time = time.time() - start_time
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        print(f"   ✅ Status: {response.status}")
                        print(f"   ⏱️  Response Time: {elapsed_time:.2f}s")
                        print(f"   📊 Results Summary:")
                        print(f"      Success: {result.get('success', False)}")
                        print(f"      Question Breakdowns: {len(result.get('question_breakdowns', []))}")
                        print(f"      Total Video Segments: {result.get('total_video_segments', 0)}")
                        print(f"      Search Strategy: {result.get('search_strategy', 'unknown')}")
                        print(f"      Processing Time: {result.get('processing_time_seconds', 0):.2f}s")
                        
                        # 显示问题拆解和对应的视频答案
                        breakdowns = result.get('question_breakdowns', [])
                        for j, breakdown in enumerate(breakdowns, 1):
                            print(f"      \n🔍 Sub-Question {j}: {breakdown.get('sub_question', 'N/A')}")
                            print(f"         Knowledge Focus: {breakdown.get('knowledge_focus', 'N/A')}")
                            print(f"         Video Segments Found: {len(breakdown.get('video_segments', []))}")
                            
                            # 显示找到的视频片段
                            segments = breakdown.get('video_segments', [])
                            for k, segment in enumerate(segments[:2], 1):  # 只显示前2个
                                video_info = segment.get('video_resource', {})
                                time_info = segment.get('time_range', {})
                                print(f"            📹 Segment {k}: {video_info.get('title', 'Unknown')[:40]}")
                                print(f"               Time: {time_info.get('start_time', '')} - {time_info.get('end_time', '')}")
                                print(f"               Relevance: {segment.get('relevance_score', 0):.2f}")
                            
                            # 显示答案摘要
                            answer = breakdown.get('answer_summary', 'No answer generated')
                            print(f"         📝 Answer: {answer[:150]}...")
                        
                        results.append({
                            "test_case": test_case,
                            "success": True,
                            "result": result,
                            "response_time": elapsed_time
                        })
                        
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Status: {response.status}")
                        print(f"   Error: {error_text}")
                        
                        results.append({
                            "test_case": test_case,
                            "success": False,
                            "error": error_text,
                            "response_time": elapsed_time
                        })
                        
            except Exception as e:
                print(f"   💥 Exception: {str(e)}")
                results.append({
                    "test_case": test_case,
                    "success": False,
                    "error": str(e),
                    "response_time": 0
                })
            
            print("   " + "-" * 50)
    
    # 总结
    print(f"\n📊 Test Summary:")
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"   ✅ Successful: {successful}/{total}")
    print(f"   📈 Success rate: {(successful/total)*100:.1f}%")
    
    # 性能统计
    response_times = [r["response_time"] for r in results if r["success"]]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"   ⚡ Average Response Time: {avg_time:.2f}s")
    
    # 详细统计
    total_breakdowns = 0
    total_segments = 0
    
    for result in results:
        if result["success"] and "result" in result:
            api_result = result["result"]
            breakdowns = api_result.get("question_breakdowns", [])
            total_breakdowns += len(breakdowns)
            total_segments += api_result.get("total_video_segments", 0)
    
    print(f"   🧩 Total Question Breakdowns: {total_breakdowns}")
    print(f"   📹 Total Video Segments Found: {total_segments}")
    
    if total_segments > 0:
        print(f"   🎉 Great! The API is successfully finding and analyzing video content.")
    else:
        print(f"   ⚠️  No video segments found. Check if video data exists in the database.")
    
    return results


async def test_async_video_answer():
    """测试异步视频答案API"""
    print("\n🎯 Testing Async Video Answer API")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    create_endpoint = "/v1/video-answers/async"
    
    payload = {
        "user_question": "解释深度学习中的反向传播算法，包括梯度计算和参数更新过程",
        "context_resource_id": None,
        "max_video_segments": 8,
        "enable_global_search": True
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # 创建异步任务
            print(f"🚀 Creating async job for complex question...")
            
            async with session.post(f"{base_url}{create_endpoint}", json=payload) as response:
                if response.status == 202:
                    job_info = await response.json()
                    job_id = job_info["job_id"]
                    status_url = f"{base_url}{job_info['status_url']}"
                    
                    print(f"   ✅ Job created: {job_id}")
                    print(f"   📋 Status URL: {status_url}")
                    
                    # 轮询任务状态
                    print(f"\n📊 Monitoring job progress...")
                    max_attempts = 20
                    
                    for attempt in range(max_attempts):
                        await asyncio.sleep(3)  # 等待3秒
                        
                        async with session.get(status_url) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                
                                print(f"   🔍 Attempt {attempt + 1}: {status_data['status']} "
                                      f"({status_data['progress_percentage']}%) - {status_data['message']}")
                                
                                if status_data['status'] == 'completed':
                                    print(f"\n🎉 Job completed successfully!")
                                    
                                    # 显示结果摘要
                                    result = status_data.get('result', {})
                                    if result:
                                        print(f"   📊 Final Results:")
                                        print(f"      Question Breakdowns: {len(result.get('question_breakdowns', []))}")
                                        print(f"      Total Video Segments: {result.get('total_video_segments', 0)}")
                                        print(f"      Processing Time: {result.get('processing_time_seconds', 0):.2f}s")
                                    
                                    return status_data
                                    
                                elif status_data['status'] == 'failed':
                                    print(f"\n❌ Job failed: {status_data.get('error_message', 'Unknown error')}")
                                    return status_data
                            else:
                                print(f"   ⚠️  Status check failed: {status_response.status}")
                    
                    print(f"\n⏰ Timeout waiting for job completion")
                    return None
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to create job: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            print(f"💥 Exception in async test: {str(e)}")
            return None


async def test_video_segment_search():
    """测试视频片段搜索功能"""
    print("\n🔍 Testing Video Segment Search")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    endpoint = "/v1/video-answers/search/segments"
    
    test_queries = [
        {
            "question": "PPO算法",
            "resource_ids": "298",  # 特定资源
            "max_results": 5
        },
        {
            "question": "神经网络训练",
            "resource_ids": None,  # 全局搜索
            "max_results": 3
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔎 Search {i}: {query['question']}")
            
            params = {
                "question": query["question"],
                "max_results": query["max_results"]
            }
            if query["resource_ids"]:
                params["resource_ids"] = query["resource_ids"]
            
            try:
                async with session.get(f"{base_url}{endpoint}", params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        print(f"   ✅ Found {result.get('total_results', 0)} segments")
                        
                        segments = result.get('segments', [])
                        for j, segment in enumerate(segments[:2], 1):
                            video_info = segment.get('video_resource', {})
                            time_info = segment.get('time_range', {})
                            print(f"      📹 {j}. {video_info.get('title', 'Unknown')[:30]}")
                            print(f"         Time: {time_info.get('start_time', '')} - {time_info.get('end_time', '')}")
                            print(f"         Score: {segment.get('relevance_score', 0):.2f}")
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Search failed: {response.status} - {error_text}")
                        
            except Exception as e:
                print(f"   💥 Exception: {str(e)}")


async def test_health_check():
    """测试健康检查"""
    print("\n🏥 Testing Health Check")
    print("=" * 30)
    
    base_url = "http://localhost:8000"
    endpoint = "/v1/video-answers/health"
    url = f"{base_url}{endpoint}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ Service Status: {result.get('status', 'unknown')}")
                    print(f"   🗄️  Database Connected: {result.get('database_connected', False)}")
                    print(f"   📹 Total Video Segments: {result.get('total_video_segments', 0)}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Health check failed: {response.status} - {error_text}")
                    
        except Exception as e:
            print(f"   💥 Health check exception: {str(e)}")


async def main():
    """主测试函数"""
    print("🎬 Video Answer API (API 5) Comprehensive Test")
    print("=" * 80)
    print(f"🚀 Starting at: {time.strftime('%H:%M:%S')}")
    
    # 1. 健康检查
    await test_health_check()
    
    # 2. 测试视频片段搜索
    await test_video_segment_search()
    
    # 3. 测试同步视频答案API
    sync_results = await test_sync_video_answer()
    
    # 4. 测试异步视频答案API（可选）
    print("\n" + "=" * 80)
    choice = input("Do you want to test async API? (y/N): ").strip().lower()
    if choice in ['y', 'yes']:
        await test_async_video_answer()
    
    print(f"\n🏁 Testing completed at: {time.strftime('%H:%M:%S')}")
    print("✅ All API 5 (Video Answer) tests finished!")
    
    return sync_results


if __name__ == "__main__":
    asyncio.run(main())