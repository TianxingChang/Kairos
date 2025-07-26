"""Main application module with dependency injection and orchestration."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
import os
import argparse
from dotenv import load_dotenv

# 获取项目根目录并加载环境变量
root_dir = Path(__file__).parent.parent.parent.parent.parent
env_path = root_dir / '.env'
load_dotenv(dotenv_path=env_path)



from core.plan.kg_construction import (
    GeminiClient,
    KimiClient,
    ApiConfig,
    Settings,
    KnowledgeGraph,
    KnowledgeGraphService
)
from core.plan.kg_construction.utils.logging_config import setup_logging
from core.plan.kg_construction.config.settings import Settings

logger = logging.getLogger(__name__)

# 支持的模型类型
ModelType = Literal["gemini-2.5-pro", "kimi-k2-0711-preview", "o3-mini"]


class  Application:
    """Main application class following Google ADK dependency injection patterns.
    
    This class orchestrates the entire application lifecycle and provides
    a clean interface for knowledge graph operations.
    """
    
    def __init__(
        self,
        api_config: Optional[ApiConfig] = None,
        settings: Optional[Settings] = None,
        model_type: ModelType = "o3-mini"  # 默认使用 Azure OpenAI
    ):
        """Initialize the   application.
        
        Args:
            api_config: API configuration (creates default if not provided).
            settings: Application settings (creates default if not provided).
            model_type: 使用的模型类型，支持 "gemini-2.5-pro"、"kimi-k2-0711-preview" 或 "o3-mini"
        """
        self._api_config = api_config or ApiConfig.from_environment()
        self._settings = settings or Settings.get_default()
        self._model_type = model_type
        
        # Setup logging
        setup_logging(settings=self._settings)
        
        # 根据model_type选择不同的API client
        if model_type == "gemini-2.5-pro":
            api_config = ApiConfig(model_name="gemini-2.5-pro")
            self._api_client = GeminiClient(api_config)
        elif model_type == "kimi-k2-0711-preview":
            api_config = ApiConfig(model_name="kimi-k2-0711-preview")
            self._api_client = KimiClient(api_config)
        else:  # o3-mini
            from backend.agents.models import AzureOpenAIModel
            self._api_client = AzureOpenAIModel()
            
        self._knowledge_graph_service = KnowledgeGraphService(
            api_client=self._api_client,
            settings=self._settings
        )
        
        logger.info(f" Application initialized with model: {model_type}")
    
    async def create_knowledge_graph(
        self,
        topic: str,
        save_to_file: bool = True,
        output_filename: Optional[str] = None,
        one_shot_example: Optional[str] = None
    ) -> KnowledgeGraph:
        """Create a knowledge graph for the specified topic.
        
        Args:
            topic: The topic to create a knowledge graph for.
            save_to_file: Whether to save the graph to a file.
            output_filename: Custom filename for output.
            one_shot_example: Path to a JSON file to use as format example.
            
        Returns:
            The generated knowledge graph.
        """
        logger.info(f"Creating knowledge graph for topic: {topic}")
        
        # 如果没有指定示例文件，默认使用reinforcement_learning_hardcoded.json
        if one_shot_example is None:
            # 使用项目根目录的 data 文件夹
            root_dir = Path(__file__).parent.parent
            one_shot_example = str(root_dir / "data" / "reinforcement_learning_hardcoded.json")
        
        # 生成带时间戳的文件名，并保存到 settings 定义的 data/kg 目录
        if save_to_file:
            # 使用settings中定义的data_dir
            settings = Settings.get_default()
            kg_dir = Path(settings.data_dir)
            kg_dir.mkdir(parents=True, exist_ok=True)
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic = topic.replace(' ', '_')
                output_filename = f"{safe_topic}_{timestamp}.json"
            output_filename = str(kg_dir / output_filename)
        
        return await self._knowledge_graph_service.create_knowledge_graph(
            topic=topic,
            save_to_file=save_to_file,
            output_filename=output_filename,
            one_shot_example=one_shot_example
        )
    
    async def load_knowledge_graph(self, filename: str) -> KnowledgeGraph:
        """Load a knowledge graph from a file.
        
        Args:
            filename: The filename to load from.
            
        Returns:
            The loaded knowledge graph.
        """
        return await self._knowledge_graph_service.load_knowledge_graph(filename)
    
    async def list_saved_graphs(self, directory: Optional[str] = None) -> list[str]:
        """List all saved knowledge graph files.
        
        Args:
            directory: Directory to search in (optional).
            
        Returns:
            List of graph filenames.
        """
        return await self._knowledge_graph_service.list_graph_files(directory)
    
    @property
    def settings(self) -> Settings:
        """Get the application settings."""
        return self._settings
    
    @property
    def api_config(self) -> ApiConfig:
        """Get the API configuration."""
        return self._api_config


def create_knowledge_graph_application(
    api_config: Optional[ApiConfig] = None,
    settings: Optional[Settings] = None,
    model_type: ModelType = "o3-mini"  # 默认使用 Azure OpenAI
) ->  Application:
    """Factory function to create a configured   application.
    
    Args:
        api_config: API configuration (optional).
        settings: Application settings (optional).
        model_type: 使用的模型类型，支持 "gemini-2.5-pro" 或 "kimi-k2-0711-preview"
        
    Returns:
        Configured  Application instance.
    """
    return  Application(
        api_config=api_config,
        settings=settings,
        model_type=model_type
    )


async def main() -> None:
    """Main entry point for the application.
    
    This function demonstrates basic usage of the   application
    following Google ADK patterns for application structure.
    """
    try:
        # 可以从环境变量或命令行参数获取model_type
        parser = argparse.ArgumentParser(description="  Knowledge Graph Builder")
        parser.add_argument('--model_type', type=str, help='模型类型: gemini-2.5-pro、kimi-k2-0711-preview 或 o3-mini')
        args = parser.parse_args()

        # 优先级：命令行参数 > 环境变量 > 默认值
        model_type: ModelType = (
            args.model_type or
            os.environ.get('MODEL_TYPE') or
            "o3-mini"  # 默认使用 Azure OpenAI
        )
        
        # Create the application with specified model
        app = create_knowledge_graph_application(model_type=model_type)
        
        print("===   Knowledge Graph Builder ===")
        print(f"Using Model: {model_type}")
        
        # 指定one-shot示例文件
        root_dir = Path(__file__).parent.parent
        example_file = str(root_dir / "data" / "reinforcement_learning_hardcoded.json")
        
        # Create a knowledge graph for Machine Learning
        topic = "Machine Learning"
        knowledge_graph = await app.create_knowledge_graph(
            topic=topic,
            save_to_file=True,
            one_shot_example=example_file
        )
        
        print(f"\nKnowledge graph created for '{topic}':")
        print(f"- Nodes: {knowledge_graph.get_node_count()}")
        print(f"- Edges: {knowledge_graph.get_edge_count()}")
        
        # List all saved graphs
        saved_graphs = await app.list_saved_graphs()
        if saved_graphs:
            print("\nSaved graphs:")
            for graph_file in saved_graphs:
                print(f"- {graph_file}")
        
        print("\nApplication completed successfully!")
        
    except Exception as e:
        logger.error(f"Application failed: {e}")
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Run the main application
    exit_code = asyncio.run(main())
    exit(exit_code)
