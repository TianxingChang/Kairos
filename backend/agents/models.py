"""自定义 LLM 模型，集成到 agno 框架中."""

import logging
from typing import Any, Dict, List, Optional, AsyncGenerator, AsyncIterator
import json
import asyncio
import os
from dotenv import load_dotenv

from openai import AzureOpenAI
from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse

from core.plan.kg_construction.clients.gemini_client import GeminiClient
from core.plan.kg_construction.clients.kimi_client import KimiClient
from core.plan.kg_construction.config.api_config import ApiConfig

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv(dotenv_path=".env")


class AzureOpenAIModel(Model):
    """Azure OpenAI LLM 模型，集成到 agno 框架中."""
    
    id: str = "o3-mini"
    name: str = "Azure OpenAI o3-mini"
    provider: str = "Azure"
    
    def __init__(self, **kwargs):
        kwargs["id"] = self.id
        super().__init__(**kwargs)
        # 初始化 Azure OpenAI 客户端，增加超时配置
        self._client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2025-02-01-preview",
            azure_deployment="o3-mini",
            azure_endpoint="https://hkust.azure-api.net",
            timeout=60.0,  # 增加超时时间到60秒
            max_retries=3,  # 设置重试次数
        )
    
    @property
    def request_kwargs(self) -> Dict[str, Any]:
        """获取请求参数."""
        return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
        }
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """转换消息格式."""
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
    
    async def ainvoke(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """异步调用模型，增加重试机制."""
        import time
        max_retries = 3
        base_delay = 2.0  # 基础延迟秒数
        
        for attempt in range(max_retries):
            try:
                t0 = time.time()
                converted_messages = self._convert_messages(messages)
                # 统计消息长度和 token 粗略估算
                total_chars = sum(len(m["content"]) for m in converted_messages)
                total_msgs = len(converted_messages)
                # 简单 token 估算：字符数/4
                est_tokens = total_chars // 4
                logger.info(f"[AzureOpenAI] 尝试 {attempt + 1}/{max_retries} - 消息数: {total_msgs}, 总字符: {total_chars}, 估算token: {est_tokens}")
                t1 = time.time()
                logger.info(f"[AzureOpenAI] 消息准备耗时: {t1-t0:.2f}s")
                
                response = await asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=self.id,
                    messages=converted_messages,
                    timeout=60.0  # 单次请求60秒超时
                )
                t2 = time.time()
                logger.info(f"[AzureOpenAI] openai 响应耗时: {t2-t1:.2f}s")
                content = response.choices[0].message.content
                logger.info(f"[AzureOpenAI] 响应内容长度: {len(content)} 字符")
                logger.info(f"[AzureOpenAI] 总耗时: {t2-t0:.2f}s")
                return ModelResponse(
                    content=content
                )
                
            except Exception as e:
                logger.warning(f"[AzureOpenAI] 尝试 {attempt + 1}/{max_retries} 失败: {e}")
                
                # 如果是最后一次尝试，直接返回错误
                if attempt == max_retries - 1:
                    logger.error(f"Azure OpenAI 模型调用失败（已重试{max_retries}次）: {e}")
                    return ModelResponse(
                        content=f"抱歉，调用模型时出现错误（已重试{max_retries}次）: {str(e)}"
                    )
                
                # 指数退避延迟
                delay = base_delay * (2 ** attempt)
                logger.info(f"[AzureOpenAI] 等待 {delay:.1f} 秒后重试...")
                await asyncio.sleep(delay)
    
    async def ainvoke_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[ModelResponse]:
        """异步流式调用模型."""
        try:
            response = await self.ainvoke(messages, **kwargs)
            
            # 将响应分块
            content = response.content
            chunk_size = 50  # 每块字符数
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield ModelResponse(
                    content=chunk
                )
                
        except Exception as e:
            logger.error(f"Azure OpenAI 流式调用失败: {e}")
            yield ModelResponse(
                content=f"抱歉，调用模型时出现错误: {str(e)}"
            )
    
    def invoke(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """同步调用模型."""
        return asyncio.run(self.ainvoke(messages, **kwargs))
    
    def invoke_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[ModelResponse]:
        """同步流式调用模型."""
        return asyncio.run(self.ainvoke_stream(messages, **kwargs).__anext__())
    
    def parse_provider_response(
        self,
        response: ModelResponse,
        **kwargs
    ) -> ModelResponse:
        """解析提供者响应."""
        return response
    
    def parse_provider_response_delta(
        self,
        response: ModelResponse,
        **kwargs
    ) -> ModelResponse:
        """解析提供者流式响应."""
        return response


class GeminiModel(Model):
    """Gemini LLM 模型，集成到 agno 框架中."""
    
    id: str = "gemini-2.5-pro"
    name: str = "Gemini 2.5 Pro"
    provider: str = "Google"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化 Gemini 客户端
        api_config = ApiConfig(model_name="gemini-2.5-pro")
        self._client = GeminiClient(api_config)
    
    @property
    def request_kwargs(self) -> Dict[str, Any]:
        """获取请求参数."""
        return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
        }
    
    def _get_user_message(self, messages: List[Message]) -> str:
        """从消息列表中获取用户消息."""
        if messages:
            # 获取最后一条用户消息
            user_message = None
            for msg in reversed(messages):
                if msg.role == "user":
                    user_message = msg.content
                    break
            
            if not user_message:
                user_message = messages[-1].content if messages else ""
        else:
            user_message = ""
        
        return user_message
    
    async def ainvoke(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """异步调用模型."""
        try:
            user_message = self._get_user_message(messages)
            response = await self._client._model.generate_content_async(user_message)
            
            return ModelResponse(
                content=response.text
            )
            
        except Exception as e:
            logger.error(f"Gemini 模型调用失败: {e}")
            return ModelResponse(
                content=f"抱歉，调用模型时出现错误: {str(e)}"
            )
    
    async def ainvoke_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[ModelResponse]:
        """异步流式调用模型."""
        try:
            response = await self.ainvoke(messages, **kwargs)
            
            # 将响应分块
            content = response.content
            chunk_size = 50  # 每块字符数
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield ModelResponse(
                    content=chunk
                )
                
        except Exception as e:
            logger.error(f"Gemini 流式调用失败: {e}")
            yield ModelResponse(
                content=f"抱歉，调用模型时出现错误: {str(e)}"
            )
    
    def invoke(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """同步调用模型."""
        return asyncio.run(self.ainvoke(messages, **kwargs))
    
    def invoke_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[ModelResponse]:
        """同步流式调用模型."""
        return asyncio.run(self.ainvoke_stream(messages, **kwargs).__anext__())
    
    def parse_provider_response(
        self,
        response: ModelResponse,
        **kwargs
    ) -> ModelResponse:
        """解析提供者响应."""
        return response
    
    def parse_provider_response_delta(
        self,
        response: ModelResponse,
        **kwargs
    ) -> ModelResponse:
        """解析提供者流式响应."""
        return response


class KimiModel(Model):
    """Kimi LLM 模型，集成到 agno 框架中."""
    
    id: str = "kimi-k2-0711-preview"
    name: str = "Kimi K2"
    provider: str = "Moonshot"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化 Kimi 客户端
        api_config = ApiConfig(model_name="kimi-k2-0711-preview")
        self._client = KimiClient(api_config)
    
    @property
    def request_kwargs(self) -> Dict[str, Any]:
        """获取请求参数."""
        return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
        }
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """转换消息格式为 Kimi 格式."""
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
    
    async def ainvoke(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """异步调用模型."""
        try:
            kimi_messages = self._convert_messages(messages)
            
            # 使用 Kimi 客户端发送请求
            url = f"{self._client._base_url}/chat/completions"
            response = self._client._client.post(
                url,
                json={
                    "model": "kimi-k2-0711-preview",
                    "messages": kimi_messages,
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=300
            )
            
            response.raise_for_status()
            result = response.json()
            
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return ModelResponse(
                content=content
            )
            
        except Exception as e:
            logger.error(f"Kimi 模型调用失败: {e}")
            return ModelResponse(
                content=f"抱歉，调用模型时出现错误: {str(e)}"
            )
    
    async def ainvoke_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[ModelResponse]:
        """异步流式调用模型."""
        try:
            response = await self.ainvoke(messages, **kwargs)
            
            # 将响应分块
            content = response.content
            chunk_size = 50  # 每块字符数
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                yield ModelResponse(
                    content=chunk
                )
                
        except Exception as e:
            logger.error(f"Kimi 流式调用失败: {e}")
            yield ModelResponse(
                content=f"抱歉，调用模型时出现错误: {str(e)}"
            )
    
    def invoke(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """同步调用模型."""
        return asyncio.run(self.ainvoke(messages, **kwargs))
    
    def invoke_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[ModelResponse]:
        """同步流式调用模型."""
        return asyncio.run(self.ainvoke_stream(messages, **kwargs).__anext__())
    
    def parse_provider_response(
        self,
        response: ModelResponse,
        **kwargs
    ) -> ModelResponse:
        """解析提供者响应."""
        return response
    
    def parse_provider_response_delta(
        self,
        response: ModelResponse,
        **kwargs
    ) -> ModelResponse:
        """解析提供者流式响应."""
        return response 

# 设置默认模型
default_model = AzureOpenAIModel() 