#!/usr/bin/env python3
"""
导出数据库为JSON文件的脚本
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from db.session import SessionLocal
from sqlalchemy import text


def export_table(db, table_name: str, schema: str = "ai") -> dict:
    """导出单个表的数据"""
    
    try:
        # 检查表是否有id列
        check_id_result = db.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = '{schema}' 
            AND table_name = '{table_name}' 
            AND column_name = 'id'
        """))
        
        has_id = check_id_result.fetchone() is not None
        
        # 根据是否有id列来构建查询
        if has_id:
            result = db.execute(text(f"SELECT * FROM {schema}.{table_name} ORDER BY id"))
        else:
            result = db.execute(text(f"SELECT * FROM {schema}.{table_name}"))
        
        rows = result.fetchall()
        
        # 获取列名
        columns = result.keys()
        
        # 转换为字典列表
        data = []
        for row in rows:
            row_dict = {}
            for i, column in enumerate(columns):
                value = row[i]
                # 处理特殊类型
                if isinstance(value, datetime):
                    row_dict[column] = value.isoformat()
                else:
                    row_dict[column] = value
            data.append(row_dict)
        
        return {
            "count": len(data),
            "data": data
        }
        
    except Exception as e:
        print(f"⚠️  导出表 {table_name} 失败: {e}")
        return {
            "count": 0,
            "data": [],
            "error": str(e)
        }


def export_database():
    """导出整个数据库"""
    
    db = SessionLocal()
    try:
        # 定义要导出的表
        tables_to_export = [
            "knowledge",
            "learning_resource", 
            "knowledge_resource_association",
            "knowledge_prerequisites",
            "video_segments",
            "user_profile",
            "user_learning_path",
            "user_learning_progress"
        ]
        
        print("🚀 开始导出数据库...")
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "database_name": "ai",
            "schema": "ai",
            "tables": {}
        }
        
        # 导出每个表
        for table in tables_to_export:
            print(f"📊 导出表: {table}")
            
            # 检查表是否存在
            check_result = db.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'ai' 
                    AND table_name = '{table}'
                );
            """))
            
            table_exists = check_result.scalar()
            
            if table_exists:
                export_data["tables"][table] = export_table(db, table)
                count = export_data["tables"][table]["count"]
                print(f"  ✅ 成功导出 {count} 条记录")
            else:
                print(f"  ⏭️  表不存在，跳过")
                export_data["tables"][table] = {
                    "count": 0,
                    "data": [],
                    "note": "table_not_exists"
                }
        
        # 添加统计信息
        total_records = sum(
            table_data["count"] 
            for table_data in export_data["tables"].values()
        )
        
        export_data["summary"] = {
            "total_tables": len([t for t in export_data["tables"].values() if t["count"] > 0]),
            "total_records": total_records,
            "export_method": "python_sqlalchemy"
        }
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kairos_database_export_{timestamp}.json"
        
        # 写入文件
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 数据库导出完成!")
        print(f"📄 文件名: {filename}")
        print(f"📊 总计: {len(export_data['tables'])} 个表, {total_records} 条记录")
        
        # 显示各表统计
        print(f"\n📋 各表记录数:")
        for table, data in export_data["tables"].items():
            if data["count"] > 0:
                print(f"  {table}: {data['count']} 条")
        
        return filename
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return None
    finally:
        db.close()


def main():
    """主函数"""
    print("数据库导出工具")
    print("================")
    
    # 标准导出
    standard_file = export_database()
    
    print(f"\n🎉 导出完成!")
    if standard_file:
        print(f"📄 导出文件: {standard_file}")


if __name__ == "__main__":
    main()