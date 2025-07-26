"""Learning API configuration settings.

This module provides configuration management for the Learning API,
replacing hardcoded magic numbers with configurable parameters.

Example usage:
    from config.learning_config import learning_config
    
    # Use configuration values instead of hardcoded numbers
    text_snippet = analysis_text[:learning_config.analysis_text_max_length]
    knowledge_points = extracted_points[:learning_config.max_main_knowledge_points]
"""

from pydantic import BaseModel, Field
from typing import Optional


class LearningConfig(BaseModel):
    """Configuration settings for the learning API.
    
    This class centralizes all configurable parameters for the learning API
    to improve maintainability and allow easy tuning without code changes.
    
    Example:
        config = LearningConfig.get_default()
        max_text = config.analysis_text_max_length  # 2000
        
        # For custom configuration:
        custom_config = LearningConfig(
            analysis_text_max_length=3000,
            max_main_knowledge_points=7
        )
    """
    
    # 文本分析配置
    analysis_text_max_length: int = Field(
        default=2000,
        description="Maximum length of text to analyze for knowledge extraction"
    )
    
    # 知识点提取配置
    max_main_knowledge_points: int = Field(
        default=5,
        description="Maximum number of main knowledge points to extract from content"
    )
    
    # 资源匹配配置
    max_best_resources_per_knowledge: int = Field(
        default=3,
        description="Maximum number of best learning resources to return per knowledge point"
    )
    
    # 搜索配置
    min_keyword_length: int = Field(
        default=3,
        description="Minimum length of keywords for fuzzy matching (adjusted for Chinese terms)"
    )
    
    # 置信度计算配置
    base_confidence_score: int = Field(
        default=50,
        description="Base confidence score for analysis results"
    )
    
    match_rate_weight: int = Field(
        default=30,
        description="Weight for match rate in confidence calculation"
    )
    
    text_length_bonus: int = Field(
        default=10,
        description="Bonus points for longer analysis text"
    )
    
    knowledge_count_bonus: int = Field(
        default=5,
        description="Bonus points per matched knowledge point (max 20)"
    )
    
    max_knowledge_count_bonus: int = Field(
        default=20,
        description="Maximum bonus from knowledge point count"
    )
    
    # 文本长度阈值配置
    long_text_threshold: int = Field(
        default=1000,
        description="Threshold for considering text as 'long' for confidence bonus"
    )
    
    class Config:
        """Pydantic configuration."""
        frozen = True
    
    @classmethod
    def get_default(cls) -> "LearningConfig":
        """Get default configuration instance.
        
        Returns:
            LearningConfig instance with default values.
        """
        return cls()


# 全局配置实例
learning_config = LearningConfig.get_default()


# Configuration Usage Examples and Best Practices
"""
配置使用示例和最佳实践：

1. 基本使用：
   ```python
   from config.learning_config import learning_config
   
   # 在函数中使用配置值
   def process_text(text: str) -> str:
       return text[:learning_config.analysis_text_max_length]
   ```

2. 动态配置调整：
   ```python
   # 对于特殊需求的临时配置调整
   high_precision_config = LearningConfig(
       max_main_knowledge_points=10,  # 提取更多知识点
       max_best_resources_per_knowledge=5,  # 返回更多资源
       base_confidence_score=60  # 提高基础置信度
   )
   ```

3. 环境相关配置：
   ```python
   # 开发环境可能需要更详细的输出
   if DEBUG:
       config = LearningConfig(
           max_main_knowledge_points=8,
           analysis_text_max_length=3000
       )
   else:
       config = learning_config  # 使用默认生产配置
   ```

4. 配置验证：
   所有配置值都通过Pydantic进行类型检查和验证，
   确保配置的正确性和一致性。

5. 性能调优指南：
   - analysis_text_max_length: 增大可提高分析准确性，但会增加LLM处理时间
   - max_main_knowledge_points: 增大可获得更全面的分析，但可能包含噪音
   - max_best_resources_per_knowledge: 影响响应大小和用户选择复杂度
   - confidence_score相关参数: 调整可改变系统的"保守"或"积极"程度
"""