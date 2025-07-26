from enum import Enum
from typing import Optional, List, Union
import os
import logging
from dotenv import load_dotenv

from agno.models.openai import OpenAIChat
from agno.models.message import Message
from agno.models.response import ModelResponse

from agents.finance_agent import get_finance_agent
from agents.web_agent import get_web_agent
from agents.agno_assist import get_agno_assist
from agents.transcript_analyzer import get_transcript_analyzer
from agents.knowledge_graph_agent import get_knowledge_graph_agent
from agents.models import GeminiModel, KimiModel, AzureOpenAIModel

# 加载环境变量
load_dotenv(dotenv_path=".env")

logger = logging.getLogger(__name__)


class AgentType(Enum):
    WEB_AGENT = "web_agent"
    AGNO_ASSIST = "agno_assist"
    FINANCE_AGENT = "finance_agent"
    TRANSCRIPT_ANALYZER = "transcript_analyzer"
    KNOWLEDGE_GRAPH_AGENT = "knowledge_graph_agent"


class SmartModelSelector:
    """智能模型选择器，支持自动后备切换."""
    
    def __init__(self):
        # 初始化时为每个模型提供正确的id参数
        self.models = {
            "o3-mini": AzureOpenAIModel(id="o3-mini"),
            "gemini-2.5-pro": GeminiModel(id="gemini-2.5-pro"),
            "kimi-k2-0711-preview": KimiModel(id="kimi-k2-0711-preview")
        }
        # 定义后备模型顺序
        self.fallback_order = ["o3-mini", "gemini-2.5-pro", "kimi-k2-0711-preview"]
    
    async def get_response(self, messages, primary_model: str = None):
        """获取响应，支持自动后备切换."""
        if primary_model is None:
            primary_model = os.getenv('MODEL_TYPE', 'o3-mini')
        
        # 首先尝试主要模型
        try:
            model = self.models.get(primary_model)
            if model:
                logger.info(f"[SmartSelector] 尝试使用主要模型: {primary_model}")
                response = await model.ainvoke(messages)
                # 检查响应是否包含错误信息
                if not response.content.startswith("抱歉，调用模型时出现错误"):
                    return response, primary_model
                else:
                    logger.warning(f"[SmartSelector] 主要模型 {primary_model} 失败")
        except Exception as e:
            logger.warning(f"[SmartSelector] 主要模型 {primary_model} 异常: {e}")
        
        # 尝试后备模型
        for fallback_model in self.fallback_order:
            if fallback_model != primary_model:  # 跳过已经失败的主要模型
                try:
                    model = self.models.get(fallback_model)
                    if model:
                        logger.info(f"[SmartSelector] 尝试后备模型: {fallback_model}")
                        response = await model.ainvoke(messages)
                        if not response.content.startswith("抱歉，调用模型时出现错误"):
                            logger.info(f"[SmartSelector] 后备模型 {fallback_model} 成功")
                            return response, fallback_model
                        else:
                            logger.warning(f"[SmartSelector] 后备模型 {fallback_model} 失败")
                except Exception as e:
                    logger.warning(f"[SmartSelector] 后备模型 {fallback_model} 异常: {e}")
        
        # 所有模型都失败
        return ModelResponse(content="抱歉，所有可用模型都暂时无法访问，请稍后再试。"), None


# 全局智能选择器实例
smart_selector = SmartModelSelector()


def get_available_agents() -> List[str]:
    """Returns a list of all available agent IDs."""
    return [agent.value for agent in AgentType]


def _get_model(model_id: str = None):
    """根据 model_id 返回相应的模型实例."""
    # 如果没有指定 model_id，从环境变量读取
    if model_id is None:
        model_id = os.getenv('MODEL_TYPE', 'o3-mini')
    
    if model_id == "gemini-2.5-pro":
        return GeminiModel(id=model_id)
    elif model_id == "kimi-k2-0711-preview":
        return KimiModel(id=model_id)
    elif model_id == "o3-mini":
        return AzureOpenAIModel(id=model_id)
    else:
        # 对于其他 OpenAI 模型，使用默认的 OpenAIChat
        return OpenAIChat(id=model_id)


def get_model(model_id: str = None) -> Union[AzureOpenAIModel, GeminiModel, KimiModel, OpenAIChat]:
    """获取模型实例的公共接口."""
    return _get_model(model_id)


async def get_smart_response(messages, model_id: str = None):
    """获取智能响应，支持自动后备切换."""
    return await smart_selector.get_response(messages, model_id)


def get_agent(
    model_id: str = None,  # 改为默认None，从环境变量读取
    agent_id: Optional[AgentType] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    # 获取模型实例
    model = _get_model(model_id)
    
    if agent_id == AgentType.WEB_AGENT:
        return get_web_agent(model=model, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.AGNO_ASSIST:
        return get_agno_assist(model=model, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.FINANCE_AGENT:
        return get_finance_agent(model=model, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.TRANSCRIPT_ANALYZER:
        return get_transcript_analyzer(model=model, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.KNOWLEDGE_GRAPH_AGENT:
        return get_knowledge_graph_agent(model=model, user_id=user_id, session_id=session_id, debug_mode=debug_mode)

    raise ValueError(f"Agent: {agent_id} not found")
