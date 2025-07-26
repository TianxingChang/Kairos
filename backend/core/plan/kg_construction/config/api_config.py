"""API configuration management."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class ApiConfig(BaseModel):
    """API configuration model following Google ADK patterns."""
    
    google_api_key: Optional[str] = Field(
        default=None,
        description="Google API key for Gemini."
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for Kimi."
    )
    model_name: str = Field(
        default="gemini-2.5-pro",  # 更新为正确的模型名称
        description="Model name to use for API calls."
    )
    use_vertex_ai: bool = Field(
        default=False,
        description="Whether to use Vertex AI instead of API Studio."
    )
    
    class Config:
        """Pydantic configuration."""
        frozen = True
    
    @classmethod
    def from_environment(cls) -> "ApiConfig":
        """Create configuration from environment variables.
        
        Returns:
            ApiConfig instance.
        """
        return cls(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            openai_api_key=os.getenv("MOONSHOT_API_KEY") or os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("MODEL_NAME", "gemini-2.5-pro"),
            use_vertex_ai=os.getenv("USE_VERTEX_AI", "false").lower() == "true"
        )
    
    def setup_environment(self) -> None:
        """Setup environment variables for API access."""
        if self.google_api_key:
            os.environ["GOOGLE_API_KEY"] = self.google_api_key
            # 同时设置 GOOGLE_API_KEY 和 GOOGLE_GENERATIVE_AI_API_KEY
            os.environ["GOOGLE_GENERATIVE_AI_API_KEY"] = self.google_api_key
        
        if self.openai_api_key:
            # 同时设置两个环境变量，确保OpenAI客户端可以找到API key
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
            os.environ["MOONSHOT_API_KEY"] = self.openai_api_key
        
        if self.use_vertex_ai:
            os.environ["USE_VERTEX_AI"] = "true"
    
    @property
    def api_key(self) -> Optional[str]:
        """Get the appropriate API key based on the model name."""
        if self.model_name.startswith("gemini-"):
            return self.google_api_key
        elif self.model_name.startswith("kimi-"):
            return self.openai_api_key
        return None 