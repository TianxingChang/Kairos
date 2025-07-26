"""Database initialization script."""

import os
import sys
import logging
from pathlib import Path

# 添加backend目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    
    # 加载环境变量（从项目根目录）
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"❌ Environment file not found: {env_path}")
        
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables")

from sqlalchemy import create_engine
from db.models import Base
from db.url import get_db_url

logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库，创建所有表"""
    try:
        db_url = get_db_url()
        print(f"连接数据库: {db_url}")
        engine = create_engine(db_url)
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("数据库表创建成功")
        logger.info("数据库表创建成功")
        
        return True
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        logger.error(f"数据库初始化失败: {e}")
        return False


if __name__ == "__main__":
    init_database() 