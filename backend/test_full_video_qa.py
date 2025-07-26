#!/usr/bin/env python3
"""
测试完整视频问答Agent功能的脚本
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/v1"

def test_full_video_qa_direct():
    """测试完整视频问答（直接调用）"""
    print("=== 测试完整视频问答（直接调用）===")
    
    test_data = {
        "video_id": "dQw4w9WgXcQ",
        "question": "这个视频的主要内容是什么？包含了哪些主要部分？",
        "user_id": "test_user"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/frontend/video-qa/ask-full",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=60  # 增加超时时间，因为完整视频分析可能需要更长时间
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 完整视频问答成功!")
            print(f"回答长度: {len(result.get('answer', ''))}")
            print(f"回答预览: {result.get('answer', '')[:200]}...")
            print(f"视频信息: {result.get('video_info', {})}")
            print(f"转录统计: {result.get('transcript_stats', {})}")
            print(f"完整转录长度: {len(result.get('full_transcript', ''))}")
        else:
            print("❌ 请求失败:")
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                print(f"错误信息: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

def test_full_video_qa_agent():
    """测试完整视频问答（使用Agent）"""
    print("\n=== 测试完整视频问答（使用Agent）===")
    
    test_data = {
        "video_id": "dQw4w9WgXcQ",
        "question": "请分析这个视频的整体结构和主要观点，并总结其关键信息。",
        "user_id": "test_user",
        "session_id": "test_session_001"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/frontend/video-qa/ask-full-agent",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Agent完整视频问答成功!")
            print(f"回答长度: {len(result.get('answer', ''))}")
            print(f"回答预览: {result.get('answer', '')[:200]}...")
            print(f"视频信息: {result.get('video_info', {})}")
            print(f"转录统计: {result.get('transcript_stats', {})}")
        else:
            print("❌ Agent请求失败:")
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                print(f"错误信息: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

def test_comparison():
    """比较两种模式的性能和质量"""
    print("\n=== 对比测试 ===")
    
    question = "这个视频的主题是什么？"
    
    print("测试同一问题在两种模式下的表现差异:")
    print(f"问题: {question}")
    
    # 测试直接调用
    print("\n1. 直接调用模式:")
    test_data = {
        "video_id": "dQw4w9WgXcQ",
        "question": question,
        "user_id": "test_user"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/frontend/video-qa/ask-full",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 直接调用回答: {result.get('answer', '')[:150]}...")
        else:
            print("❌ 直接调用失败")
    except Exception as e:
        print(f"❌ 直接调用错误: {e}")
    
    # 测试Agent模式
    print("\n2. Agent模式:")
    test_data["session_id"] = "comparison_test"
    
    try:
        response = requests.post(
            f"{BASE_URL}/frontend/video-qa/ask-full-agent",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Agent回答: {result.get('answer', '')[:150]}...")
        else:
            print("❌ Agent调用失败")
    except Exception as e:
        print(f"❌ Agent调用错误: {e}")

if __name__ == "__main__":
    print("开始测试完整视频问答Agent功能...")
    print("=" * 60)
    
    # 测试完整视频问答功能
    test_full_video_qa_direct()
    test_full_video_qa_agent()
    test_comparison()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("\n新增功能说明:")
    print("1. /v1/frontend/video-qa/ask-full - 完整视频问答（直接调用）")
    print("2. /v1/frontend/video-qa/ask-full-agent - 完整视频问答（Agent模式）")
    print("3. Agent模式支持会话记忆和更智能的对话交互")
    print("4. 前端界面已更新，包含三种模式选择")