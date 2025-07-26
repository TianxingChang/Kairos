#!/usr/bin/env python3
"""
测试视频问答功能的脚本
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/v1"

def test_video_qa_endpoint():
    """测试视频问答接口"""
    print("=== 测试视频问答功能 ===")
    
    # 测试数据
    test_data = {
        "video_id": "dQw4w9WgXcQ",  # 示例YouTube视频ID
        "timestamp": 30.0,  # 30秒
        "question": "这个时间点在说什么？",
        "user_id": "test_user",
        "context_before": 20,
        "context_after": 5
    }
    
    try:
        # 发送请求到前端API端点
        response = requests.post(
            f"{BASE_URL}/frontend/video-qa/ask",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 请求成功!")
            print(f"回答: {result.get('answer', 'N/A')}")
            print(f"视频信息: {result.get('video_info', {})}")
            print(f"时间戳信息: {result.get('timestamp_info', {})}")
            print(f"上下文长度: {len(result.get('context_transcript', ''))}")
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

def test_youtube_upload_endpoint():
    """测试YouTube上传接口"""
    print("\n=== 测试YouTube上传功能 ===")
    
    test_data = {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "user_id": "test_user"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/frontend/youtube/upload",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 上传请求成功!")
            print(f"视频ID: {result.get('video_id', 'N/A')}")
            print(f"状态: {result.get('status', 'N/A')}")
            print(f"消息: {result.get('message', 'N/A')}")
        else:
            print("❌ 上传失败:")
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                print(f"错误信息: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

def test_video_status_endpoint():
    """测试视频状态检查接口"""
    print("\n=== 测试视频状态检查功能 ===")
    
    video_id = "dQw4w9WgXcQ"
    
    try:
        response = requests.get(
            f"{BASE_URL}/frontend/video-qa/video-status/{video_id}",
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 状态检查成功!")
            print(f"视频ID: {result.get('video_id', 'N/A')}")
            print(f"有视频信息: {result.get('has_video_info', False)}")
            print(f"有转录文本: {result.get('has_transcript', False)}")
            print(f"准备问答: {result.get('ready_for_qa', False)}")
        else:
            print("❌ 状态检查失败:")
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                print(f"错误信息: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

def test_health_endpoint():
    """测试健康检查接口"""
    print("\n=== 测试健康检查功能 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 服务器健康!")
            print(f"状态: {result}")
        else:
            print("❌ 服务器不健康")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 连接失败: {e}")
        print("请确保后端服务正在运行在 http://localhost:8000")

if __name__ == "__main__":
    print("开始测试视频问答API功能...")
    print("=" * 50)
    
    # 首先测试服务器是否运行
    test_health_endpoint()
    
    # 测试各个功能
    test_video_status_endpoint()
    test_youtube_upload_endpoint()
    test_video_qa_endpoint()
    
    print("\n" + "=" * 50)
    print("测试完成!")
    print("\n使用说明:")
    print("1. 确保后端服务运行: cd backend && python -m uvicorn api.main:app --reload")
    print("2. 确保前端服务运行: cd frontend && npm run dev")
    print("3. 访问测试页面: http://localhost:3000/video-qa-test")