"""Kimi API client for knowledge graph generation."""

import json
import logging
from typing import List, Dict, Optional, Any
import os # Added for os.getenv

import requests

from core.plan.kg_construction.clients.base_client import BaseApiClient, ApiClientError, ApiAuthenticationError, ApiResponseError
from core.plan.kg_construction.config.api_config import ApiConfig
from core.plan.kg_construction.models.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class KimiClient(BaseApiClient):
    """Kimi API client implementation."""
    
    def __init__(self, config: ApiConfig):
        """Initialize the Kimi client.
        
        Args:
            config: API configuration instance.
            
        Raises:
            ApiAuthenticationError: If authentication setup fails.
        """
        self._config = config
        self._setup_authentication()
        
        # 确保有API key
        api_key = os.getenv("MOONSHOT_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ApiAuthenticationError("Missing API key. Please set MOONSHOT_API_KEY or OPENAI_API_KEY environment variable.")
            
        # 初始化请求客户端
        self._base_url = "https://api.moonshot.cn/v1"  # 保存 base_url
        self._client = requests.Session()
        self._client.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        # 设置超时配置
        self._client.timeout = 300  # 5分钟超时
        logger.info("Kimi client initialized")
    
    def _setup_authentication(self) -> None:
        """Setup authentication for Kimi API.
        
        Raises:
            ApiAuthenticationError: If authentication fails.
        """
        try:
            self._config.setup_environment()
            logger.info("Kimi client initialized")
        except Exception as e:
            raise ApiAuthenticationError(f"Failed to setup Kimi authentication: {e}")
    
    def _build_prompt(self, topic: str, example_json: Optional[str] = None) -> List[Dict[str, str]]:
        """Build the chat messages for knowledge graph generation.
        
        Args:
            topic: The topic to generate a graph for.
            example_json: Example JSON content to use as format reference.
            
        Returns:
            List of chat messages.
        """
        system_message = {
            "role": "system",
            "content": """你是一位专业的知识图谱架构师，擅长构建精确的知识依赖关系图。
你的职责是分析主题，识别关键概念，并建立清晰的学习路径。

工作重点：
1. 概念粒度：每个节点应该是具体的知识点，而不是宽泛的主题
2. 结构完整：确保知识图谱从基础概念到高级主题的完整性
3. 依赖准确：仔细梳理概念间的前置依赖关系
4. 实用导向：注重知识在实践中的应用价值

注意事项：
- 只输出 JSON 对象，不要包含任何解释或其他文本
- 确保所有在边中引用的节点 ID 都存在于节点数组中
- 保持节点 ID 的一致性
- 严格遵循示例的 JSON 结构和格式"""
        }
        
        user_message = {
            "role": "user",
            "content": f"""请为主题"{topic}"创建知识图谱，遵循以下规范：

1. 节点(Node)要求：
   - ID格式：必须是小写字母+下划线（如 'basic_syntax'）
   - 内容要求：具体的知识点（不要过于宽泛）
   - 必填信息：预计学习时间、重要性说明
   - 合理分类：按领域归类（如：核心概念、前置知识、进阶主题）

2. 边(Edge)要求：
   - 严格表示前置依赖关系
   - 只能引用已定义的节点ID
   - 避免循环依赖
   - 保持依赖关系的直接性（如果A->B->C，就不要加A->C）

3. 完整性要求：
   - 所有节点都应该可以从基础概念到达
   - 所有边必须连接有效的节点ID
   - 节点ID必须唯一且具有描述性
   - 概念粒度要适中（不能太大也不能太小）

4. 内容建议：
   - 从其他领域的基础知识开始（数学、计算机等）
   - 过渡到本领域的基础概念
   - 最后到高级主题
   - 注意知识的实际应用场景

5. JSON格式要求（关键）：
   - 输出必须是单个完整的JSON对象
   - 每个对象必须以 {{ 开始，以 }} 结束
   - 每个数组必须以 [ 开始，以 ] 结束
   - 数组项之间必须用逗号分隔
   - 最后一项后不能有逗号
   - 所有字符串和字段名必须用双引号
   - 缩进必须保持一致

必需的JSON结构：
{{
    "topic": "主题名称",
    "nodes": [
        {{
            "id": "node_id_1",
            "label": "人类可读的标签",
            "domain": "领域分类",
            "description": "概念的详细描述",
            "importance": "为什么这个概念重要",
            "estimatedHours": 2
        }}
    ],
    "edges": [
        {{
            "source": "前置节点ID",
            "target": "依赖节点ID",
            "type": "PREREQUISITE"
        }}
    ]
}}

Schema定义：
{KnowledgeGraph.model_json_schema()}"""
        }
        
        if example_json:
            user_message["content"] += f"""

参考格式：
这是一个标准格式示例，请严格保持相同的结构，只改变内容以适配"{topic}"：

{example_json}

格式规则：
1. 以单个左大括号 {{ 开始
2. 以单个右大括号 }} 结束
3. 包含所有必需的字段
4. 保持完全相同的缩进模式
5. 数组项之间必须有逗号
6. 最后一项后不能有逗号
7. 所有字符串和字段名必须用双引号
8. 输出前验证 JSON 结构的正确性"""
        
        return [system_message, user_message]
    
    def _fix_json_format(self, text: str) -> str:
        """尝试修复常见的 JSON 格式问题。
        
        Args:
            text: 原始 JSON 文本
            
        Returns:
            修复后的 JSON 文本
        """
        # 1. 移除可能的 markdown 代码块标记
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        # 2. 确保使用双引号
        text = text.replace("'", '"')
        
        # 3. 处理常见的 JSON 格式问题
        lines = text.split("\n")
        fixed_lines = []
        in_array = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # 检查数组开始和结束
            if "[" in line:
                in_array = True
            if "]" in line:
                in_array = False
            
            # 修复缺少逗号的问题
            if in_array and i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if (line.endswith("}") or line.endswith('"')) and \
                   (next_line.startswith("{") or next_line.startswith('"')):
                    line += ","
            
            # 移除多余的逗号
            if line.endswith(",") and i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line.startswith("]") or next_line.startswith("}"):
                    line = line[:-1]
            
            fixed_lines.append(line)
        
        # 4. 重新组合并确保基本的 JSON 结构
        text = "\n".join(fixed_lines)
        
        # 5. 移除可能的注释
        text = "\n".join(line for line in text.split("\n") 
                        if not line.strip().startswith("//"))
        
        # 6. 确保对象和数组的闭合
        brackets_stack = []
        for char in text:
            if char in "{[":
                brackets_stack.append(char)
            elif char in "}]":
                if not brackets_stack:
                    continue
                if (char == "}" and brackets_stack[-1] == "{") or \
                   (char == "]" and brackets_stack[-1] == "["):
                    brackets_stack.pop()
        
        # 补充缺失的闭合括号
        while brackets_stack:
            bracket = brackets_stack.pop()
            text += "}" if bracket == "{" else "]"
        
        return text.strip()
    
    async def generate_knowledge_graph(
        self,
        topic: str,
        one_shot_example: Optional[str] = None
    ) -> KnowledgeGraph:
        """Generate a knowledge graph using Kimi API.
        
        Args:
            topic: The topic to generate a graph for.
            one_shot_example: Path to a JSON file to use as format example.
            
        Returns:
            A validated KnowledgeGraph instance.
            
        Raises:
            ApiClientError: If the API call fails.
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
            
            messages = self._build_prompt(topic, example_json)
            
            logger.info(f"Generating knowledge graph for topic: {topic}")
            
            # 完整的 URL
            url = f"{self._base_url}/chat/completions"
            
            # 发送请求
            response = self._client.post(
                url,
                json={
                    "model": "kimi-k2-0711-preview",
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7,  # 可选：控制输出的随机性
                    "max_tokens": 4000   # 可选：控制输出长度
                },
                timeout=300  # 5分钟超时
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            return self._parse_response(response, topic)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise ApiClientError(f"Failed to call Kimi API: {e}")
        except Exception as e:
            logger.error(f"Failed to generate knowledge graph: {e}")
            raise ApiClientError(f"Knowledge graph generation failed: {e}")
    
    def _parse_response(self, response: Any, topic: str) -> KnowledgeGraph:
        """Parse and validate the API response.
        
        Args:
            response: Raw API response.
            topic: Original topic for context.
            
        Returns:
            Validated KnowledgeGraph instance.
            
        Raises:
            ApiResponseError: If parsing fails.
        """
        try:
            # 1. 获取响应文本
            raw_text = response.text
            
            # 2. 尝试修复 JSON 格式
            fixed_text = self._fix_json_format(raw_text)
            
            try:
                # 3. 尝试解析修复后的 JSON
                graph_data = json.loads(fixed_text)
            except json.JSONDecodeError as e:
                # 4. 如果修复后仍然失败，记录详细信息
                logger.error(f"JSON parsing error: {str(e)}")
                logger.debug("Raw response text:")
                logger.debug(raw_text)
                logger.debug("Fixed text:")
                logger.debug(fixed_text)
                raise
            
            # 5. 验证知识图谱模型
            knowledge_graph = KnowledgeGraph.model_validate(graph_data)
            
            # 6. 验证图完整性
            validation_errors = knowledge_graph.validate_graph_integrity()
            if validation_errors:
                logger.warning(f"Graph validation warnings: {validation_errors}")
            
            logger.info(
                f"Successfully generated graph with {knowledge_graph.get_node_count()} "
                f"nodes and {knowledge_graph.get_edge_count()} edges"
            )
            
            return knowledge_graph
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")
            logger.debug(f"Raw response text: {response.text}")
            raise ApiResponseError(f"Invalid API response format: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while parsing response: {e}")
            raise ApiResponseError(f"Failed to process response: {e}") 