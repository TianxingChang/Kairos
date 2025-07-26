"""
数据库迁移脚本
创建YouTube相关表
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from db.url import get_db_url
from db.models import Base


def create_tables():
    """创建所有数据库表"""
    try:
        # 创建数据库引擎
        db_url = get_db_url()
        engine = create_engine(db_url, pool_pre_ping=True)
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        print("✅ 数据库表创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 创建数据库表失败: {e}")
        return False


def drop_tables():
    """删除所有数据库表（慎用）"""
    try:
        db_url = get_db_url()
        engine = create_engine(db_url, pool_pre_ping=True)
        
        Base.metadata.drop_all(bind=engine)
        
        print("✅ 数据库表删除成功")
        return True
        
    except Exception as e:
        print(f"❌ 删除数据库表失败: {e}")
        return False


def check_tables_exist():
    """检查表是否存在"""
    try:
        db_url = get_db_url()
        engine = create_engine(db_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # 检查youtube_videos表
            result1 = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = current_schema() 
                    AND table_name = 'youtube_videos'
                );
            """))
            videos_table_exists = result1.scalar()
            
            # 检查youtube_transcripts表
            result2 = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = current_schema() 
                    AND table_name = 'youtube_transcripts'
                );
            """))
            transcripts_table_exists = result2.scalar()
            
            # 检查youtube_videos表是否有新的文件存储字段
            result3 = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = current_schema() 
                    AND table_name = 'youtube_videos'
                    AND column_name = 'transcript_file_path'
                );
            """))
            has_file_columns = result3.scalar()
            
            return {
                'youtube_videos': videos_table_exists,
                'youtube_transcripts': transcripts_table_exists,
                'has_file_storage_columns': has_file_columns
            }
            
    except Exception as e:
        print(f"❌ 检查表失败: {e}")
        return None


if __name__ == "__main__":
    print("🔄 开始数据库迁移...")
    
    # 检查表是否已存在
    tables_status = check_tables_exist()
    if tables_status:
        print(f"📊 表状态检查:")
        print(f"  - youtube_videos: {'✅ 存在' if tables_status['youtube_videos'] else '❌ 不存在'}")
        print(f"  - youtube_transcripts: {'✅ 存在' if tables_status['youtube_transcripts'] else '❌ 不存在'}")
        print(f"  - 文件存储字段: {'✅ 存在' if tables_status.get('has_file_storage_columns', False) else '❌ 不存在'}")
        
        # 检查是否需要迁移
        basic_tables_exist = tables_status['youtube_videos'] and tables_status['youtube_transcripts']
        has_file_columns = tables_status.get('has_file_storage_columns', False)
        
        if not basic_tables_exist or not has_file_columns:
            print("\n🔄 执行数据库迁移...")
            success = create_tables()
            if success:
                print("🎉 数据库迁移完成!")
                print("\n💡 新功能:")
                print("  - 转录文本现在以JSON文件形式存储")
                print("  - 数据库只保存文件路径，减少存储负担")
                print("  - 支持文件管理API和清理功能")
            else:
                print("💥 数据库迁移失败!")
        else:
            print("\n✅ 数据库已是最新版本")
    else:
        print("💥 无法检查表状态，尝试创建表...")
        create_tables()