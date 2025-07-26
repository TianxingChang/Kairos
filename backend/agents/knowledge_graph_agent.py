"""知识图谱生成 Agent，使用 agno 框架."""

import json
import logging
from textwrap import dedent
from typing import Optional, Dict, Any
from pathlib import Path

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools import Toolkit

from core.plan.kg_construction.models.knowledge_graph import KnowledgeGraph
from core.plan.kg_construction.config.settings import Settings
from db.session import db_url

logger = logging.getLogger(__name__)


class KnowledgeGraphTool(Toolkit):
    """知识图谱生成工具."""
    
    def __init__(self):
        super().__init__(name="knowledge_graph_tool")
        
        self.register(self.generate_knowledge_graph)
        self.register(self.save_knowledge_graph)
        self.register(self.load_example_format)
    
    def generate_knowledge_graph(self, topic: str, example_format: Optional[str] = None) -> str:
        """
        生成指定主题的知识图谱。
        
        Args:
            topic: 要生成知识图谱的主题
            example_format: 可选的格式示例
            
        Returns:
            生成的知识图谱JSON字符串
        """
        try:
            prompt = f"""
请为主题"{topic}"创建一个详细的知识前置依赖图。

**重要要求：请严格按照以下JSON格式输出，不要包含任何其他文字说明。**

必须包含的字段结构：

1. 根级别必需字段：
   - topic: 设置为 "{topic}"
   - nodes: 节点数组
   - edges: 边数组

2. 每个节点（node）必需字段：
   - id: 唯一标识符（格式：前缀_数字_描述，如 "ml_1_basics"）
   - label: 中文名称（如 "机器学习基础"）
   - domain: 领域分类（如 "机器学习基础"）

3. 每个边（edge）必需字段：
   - source: 前置节点的id
   - target: 目标节点的id  
   - type: 固定值 "PREREQUISITE"

**严格按照以下示例格式输出JSON：**

{{
    "topic": "{topic}",
    "nodes": [
        {{
            "id": "concept_1_foundation",
            "label": "基础概念",
            "domain": "基础知识"
        }},
        {{
            "id": "concept_2_intermediate", 
            "label": "中级概念",
            "domain": "进阶知识"
        }},
        {{
            "id": "concept_3_advanced",
            "label": "高级概念", 
            "domain": "高级知识"
        }}
    ],
    "edges": [
        {{
            "source": "concept_1_foundation",
            "target": "concept_2_intermediate",
            "type": "PREREQUISITE"
        }},
        {{
            "source": "concept_2_intermediate", 
            "target": "concept_3_advanced",
            "type": "PREREQUISITE"
        }}
    ]
}}

**注意：**
- 每个节点必须包含 id、label、domain 三个字段
- 每个边必须包含 source、target、type 三个字段
- 不要使用 from/to，必须使用 source/target
- 直接返回有效的JSON，不要包含任何解释文字

{f"参考格式示例：{example_format}" if example_format else ""}

请直接返回符合上述格式的JSON数据：
"""
            return prompt
            
        except Exception as e:
            logger.error(f"生成知识图谱提示失败: {e}")
            return f"生成失败: {str(e)}"
    
    def save_knowledge_graph(self, graph_json: str, topic: str) -> str:
        """
        保存知识图谱到文件。
        
        Args:
            graph_json: 知识图谱JSON字符串
            topic: 主题名称
            
        Returns:
            保存结果信息
        """
        try:
            # 验证JSON格式
            graph_data = json.loads(graph_json)
            knowledge_graph = KnowledgeGraph.model_validate(graph_data)
            
            # 获取保存路径
            settings = Settings.get_default()
            kg_dir = Path(settings.data_dir)
            kg_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = topic.replace(' ', '_').replace('/', '_')
            filename = f"{safe_topic}_{timestamp}.json"
            filepath = kg_dir / filename
            
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            
            validation_errors = knowledge_graph.validate_graph_integrity()
            validation_info = f"\n验证结果: {validation_errors}" if validation_errors else "\n图结构验证通过"
            
            return f"知识图谱已保存到: {filepath}\n节点数量: {knowledge_graph.get_node_count()}\n边数量: {knowledge_graph.get_edge_count()}{validation_info}"
            
        except json.JSONDecodeError as e:
            return f"JSON格式错误: {str(e)}"
        except Exception as e:
            logger.error(f"保存知识图谱失败: {e}")
            return f"保存失败: {str(e)}"
    
    def load_example_format(self, example_file: str = "reinforcement_learning_hardcoded.json") -> str:
        """
        加载示例格式文件。
        
        Args:
            example_file: 示例文件名
            
        Returns:
            示例文件内容
        """
        try:
            # 查找示例文件
            possible_paths = [
                Path("backend/core/plan/data") / example_file,
                Path("core/plan/data") / example_file,
                Path("data") / example_file,
            ]
            
            for path in possible_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return f"已加载示例格式: {path}\n内容:\n{content}"
            
            return f"未找到示例文件: {example_file}"
            
        except Exception as e:
            logger.error(f"加载示例格式失败: {e}")
            return f"加载失败: {str(e)}"


def get_knowledge_graph_agent(
    model = None,
    model_id: str = None,  # 改为None，优先使用传入的model
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """创建知识图谱生成 Agent."""
    # 如果没有提供模型实例，则调用selector来获取正确的模型
    if model is None:
        from agents.selector import _get_model
        model = _get_model(model_id)
    
    return Agent(
        name="Knowledge Graph Agent",
        agent_id="knowledge_graph_agent",
        user_id=user_id,
        session_id=session_id,
        model=model,
        # Tools available to the agent
        tools=[KnowledgeGraphTool()],
        # Description of the agent
        description=dedent("""\
            你是知识图谱架构师，专门负责为各种学科主题创建结构化的知识前置依赖图。

            你的目标是帮助用户理解复杂主题的学习路径，通过创建清晰的知识依赖关系图来指导学习过程。
        """),
        # Instructions for the agent
        instructions=dedent("""\
            你是一位专业的知识图谱架构师，擅长将复杂的学科知识结构化为清晰的学习路径。

            工作流程：
            1. **理解需求**: 分析用户想要创建知识图谱的主题
            2. **加载示例**: 如果需要，使用 load_example_format 工具加载格式示例
            3. **生成图谱**: 使用 generate_knowledge_graph 工具创建知识图谱
            4. **保存结果**: 使用 save_knowledge_graph 工具保存生成的图谱

            设计原则：
            - 知识粒度：优先将知识点拆分为1小时的学习单元
            - 依赖关系：确保前置知识的合理性和必要性
            - 结构完整：从基础概念到高级主题的完整覆盖
            - 实用导向：注重知识在实践中的应用价值

            输出要求：
            - 使用中文描述所有概念
            - 节点ID使用英文，格式为"领域前缀_序号_描述"
            - 确保JSON格式的正确性
            - 提供清晰的学习时间估计

            记住：你的目标是创建既科学又实用的知识学习路径图。
        """),
        # -*- Storage -*-
        storage=PostgresAgentStorage(table_name="knowledge_graph_sessions", db_url=db_url),
        # -*- History -*-
        add_history_to_messages=True,
        num_history_runs=3,
        read_chat_history=True,
        # -*- Memory -*-
        memory=Memory(
            model=model,
            db=PostgresMemoryDb(table_name="kg_user_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # -*- Other settings -*-
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    ) 