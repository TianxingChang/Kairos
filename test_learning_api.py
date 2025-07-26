#!/usr/bin/env python3
"""
测试learning.py API的脚本
测试视频前置知识分析功能
"""

import requests
import json
from typing import Dict, Any
import time

class LearningAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.api_endpoint = f"{self.base_url}/v1/learning/video/prerequisites"
    
    def test_video_prerequisites(self, video_url: str, video_title: str = None, model_type: str = "o3-mini") -> Dict[str, Any]:
        """
        测试视频前置知识分析API
        """
        payload = {
            "video_url": video_url,
            "model_type": model_type
        }
        
        if video_title:
            payload["video_title"] = video_title
        
        print(f"\n{'='*60}")
        print(f"测试视频: {video_title or video_url}")
        print(f"使用模型: {model_type}")
        print(f"API端点: {self.api_endpoint}")
        print(f"{'='*60}")
        
        try:
            start_time = time.time()
            response = requests.post(
                self.api_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300  # 5分钟超时
            )
            
            elapsed_time = time.time() - start_time
            
            print(f"HTTP状态码: {response.status_code}")
            print(f"响应时间: {elapsed_time:.2f}秒")
            
            if response.status_code == 200:
                result = response.json()
                self._print_analysis_result(result)
                return result
            else:
                print(f"错误响应: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except requests.exceptions.Timeout:
            print("❌ 请求超时")
            return {"error": "请求超时"}
        except requests.exceptions.ConnectionError:
            print("❌ 连接错误 - 请确保API服务器正在运行")
            return {"error": "连接错误"}
        except Exception as e:
            print(f"❌ 发生错误: {str(e)}")
            return {"error": str(e)}
    
    def _print_analysis_result(self, result: Dict[str, Any]):
        """打印分析结果"""
        print("\n✅ 分析成功!")
        print(f"消息: {result.get('message', 'N/A')}")
        print(f"置信度: {result.get('confidence_score', 0)}/100")
        print(f"分析模型: {result.get('analysis_model', 'N/A')}")
        
        # 打印原始JSON响应
        print(f"\n📄 原始JSON响应:")
        print("=" * 80)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        print("=" * 80)
        
        video_info = result.get('video_info', {})
        if video_info:
            print(f"\n📹 视频信息:")
            print(f"  - 标题: {video_info.get('title', 'N/A')}")
            print(f"  - URL: {video_info.get('url', 'N/A')}")
            print(f"  - 有转录文本: {video_info.get('has_transcript', False)}")
        
        prerequisites = result.get('prerequisite_knowledge', [])
        if prerequisites:
            print(f"\n📚 发现 {len(prerequisites)} 个前置知识点:")
            for i, prereq in enumerate(prerequisites, 1):
                print(f"\n  {i}. {prereq.get('title', 'N/A')}")
                print(f"     - 领域: {prereq.get('domain', 'N/A')}")
                print(f"     - 估计学习时间: {prereq.get('estimated_hours', 'N/A')} 小时")
                print(f"     - 描述: {prereq.get('description', 'N/A')[:100]}...")
                
                resources = prereq.get('learning_resources', [])
                if resources:
                    print(f"     - 推荐学习资源 ({len(resources)}个):")
                    for j, resource in enumerate(resources[:3], 1):  # 只显示前3个
                        print(f"       {j}. {resource.get('title', 'N/A')} "
                              f"(评分: {resource.get('quality_score', 0)}/10)")
                        print(f"          类型: {resource.get('resource_type', 'N/A')} | "
                              f"URL: {resource.get('resource_url', 'N/A')[:50]}...")
                else:
                    print(f"     - ⚠️  暂无推荐学习资源")
        else:
            print("\n❌ 未发现前置知识点")
    
    def test_api_health(self) -> bool:
        """测试API健康状态"""
        try:
            # 测试基础统计端点
            stats_url = f"{self.base_url}/v1/learning/stats"
            response = requests.get(stats_url, timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ API服务正常运行")
                print(f"知识点总数: {stats.get('total_knowledge_points', 0)}")
                print(f"学习资源总数: {stats.get('total_resources', 0)}")
                return True
            else:
                print(f"❌ API健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API健康检查错误: {str(e)}")
            return False

def main():
    """主测试函数"""
    print("🚀 开始测试 Learning API")
    
    # 初始化测试器
    tester = LearningAPITester()
    
    # 测试API健康状态
    if not tester.test_api_health():
        print("\n❌ API服务不可用，请检查服务器状态")
        return
    
    # 测试用的YouTube视频
    test_videos = [
        {
            "url": "https://youtu.be/OAKAZhFmYoI"
        },
        {
            "url": "https://youtu.be/-5cCWhu0OaM"
        },
        {
            "url": "https://youtu.be/rl_ozvqQUU8"
        }
    ]
    
    print(f"\n🎯 将测试 {len(test_videos)} 个视频")
    
    results = []
    
    for i, video in enumerate(test_videos, 1):
        print(f"\n{'🔍' * 20} 测试 {i}/{len(test_videos)} {'🔍' * 20}")
        
        result = tester.test_video_prerequisites(
            video_url=video["url"],
            video_title=video.get("title"),
            model_type="o3-mini"
        )
        
        results.append({
            "video": video,
            "result": result,
            "success": "error" not in result
        })
        
        # 在测试之间稍作停顿
        if i < len(test_videos):
            print("\n⏳ 等待5秒后继续下一个测试...")
            time.sleep(5)
    
    # 打印测试总结
    print(f"\n{'🎉' * 30} 测试完成 {'🎉' * 30}")
    
    successful_tests = sum(1 for r in results if r["success"])
    print(f"成功测试: {successful_tests}/{len(results)}")
    
    for i, result in enumerate(results, 1):
        status = "✅" if result["success"] else "❌"
        video_title = result["video"].get("title", result["video"]["url"])
        print(f"{status} 测试 {i}: {video_title}")
        
        if not result["success"]:
            error = result["result"].get("error", "未知错误")
            print(f"   错误: {error}")
        else:
            prereq_count = len(result["result"].get("prerequisite_knowledge", []))
            confidence = result["result"].get("confidence_score", 0)
            print(f"   前置知识点: {prereq_count}个, 置信度: {confidence}/100")
    
    # 保存详细结果到文件
    timestamp = int(time.time())
    result_file = f"learning_api_test_results_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n📄 详细测试结果已保存到: {result_file}")

if __name__ == "__main__":
    main()