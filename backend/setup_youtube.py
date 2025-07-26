#!/usr/bin/env python3
"""
YouTube功能设置脚本
运行数据库迁移并安装依赖
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🔄 {description}")
    print(f"运行命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} 成功")
        if result.stdout:
            print(f"输出: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败")
        print(f"错误: {e.stderr}")
        return False

def main():
    print("🚀 开始设置YouTube功能...")
    
    # 检查当前目录
    if not os.path.exists("pyproject.toml"):
        print("❌ 请在backend目录下运行此脚本")
        sys.exit(1)
    
    # 1. 安装依赖
    success = run_command(
        "pip install youtube-transcript-api yt-dlp", 
        "安装youtube-transcript-api和yt-dlp依赖"
    )
    if not success:
        print("💡 尝试使用uv安装...")
        run_command("uv add youtube-transcript-api", "使用uv安装youtube-transcript-api")
        run_command("uv add yt-dlp", "使用uv安装yt-dlp")
    
    # 2. 运行数据库迁移
    print("\n🔄 运行数据库迁移...")
    try:
        from db.migrations import create_tables, check_tables_exist
        
        # 检查表状态
        tables_status = check_tables_exist()
        if tables_status:
            print("📊 当前表状态:")
            for table, exists in tables_status.items():
                status = "✅ 存在" if exists else "❌ 不存在"
                print(f"  - {table}: {status}")
            
            # 创建缺失的表
            if not all(tables_status.values()):
                print("\n🔄 创建缺失的表...")
                success = create_tables()
                if success:
                    print("✅ 数据库迁移完成!")
                else:
                    print("❌ 数据库迁移失败!")
                    sys.exit(1)
            else:
                print("✅ 所有表都已存在")
        else:
            print("❌ 无法检查表状态")
            sys.exit(1)
            
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保在正确的环境中运行，并且所有依赖都已安装")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        sys.exit(1)
    
    print("\n🎉 YouTube功能设置完成!")
    print("\n📋 功能说明:")
    print("  - 后端API端点: /v1/youtube/")
    print("  - 快速处理: POST /v1/youtube/quick-process")
    print("  - 获取转录: GET /v1/youtube/transcript/{video_id}")
    print("  - 状态检查: GET /v1/youtube/status/{video_id}")
    print("\n💡 使用方法:")
    print("  1. 启动后端服务器")
    print("  2. 前端上传YouTube链接时会自动调用API处理")
    print("  3. 转录文本会在后台异步下载并存储到数据库")

if __name__ == "__main__":
    main()