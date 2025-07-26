#!/usr/bin/env python3
"""
测试完整视频问答Agent功能是否正确调用
"""

import requests
import json

BASE_URL = "http://localhost:8000/v1"

def test_agent_call_debug():
    """测试Agent调用并显示详细信息"""
    print("=== 测试完整视频Agent调用 ===")
    
    test_data = {
        "video_id": "dQw4w9WgXcQ",
        "question": "请总结这个视频的主要内容",
        "user_id": "frontend_user", 
        "session_id": "debug_session_001"
    }
    
    try:
        print(f"发送请求到: {BASE_URL}/frontend/video-qa/ask-full-agent")
        print(f"请求数据: {json.dumps(test_data, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/frontend/video-qa/ask-full-agent",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Agent调用成功!")
            print(f"Success: {result.get('success')}")
            print(f"回答长度: {len(result.get('answer', ''))}")
            
            # 检查是否包含Agent特有的内容
            answer = result.get('answer', '')
            if answer:
                print(f"回答前200字符: {answer[:200]}...")
                # 检查是否真的调用了Agent
                if "视频" in answer or "内容" in answer or len(answer) > 50:
                    print("✅ Agent确实处理了请求并生成了有意义的回答")
                else:
                    print("⚠️ 回答可能不完整或Agent没有正确处理")
            else:
                print("❌ 没有获得有效回答")
                
            print(f"\n视频信息: {result.get('video_info', {})}")
            print(f"转录文本长度: {len(result.get('full_transcript', ''))}")
            
            # 检查是否获取到了转录文本
            full_transcript = result.get('full_transcript', '')
            if full_transcript:
                print(f"转录文本前100字符: {full_transcript[:100]}...")
                print("✅ 成功获取到完整转录文本")
            else:
                print("❌ 没有获取到转录文本，可能是数据库问题")
            
        else:
            print("❌ Agent调用失败:")
            try:
                error_data = response.json()
                print(f"错误详情: {json.dumps(error_data, indent=2)}")
            except:
                print(f"错误信息: {response.text}")
                
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()

def test_regular_vs_agent():
    """对比常规模式和Agent模式的差异"""
    print("\n=== 对比常规模式 vs Agent模式 ===")
    
    question = "这个视频讲了什么？"
    video_id = "dQw4w9WgXcQ"
    
    print(f"测试问题: {question}")
    print(f"视频ID: {video_id}")
    
    # 测试常规模式
    print("\n1. 常规模式 (/ask-full):")
    try:
        response = requests.post(
            f"{BASE_URL}/frontend/video-qa/ask-full",
            json={
                "video_id": video_id,
                "question": question,
                "user_id": "test_user"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            print(f"   状态: ✅ 成功")
            print(f"   回答长度: {len(answer)}")
            print(f"   回答预览: {answer[:100]}...")
        else:
            print(f"   状态: ❌ 失败 ({response.status_code})")
    except Exception as e:
        print(f"   状态: ❌ 异常 ({e})")
    
    # 测试Agent模式
    print("\n2. Agent模式 (/ask-full-agent):")
    try:
        response = requests.post(
            f"{BASE_URL}/frontend/video-qa/ask-full-agent",
            json={
                "video_id": video_id,
                "question": question,
                "user_id": "test_user",
                "session_id": "comparison_test"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            print(f"   状态: ✅ 成功")
            print(f"   回答长度: {len(answer)}")
            print(f"   回答预览: {answer[:100]}...")
        else:
            print(f"   状态: ❌ 失败 ({response.status_code})")
    except Exception as e:
        print(f"   状态: ❌ 异常 ({e})")

if __name__ == "__main__":
    print("开始调试完整视频Agent调用...")
    print("=" * 60)
    
    test_agent_call_debug()
    test_regular_vs_agent()
    
    print("\n" + "=" * 60)
    print("调试完成!")
    print("\n说明:")
    print("- 如果Agent调用成功但回答为空，可能是数据库中没有视频转录数据")
    print("- 如果Agent调用失败，检查后端服务是否正常运行")
    print("- 前端现在会默认对所有完整视频问答使用Agent模式")