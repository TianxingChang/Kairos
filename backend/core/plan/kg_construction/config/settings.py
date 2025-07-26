"""Application settings management."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# 获取项目根目录的绝对路径
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.absolute()

class Settings(BaseModel):
    """Application settings model following Google ADK patterns."""
    
    # 使用绝对路径
    data_dir: str = Field(
        default=str(ROOT_DIR / "data" / "kg"),
        description="Directory for storing data files."
    )
    default_output_encoding: str = Field(
        default="utf-8",
        description="Default encoding for file output."
    )
    
    class Config:
        """Pydantic configuration."""
        frozen = True
    
    @classmethod
    def get_default(cls) -> "Settings":
        """Get default settings instance.
        
        Returns:
            Settings instance with default values.
        """
        return cls() 