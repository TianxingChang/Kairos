"""Google Gemini API client for knowledge graph generation."""

import json
import logging
from typing import Dict, Any, Optional
import os

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from core.plan.kg_construction.clients.base_client import BaseApiClient, ApiClientError, ApiAuthenticationError, ApiResponseError
from core.plan.kg_construction.config.api_config import ApiConfig
from core.plan.kg_construction.models.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class GeminiClient(BaseApiClient):
    """Google Gemini API client implementation."""
    
    def __init__(self, config: ApiConfig):
        """Initialize the Gemini client.
        
        Args:
            config: API configuration instance.
            
        Raises:
            ApiAuthenticationError: If authentication setup fails.
        """
        self._config = config
        self._setup_authentication()
        self._model = self._create_model()
    
    def _setup_authentication(self) -> None:
        """Setup authentication for Gemini API.
        
        Raises:
            ApiAuthenticationError: If authentication fails.
        """
        try:
            self._config.setup_environment()
            
            # 检查两个可能的API密钥环境变量
            api_key = (
                os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") or 
                os.getenv("GOOGLE_API_KEY") or 
                self._config.api_key
            )
            
            if not api_key:
                raise ApiAuthenticationError("No API key found")
            
            # 同时设置两个环境变量
            os.environ["GOOGLE_API_KEY"] = api_key
            os.environ["GOOGLE_GENERATIVE_AI_API_KEY"] = api_key
            
            genai.configure(api_key=api_key)
            
            logger.info(
                f"Gemini client initialized with {'Vertex AI' if self._config.use_vertex_ai else 'API Studio'}"
            )
            
        except Exception as e:
            raise ApiAuthenticationError(f"Failed to setup Gemini authentication: {e}")
    
    def _create_model(self) -> genai.GenerativeModel:
        """Create and configure the generative model.
        
        Returns:
            Configured GenerativeModel instance.
        """
        return genai.GenerativeModel('gemini-2.5-pro')
    
    def _build_prompt(self, topic: str, example_json: Optional[str] = None) -> str:
        """构建知识图谱生成提示。
        
        Args:
            topic: 要生成知识图谱的主题
            example_json: 可选的示例 JSON 格式
            
        Returns:
            格式化的提示字符串
        """
        # 获取 Pydantic schema 定义
        schema_definition = KnowledgeGraph.model_json_schema()
        
        base_prompt = f"""
You are a Knowledge Architect. Your task is to generate a comprehensive knowledge prerequisite graph for "{topic}" in Chinese (Simplified Chinese).

Your output MUST be a single, valid JSON object that conforms to the following JSON Schema and format requirements. Do NOT include any text, comments, or markdown formatting outside of the JSON object itself.

**Node Format Example:**
```json
{{
    "id": "drl_2_dqn",
    "label": "深度Q网络 (DQN)",
    "domain": "深度强化学习",
    "description": "用深度神经网络近似Q函数，并引入经验回放和固定Q目标技术。",
    "importance": "深度强化学习的开山之作。",
    "estimatedHours": 2
}}
```

**Content Requirements:**

1. **Knowledge Granularity:**
   - 优先将知识点拆分为1小时的学习单元
   - 只有当概念确实复杂且不可再分时，才使用多个小时
   - 如果一个知识点预计超过2小时，考虑是否可以拆分成多个相关的1小时知识点
   - 确保每个1小时的知识点内容充实但不过载

2. **Node ID Format:**
   - Use meaningful prefixes for categories (e.g., "drl_" for 深度强化学习)
   - Follow with a number for sequence (e.g., "drl_1_", "drl_2_")
   - End with a short descriptive term (e.g., "dqn", "policy_gradient")
   - Example: "drl_2_dqn", "ml_1_basics"

3. **Node Content Format:**
   - label: 简洁的中文名称，可以在括号中包含英文缩写
   - domain: 领域分类（如"深度强化学习"、"机器学习基础"）
   - description: 一句话简明描述，重点突出技术要点
   - importance: 一句话说明重要性，突出历史地位或应用价值
   - estimatedHours: 优先使用1，确实需要更多时间时可以使用2-3

4. **Graph Structure:**
   - 按照领域和难度顺序组织节点
   - 确保前置知识合理连接
   - 保持知识点的连贯性和渐进性
   - 复杂概念优先拆分，而不是简单地增加学习时间

**Final Check before outputting:**
- Verify most nodes have estimatedHours = 1
- Justify any nodes with estimatedHours > 1
- Verify node IDs follow the prefix_number_name pattern
- Ensure all content is in clear, professional Chinese
- Validate all node IDs in `edges` exist in the `nodes` array
- Check that descriptions and importance are concise and informative
- Make sure to use "domain" instead of "category" for the domain field

**JSON Schema:**
```json
{schema_definition}
```
"""

        if example_json:
            base_prompt += f"""

Reference Example:
```json
{example_json}
```

Remember: Follow the EXACT same format as shown in the Node Format Example, maintaining consistent style and structure throughout the graph. Prioritize breaking down knowledge into 1-hour learning units whenever possible. Always use "domain" as the field name for categorization.
"""

        return base_prompt

    async def _repair_json_with_llm(self, faulty_json: str, error_message: str) -> str:
        """使用 LLM 修复损坏的 JSON 字符串。

        Args:
            faulty_json: 有语法错误的 JSON 字符串
            error_message: JSON 解析器报告的错误信息

        Returns:
            修复后的 JSON 字符串
        """
        logger.info("尝试使用 LLM 修复 JSON...")
        repair_prompt = f"""
The following JSON is malformed. Please fix the syntax errors and return ONLY the corrected, complete, and valid JSON object. Do NOT add any explanatory text.

Error reported by the parser:
{error_message}

Faulty JSON to fix:
```json
{faulty_json}
```
"""

        try:
            # 使用同一个模型进行修复
            response = await self._model.generate_content_async(
                repair_prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json"
                ),
                request_options={"timeout": 300}  # 5分钟超时
            )

            # 移除可能的 markdown 代码块
            repaired_text = response.text.strip()
            if repaired_text.startswith("```json"):
                repaired_text = repaired_text[7:]
            if repaired_text.startswith("```"):
                repaired_text = repaired_text[3:]
            if repaired_text.endswith("```"):
                repaired_text = repaired_text[:-3]

            return repaired_text.strip()

        except Exception as e:
            logger.error(f"LLM JSON 修复失败: {e}")
            return faulty_json  # 修复失败时返回原文

    async def _parse_response(self, response: Any, topic: str) -> KnowledgeGraph:
        """解析并验证 API 响应。

        Args:
            response: 原始 API 响应
            topic: 原始主题（用于上下文）

        Returns:
            验证后的 KnowledgeGraph 实例

        Raises:
            ApiResponseError: 如果解析失败
        """
        try:
            raw_text = response.text.strip()

            try:
                # 首次尝试直接解析
                graph_data = json.loads(raw_text)
            except json.JSONDecodeError as e:
                logger.warning(f"初始 JSON 解析失败: {e}，尝试使用 LLM 修复")
                # 解析失败，调用 LLM 进行修复
                repaired_text = await self._repair_json_with_llm(raw_text, str(e))

                try:
                    # 再次尝试解析修复后的文本
                    graph_data = json.loads(repaired_text)
                    logger.info("LLM 修复后成功解析 JSON")
                except json.JSONDecodeError as final_e:
                    logger.error(f"修复尝试后 JSON 解析仍然失败: {final_e}")
                    logger.debug("原始响应:\n" + raw_text)
                    logger.debug("修复后仍然失败的文本:\n" + repaired_text)
                    raise ApiResponseError(f"修复后的响应格式仍然无效: {final_e}")

            # 验证知识图谱模型
            knowledge_graph = KnowledgeGraph.model_validate(graph_data)
            validation_errors = knowledge_graph.validate_graph_integrity()
            if validation_errors:
                logger.warning(f"图验证警告: {validation_errors}")

            logger.info(
                f"成功生成图谱，包含 {knowledge_graph.get_node_count()} 个节点"
                f"和 {knowledge_graph.get_edge_count()} 条边"
            )

            return knowledge_graph

        except Exception as e:
            logger.error(f"解析响应时发生意外错误: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                logger.debug(f"原始响应文本: {response.text}")
            raise ApiResponseError(f"处理响应失败: {e}")
    
    async def generate_knowledge_graph(
        self,
        topic: str,
        one_shot_example: Optional[str] = None
    ) -> KnowledgeGraph:
        """Generate a knowledge graph for the given topic using Gemini API.
        
        Args:
            topic: The topic to generate a knowledge graph for.
            one_shot_example: Path to a JSON file to use as format example.
            
        Returns:
            A validated KnowledgeGraph instance.
            
        Raises:
            ApiClientError: If the API call fails.
            ApiResponseError: If the response cannot be parsed.
        """
        try:
            # 如果提供了示例文件，读取它
            example_json = None
            if one_shot_example:
                try:
                    with open(one_shot_example, 'r', encoding='utf-8') as f:
                        example_json = f.read()
                except Exception as e:
                    logger.warning(f"Failed to read example file {one_shot_example}: {e}")
            
            prompt = self._build_prompt(topic, example_json)
            
            logger.info(f"Generating knowledge graph for topic: {topic}")
            
            response = await self._model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json"
                ),
                request_options={"timeout": 300}  # 5分钟超时
            )
            
            return await self._parse_response(response, topic)
            
        except Exception as e:
            logger.error(f"Failed to generate knowledge graph: {e}")
            raise ApiClientError(f"Knowledge graph generation failed: {e}")
