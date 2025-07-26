#!/usr/bin/env python3
"""
视频切割API - 完整使用示例
=========================

这个文件展示了如何使用视频切割API的完整流程：
1. 提交视频分析请求
2. 监控任务进度
3. 查询数据库结果
4. 导出前端可用的JSON格式

使用方法:
    python video_analysis_example.py

作者: Kairos Team
日期: 2025-07-26
"""

import requests
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List
import sys
from datetime import datetime


class VideoAnalysisClient:
    """视频分析API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", db_config: Optional[Dict] = None):
        """
        初始化客户端
        
        Args:
            base_url: API基础URL
            db_config: 数据库配置字典
        """
        self.base_url = base_url.rstrip('/')
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'user': 'ai',
            'password': 'ai',
            'database': 'ai'
        }
    
    def submit_video_analysis(self, video_url: str, knowledge_context_id: int = 1, 
                            resource_title: Optional[str] = None,
                            preferred_subtitle_language: str = "en") -> Optional[Dict]:
        """
        提交视频分析请求
        
        Args:
            video_url: YouTube视频URL
            knowledge_context_id: 知识点上下文ID（用于筛选相关知识点）
            resource_title: 可选的资源标题
            preferred_subtitle_language: 首选字幕语言
        
        Returns:
            dict: 包含job_id和resource_id的响应，失败时返回None
        """
        url = f"{self.base_url}/v1/videos/analyze-segments-from-video-link"
        
        payload = {
            "video_url": video_url,
            "knowledge_context_id": knowledge_context_id,
            "preferred_subtitle_language": preferred_subtitle_language
        }
        
        if resource_title:
            payload["resource_title"] = resource_title
        
        try:
            print(f"🚀 提交视频分析请求...")
            print(f"🎬 视频URL: {video_url}")
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 202:
                result = response.json()
                print(f"✅ 任务创建成功!")
                print(f"🆔 任务ID: {result['job_id']}")
                print(f"🗂️ 资源ID: {result['resource_id']}")
                print(f"📊 状态查询URL: {result['status_url']}")
                return result
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return None
                
        except requests.RequestException as e:
            print(f"❌ 网络请求错误: {e}")
            return None
    
    def check_job_status(self, job_id: str) -> Optional[Dict]:
        """
        检查任务状态
        
        Args:
            job_id: 任务ID
        
        Returns:
            dict: 任务状态信息，失败时返回None
        """
        url = f"{self.base_url}/v1/videos/analyze-segments/status/{job_id}"
        
        try:
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                status = response.json()
                return status
            elif response.status_code == 404:
                print(f"❌ 任务不存在或已过期: {job_id}")
                return None
            else:
                print(f"❌ 状态查询失败: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"❌ 网络请求错误: {e}")
            return None
    
    def wait_for_completion(self, job_id: str, max_attempts: int = 30, 
                          check_interval: int = 10) -> Optional[Dict]:
        """
        等待任务完成
        
        Args:
            job_id: 任务ID
            max_attempts: 最大检查次数
            check_interval: 检查间隔（秒）
        
        Returns:
            dict: 最终状态，失败时返回None
        """
        print(f"\n📋 监控任务进度 (最多 {max_attempts} 次检查)")
        print("=" * 50)
        
        for attempt in range(max_attempts):
            print(f"\n🔍 检查 {attempt + 1}/{max_attempts}")
            status = self.check_job_status(job_id)
            
            if not status:
                break
            
            print(f"  📊 状态: {status['status']}")
            print(f"  📈 进度: {status['progress_percentage']}%")
            print(f"  💬 消息: {status['message']}")
            print(f"  🎯 已创建分段: {status['segments_created']}")
            
            if status['status'] == 'completed':
                print(f"\n🎉 分析完成! 创建了 {status['segments_created']} 个分段")
                return status
            elif status['status'] == 'failed':
                error_msg = status.get('error_message', '未知错误')
                print(f"\n❌ 分析失败: {error_msg}")
                return status
            
            print("  ⏳ 继续等待...")
            time.sleep(check_interval)
        
        print("\n⏰ 等待超时")
        return None
    
    def query_video_segments(self, resource_id: int) -> Optional[Dict]:
        """
        查询视频分段结果
        
        Args:
            resource_id: 资源ID
        
        Returns:
            dict: 包含resource和segments的数据，失败时返回None
        """
        try:
            # 连接数据库
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 查询资源信息
            cursor.execute("""
                SELECT id, title, resource_url, duration_minutes, description, created_at
                FROM learning_resource 
                WHERE id = %s
            """, (resource_id,))
            
            resource = cursor.fetchone()
            
            if not resource:
                print(f"❌ 未找到资源ID: {resource_id}")
                return None
            
            print(f"\n📺 视频资源信息:")
            print(f"   🆔 ID: {resource['id']}")
            print(f"   📖 标题: {resource['title']}")
            print(f"   🔗 URL: {resource['resource_url']}")
            print(f"   ⏱️  时长: {resource['duration_minutes']}分钟" if resource['duration_minutes'] else "   ⏱️  时长: 未知")
            print(f"   📅 创建时间: {resource['created_at']}")
            print()
            
            # 查询分段信息
            cursor.execute("""
                SELECT 
                    vs.id,
                    vs.start_time,
                    vs.end_time,
                    vs.start_seconds,
                    vs.end_seconds,
                    vs.segment_title,
                    vs.segment_description,
                    vs.importance_level,
                    vs.created_at,
                    k.title as knowledge_title,
                    k.description as knowledge_description,
                    k.domain as knowledge_domain,
                    k.knowledge_level
                FROM video_segment vs
                JOIN knowledge k ON vs.knowledge_id = k.id
                WHERE vs.resource_id = %s
                ORDER BY vs.start_seconds
            """, (resource_id,))
            
            segments = cursor.fetchall()
            
            print(f"📊 找到 {len(segments)} 个分段:")
            print("=" * 100)
            
            result_data = []
            total_duration = 0
            
            for i, segment in enumerate(segments, 1):
                duration = segment['end_seconds'] - segment['start_seconds']
                total_duration += duration
                
                segment_data = {
                    'segment_id': segment['id'],
                    'time_range': f"{segment['start_time']} - {segment['end_time']}",
                    'start_seconds': segment['start_seconds'],
                    'end_seconds': segment['end_seconds'],
                    'duration': duration,
                    'knowledge_title': segment['knowledge_title'],
                    'knowledge_domain': segment['knowledge_domain'],
                    'knowledge_level': segment['knowledge_level'],
                    'description': segment['segment_description'],
                    'importance_level': segment['importance_level'],
                    'created_at': segment['created_at'].isoformat() if segment['created_at'] else None
                }
                result_data.append(segment_data)
                
                print(f"{i}. [{segment['start_time']} - {segment['end_time']}] ({duration}秒)")
                print(f"   📖 知识点: {segment['knowledge_title']}")
                print(f"   🏷️  领域: {segment['knowledge_domain']} ({segment['knowledge_level']})")
                print(f"   📝 描述: {segment['segment_description']}")
                print(f"   ⭐ 重要级别: {segment['importance_level']}/5")
                print(f"   📅 创建时间: {segment['created_at']}")
                print()
            
            print(f"⏱️  总分段时长: {total_duration}秒 ({total_duration//60}分{total_duration%60}秒)")
            
            cursor.close()
            conn.close()
            
            return {
                'resource': dict(resource),
                'segments': result_data,
                'summary': {
                    'total_segments': len(segments),
                    'total_duration_seconds': total_duration,
                    'average_segment_duration': total_duration / len(segments) if segments else 0
                }
            }
            
        except Exception as e:
            print(f"❌ 数据库查询错误: {e}")
            return None
    
    def export_segments_for_frontend(self, resource_id: int, output_file: Optional[str] = None) -> Optional[Dict]:
        """
        导出为前端友好的JSON格式
        
        Args:
            resource_id: 资源ID
            output_file: 输出文件路径，None时自动生成
        
        Returns:
            dict: 前端可直接使用的JSON数据，失败时返回None
        """
        segments_data = self.query_video_segments(resource_id)
        
        if not segments_data:
            return None
        
        # 格式化为前端友好的结构
        frontend_data = {
            "meta": {
                "exported_at": datetime.now().isoformat(),
                "api_version": "v1",
                "total_segments": len(segments_data['segments'])
            },
            "video_info": {
                "resource_id": segments_data['resource']['id'],
                "title": segments_data['resource']['title'],
                "url": segments_data['resource']['resource_url'],
                "duration_minutes": segments_data['resource']['duration_minutes'],
                "created_at": segments_data['resource']['created_at'].isoformat() if segments_data['resource']['created_at'] else None
            },
            "summary": segments_data['summary'],
            "segments": []
        }
        
        for segment in segments_data['segments']:
            frontend_segment = {
                "id": segment['segment_id'],
                "title": segment['knowledge_title'],
                "description": segment['description'],
                "timeRange": {
                    "start": segment['start_seconds'],
                    "end": segment['end_seconds'],
                    "startTime": segment['time_range'].split(' - ')[0],
                    "endTime": segment['time_range'].split(' - ')[1],
                    "duration": segment['duration']
                },
                "knowledge": {
                    "title": segment['knowledge_title'],
                    "domain": segment['knowledge_domain'],
                    "level": segment['knowledge_level'],
                    "importance": segment['importance_level']
                },
                "metadata": {
                    "created_at": segment['created_at']
                }
            }
            frontend_data["segments"].append(frontend_segment)
        
        # 生成输出文件名
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"video_segments_{resource_id}_{timestamp}.json"
        
        # 保存到文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(frontend_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n📄 数据已导出到: {output_file}")
            print(f"📊 包含 {len(frontend_data['segments'])} 个分段")
            
            return frontend_data
            
        except Exception as e:
            print(f"❌ 文件写入错误: {e}")
            return None


def main():
    """主函数 - 完整的使用示例"""
    
    print("🎯 视频切割API - 完整使用示例")
    print("=" * 50)
    print(f"🚀 开始时间: {datetime.now().strftime('%H:%M:%S')}")
    
    # 初始化客户端
    client = VideoAnalysisClient()
    
    # 示例视频URL（可以修改为其他YouTube视频）
    video_url = "https://youtu.be/OAKAZhFmYoI"
    
    # 1. 提交视频分析请求
    print(f"\n📋 1. 提交视频分析请求")
    job_result = client.submit_video_analysis(
        video_url=video_url,
        knowledge_context_id=1,
        resource_title="PPO算法讲解视频",
        preferred_subtitle_language="en"
    )
    
    if not job_result:
        print("❌ 任务提交失败，程序退出")
        sys.exit(1)
    
    # 2. 等待任务完成
    print(f"\n📋 2. 等待任务完成")
    final_status = client.wait_for_completion(
        job_id=job_result['job_id'],
        max_attempts=30,
        check_interval=10
    )
    
    if not final_status or final_status['status'] != 'completed':
        print("❌ 任务未能成功完成，程序退出")
        sys.exit(1)
    
    # 3. 查询数据库结果
    print(f"\n📋 3. 查询数据库结果")
    segments_data = client.query_video_segments(job_result['resource_id'])
    
    if not segments_data:
        print("❌ 无法查询到分段数据")
        sys.exit(1)
    
    # 4. 导出前端JSON
    print(f"\n📋 4. 导出前端JSON格式")
    frontend_json = client.export_segments_for_frontend(job_result['resource_id'])
    
    if frontend_json:
        # 显示JSON预览
        print(f"\n📋 前端JSON格式预览 (前500字符):")
        print("-" * 50)
        json_str = json.dumps(frontend_json, ensure_ascii=False, indent=2)
        print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
    
    # 5. 显示统计信息
    print(f"\n📊 分析统计:")
    print(f"   🎬 视频资源ID: {job_result['resource_id']}")
    print(f"   📝 总分段数: {segments_data['summary']['total_segments']}")
    print(f"   ⏱️  总时长: {segments_data['summary']['total_duration_seconds']}秒")
    print(f"   📊 平均分段时长: {segments_data['summary']['average_segment_duration']:.1f}秒")
    
    print(f"\n🏁 完成时间: {datetime.now().strftime('%H:%M:%S')}")
    print("✅ 所有步骤执行完毕!")


def demo_query_existing_resource():
    """演示查询已存在资源的分段数据"""
    
    print("\n🔍 演示: 查询已存在资源的分段数据")
    print("=" * 50)
    
    client = VideoAnalysisClient()
    
    # 假设你知道一个已存在的resource_id
    resource_id = 298  # 修改为实际的resource_id
    
    print(f"📋 查询资源ID: {resource_id}")
    segments_data = client.query_video_segments(resource_id)
    
    if segments_data:
        # 导出JSON
        frontend_json = client.export_segments_for_frontend(
            resource_id, 
            f"existing_resource_{resource_id}.json"
        )
        print("✅ 查询完成!")
    else:
        print("❌ 资源不存在或查询失败")


if __name__ == "__main__":
    # 选择运行模式
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # 演示模式：查询已存在的资源
        demo_query_existing_resource()
    else:
        # 完整流程模式
        main()