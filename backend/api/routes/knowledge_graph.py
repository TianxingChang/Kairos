"""Knowledge Graph construction API routes."""

import logging
from typing import Optional, List, Literal
from pathlib import Path
import os
import traceback
import json

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from agents.selector import AgentType, get_agent
from core.plan.kg_construction.models.knowledge_graph import KnowledgeGraph, KnowledgeNode, KnowledgeEdge
from db.session import get_db
from db.models import Knowledge, LearningResource, knowledge_resource_association, knowledge_prerequisites

logger = logging.getLogger(__name__)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

knowledge_graph_router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])

# 支持的模型类型
ModelType = Literal["gpt-4.1", "o4-mini", "gemini-2.5-pro", "kimi-k2-0711-preview", "o3-mini"]


class CreateKnowledgeGraphRequest(BaseModel):
    """Request model for creating a knowledge graph."""
    
    topic: str = Field(
        description="The topic to create a knowledge graph for",
        example="Machine Learning"
    )
    model_type: ModelType = Field(
        default=os.environ.get('MODEL_TYPE', 'o3-mini'),  # 从环境变量读取默认值
        description="The model type to use for generation"
    )
    save_to_file: bool = Field(
        default=True,
        description="Whether to save the graph to a file"
    )
    output_filename: Optional[str] = Field(
        default=None,
        description="Custom filename for output (optional)"
    )
    one_shot_example: Optional[str] = Field(
        default=None,
        description="Path to a JSON file to use as format example"
    )


class KnowledgeGraphResponse(BaseModel):
    """Response model for knowledge graph operations."""
    
    success: bool
    message: str
    graph: Optional[KnowledgeGraph] = None
    file_path: Optional[str] = None


class PrerequisiteKnowledge(BaseModel):
    """Response model for a prerequisite knowledge point."""
    
    id: int
    title: str
    description: Optional[str] = None
    domain: str
    difficulty_level: str
    estimated_hours: int
    learning_resources: List[dict] = []


class VideoPrerequisitesResponse(BaseModel):
    """Response model for video prerequisites API."""
    
    success: bool
    message: str
    video_id: int
    video_title: Optional[str] = None
    core_knowledge_points: List[dict] = []
    prerequisites: List[PrerequisiteKnowledge] = []
    analysis_method: str  # "database_lookup" or "llm_analysis"


@knowledge_graph_router.post("/create", response_model=KnowledgeGraphResponse)
async def create_knowledge_graph(request: CreateKnowledgeGraphRequest):
    """
    Create a knowledge graph for a given topic using agno Agent.
    
    Args:
        request: The knowledge graph creation request
        
    Returns:
        KnowledgeGraphResponse: The created knowledge graph and metadata
    """
    try:
        logger.info(f"Creating knowledge graph for topic: {request.topic} using model: {request.model_type}")
        
        # 创建知识图谱 Agent
        agent = get_agent(
            model_id=request.model_type,
            agent_id=AgentType.KNOWLEDGE_GRAPH_AGENT,
            debug_mode=True
        )
        
        # 构建提示消息
        prompt_parts = [f"请为主题'{request.topic}'创建知识图谱，直接返回JSON格式数据，不要包含任何其他说明文字"]
        
        if request.one_shot_example:
            prompt_parts.append(f"请先加载示例格式文件: {request.one_shot_example}")
        
        if request.save_to_file:
            prompt_parts.append("生成完成后请保存到文件")
            if request.output_filename:
                prompt_parts.append(f"文件名使用: {request.output_filename}")
        
        prompt = "。".join(prompt_parts) + "。"
        
        # 使用 Agent 生成知识图谱
        response = await agent.arun(prompt)
        
        # 解析响应中的知识图谱
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # 添加调试日志，查看实际生成的内容
        logger.info(f"LLM生成的原始响应: {response_text}")
        
        # 尝试从响应文本中提取 JSON
        import json
        import re
        
        # 查找 JSON 对象
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON object found in response")
            
        graph_json = json_match.group()
        logger.info(f"提取的JSON: {graph_json}")
        
        # 解析 JSON
        graph_data = json.loads(graph_json)
        
        # 自动修正常见格式错误
        if 'nodes' in graph_data:
            for node in graph_data['nodes']:
                # 如果缺少 label 字段，根据 id 生成
                if 'label' not in node and 'id' in node:
                    # 从 id 中提取描述部分作为 label
                    parts = node['id'].split('_')
                    if len(parts) >= 3:
                        node['label'] = parts[2]  # 使用第三部分作为 label
                    else:
                        node['label'] = node['id']  # 如果无法解析，使用整个 id
                
                # 确保有 domain 字段
                if 'domain' not in node:
                    node['domain'] = f"{node['id'].split('_')[0]}领域"
        
        if 'edges' in graph_data:
            for edge in graph_data['edges']:
                # 修正边的字段名：from -> source, to -> target
                if 'from' in edge and 'source' not in edge:
                    edge['source'] = edge.pop('from')
                if 'to' in edge and 'target' not in edge:
                    edge['target'] = edge.pop('to')
                
                # 确保有 type 字段
                if 'type' not in edge:
                    edge['type'] = 'PREREQUISITE'
        
        # 确保必要字段存在
        if 'topic' not in graph_data:
            graph_data['topic'] = request.topic
            
        # 验证数据
        knowledge_graph = KnowledgeGraph.model_validate(graph_data)
        
        # 如果需要保存到文件
        file_path = None
        if request.save_to_file:
            from core.plan.kg_construction.config.settings import Settings
            settings = Settings.get_default()
            kg_dir = Path(settings.data_dir)
            kg_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = request.output_filename or f"{request.topic.replace(' ', '_')}_{timestamp}.json"
            file_path = kg_dir / filename
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            file_path = str(file_path)
        
        return KnowledgeGraphResponse(
            success=True,
            message=f"Knowledge graph created successfully for topic: {request.topic}",
            graph=knowledge_graph,
            file_path=file_path
        )
        
    except Exception as e:
        logger.error(f"Failed to create knowledge graph: {e}")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create knowledge graph: {str(e)}"
        )


@knowledge_graph_router.get("/list")
async def list_saved_graphs():
    """
    List all saved knowledge graphs.
    
    Returns:
        List of saved graph filenames
    """
    try:
        from core.plan.kg_construction.config.settings import Settings
        
        settings = Settings.get_default()
        kg_dir = Path(settings.data_dir)
        
        if not kg_dir.exists():
            return {"graphs": []}
        
        # 获取所有 JSON 文件
        graph_files = []
        for file_path in kg_dir.glob("*.json"):
            graph_files.append({
                "filename": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "created": file_path.stat().st_ctime
            })
        
        # 按创建时间排序
        graph_files.sort(key=lambda x: x["created"], reverse=True)
        
        return {"graphs": graph_files}
        
    except Exception as e:
        logger.error(f"Failed to list saved graphs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list saved graphs: {str(e)}"
        )


@knowledge_graph_router.get("/load/{filename}")
async def load_knowledge_graph(filename: str):
    """
    Load a specific knowledge graph by filename.
    
    Args:
        filename: The filename of the graph to load
        
    Returns:
        The loaded knowledge graph
    """
    try:
        from core.plan.kg_construction.config.settings import Settings
        
        settings = Settings.get_default()
        kg_dir = Path(settings.data_dir)
        file_path = kg_dir / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge graph file not found: {filename}"
            )
        
        # 加载并验证知识图谱
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        knowledge_graph = KnowledgeGraph.model_validate(graph_data)
        
        return {
            "filename": filename,
            "graph": knowledge_graph,
            "metadata": {
                "nodes": knowledge_graph.get_node_count(),
                "edges": knowledge_graph.get_edge_count(),
                "file_size": file_path.stat().st_size
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to load knowledge graph {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load knowledge graph: {str(e)}"
        )


def get_associated_knowledge_points(db: Session, resource_id: int) -> List[int]:
    """Get knowledge points associated with a resource from database."""
    try:
        result = db.execute(
            text("""
            SELECT knowledge_id 
            FROM knowledge_resource_association 
            WHERE resource_id = :resource_id
            """),
            {"resource_id": resource_id}
        )
        return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Error querying knowledge_resource_association: {e}")
        return []


def get_recursive_prerequisites(db: Session, knowledge_ids: List[int]) -> List[int]:
    """Recursively get all prerequisite knowledge points."""
    if not knowledge_ids:
        return []
    
    all_prerequisites = set()
    to_process = set(knowledge_ids)
    processed = set()
    
    while to_process:
        current_ids = list(to_process)
        to_process.clear()
        
        try:
            placeholders = ', '.join([f':id_{i}' for i in range(len(current_ids))])
            params = {f'id_{i}': id_val for i, id_val in enumerate(current_ids)}
            
            result = db.execute(
                text(f"""
                SELECT DISTINCT prerequisite_id 
                FROM knowledge_prerequisites 
                WHERE knowledge_id IN ({placeholders})
                """),
                params
            )
            
            for row in result.fetchall():
                prereq_id = row[0]
                if prereq_id not in processed and prereq_id not in all_prerequisites:
                    all_prerequisites.add(prereq_id)
                    to_process.add(prereq_id)
            
            processed.update(current_ids)
            
        except Exception as e:
            logger.error(f"Error in recursive prerequisites query: {e}")
            break
    
    return list(all_prerequisites)


def get_knowledge_details(db: Session, knowledge_ids: List[int]) -> List[Knowledge]:
    """Get detailed information for knowledge points."""
    if not knowledge_ids:
        return []
    
    try:
        return db.query(Knowledge).filter(Knowledge.id.in_(knowledge_ids)).all()
    except Exception as e:
        logger.error(f"Error querying knowledge details: {e}")
        return []


def get_best_resources_for_knowledge(db: Session, knowledge_id: int, limit: int = 3) -> List[dict]:
    """Get the best learning resources for a knowledge point."""
    try:
        result = db.execute(
            text("""
            SELECT lr.id, lr.title, lr.resource_type, lr.resource_url, 
                   lr.description, lr.quality_score, lr.duration_minutes
            FROM learning_resource lr
            JOIN knowledge_resource_association kra ON lr.id = kra.resource_id
            WHERE kra.knowledge_id = :knowledge_id 
                AND lr.is_available = true
            ORDER BY lr.quality_score DESC, lr.id DESC
            LIMIT :limit
            """),
            {"knowledge_id": knowledge_id, "limit": limit}
        )
        
        resources = []
        for row in result.fetchall():
            resources.append({
                "id": row[0],
                "title": row[1],
                "resource_type": row[2],
                "resource_url": row[3],
                "description": row[4],
                "quality_score": row[5],
                "duration_minutes": row[6]
            })
        return resources
    except Exception as e:
        logger.error(f"Error querying resources for knowledge {knowledge_id}: {e}")
        return []


def extract_knowledge_from_transcript_llm(db: Session, resource: LearningResource) -> List[int]:
    """Fallback: Extract knowledge points from transcript using LLM."""
    if not resource.transcript:
        logger.warning(f"No transcript available for resource {resource.id}")
        return []
    
    try:
        # Use existing transcript analyzer
        from agents.transcript_analyzer import get_transcript_analyzer
        from agents.selector import _get_model
        
        model = _get_model("gpt-4")
        analyzer = get_transcript_analyzer(model=model, debug_mode=True)
        
        # Create a prompt to extract knowledge points
        prompt = f"""
        分析以下视频转录文本，提取其中包含的主要知识点。
        请只返回知识点的标题列表，每行一个，不要包含任何其他文字或解释。
        
        转录文本：
        {resource.transcript[:3000]}
        
        请提取的知识点应该是具体的概念、技术或方法，例如：
        - 深度学习
        - 卷积神经网络
        - 反向传播算法
        - 强化学习
        
        知识点列表：
        """
        
        response = analyzer.model.run(prompt)
        knowledge_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse LLM response to extract knowledge point names
        knowledge_titles = []
        for line in knowledge_text.strip().split('\n'):
            line = line.strip()
            # Improved filtering: allow 3+ character terms like "PPO", "CNN", "RNN"
            if len(line) >= 3 and not line.startswith('#') and not line.startswith('-'):
                # Remove bullet points and numbering
                clean_line = line.lstrip('- •*').strip()
                if clean_line and len(clean_line) >= 3:
                    knowledge_titles.append(clean_line)
        
        # Match against database using both title and search_keywords
        matched_ids = []
        for title in knowledge_titles:
            try:
                # Search in both title and search_keywords fields
                result = db.execute(
                    text("""
                    SELECT id FROM knowledge 
                    WHERE (LOWER(title) LIKE LOWER(:pattern) 
                           OR LOWER(search_keywords) LIKE LOWER(:pattern))
                        AND is_active = true
                    LIMIT 1
                    """),
                    {"pattern": f"%{title.lower()}%"}
                )
                row = result.fetchone()
                if row:
                    matched_ids.append(row[0])
            except Exception as e:
                logger.error(f"Error matching knowledge point '{title}': {e}")
                continue
        
        logger.info(f"LLM extracted {len(knowledge_titles)} knowledge points, matched {len(matched_ids)} in database")
        return matched_ids
        
    except Exception as e:
        logger.error(f"Error in LLM knowledge extraction: {e}")
        return []


@knowledge_graph_router.get("/video/{resource_id}/prerequisites", response_model=VideoPrerequisitesResponse)
async def get_video_prerequisites(resource_id: int, db: Session = Depends(get_db)):
    """
    Get prerequisite knowledge for a video resource.
    
    Implements the complete data query chain:
    1. Find core knowledge points associated with the video
    2. Recursively traverse prerequisites in knowledge graph  
    3. Return prerequisite knowledge with best learning resources
    4. Fallback to LLM analysis if no associations exist
    
    Args:
        resource_id: The ID of the learning resource (video)
        db: Database session
        
    Returns:
        VideoPrerequisitesResponse: Prerequisites and learning resources
    """
    try:
        logger.info(f"Getting prerequisites for video resource {resource_id}")
        
        # Step 1: Get the video resource
        resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video resource not found: {resource_id}"
            )
        
        # Step 2: Try to get associated knowledge points from database
        core_knowledge_ids = get_associated_knowledge_points(db, resource_id)
        analysis_method = "database_lookup"
        
        # Step 3: Fallback to LLM analysis if no associations found
        if not core_knowledge_ids:
            logger.info(f"No knowledge associations found for resource {resource_id}, using LLM analysis")
            core_knowledge_ids = extract_knowledge_from_transcript_llm(db, resource)
            analysis_method = "llm_analysis"
        
        if not core_knowledge_ids:
            return VideoPrerequisitesResponse(
                success=True,
                message="No knowledge points found for this video",
                video_id=resource_id,
                video_title=resource.title,
                core_knowledge_points=[],
                prerequisites=[],
                analysis_method=analysis_method
            )
        
        # Step 4: Get core knowledge details
        core_knowledge = get_knowledge_details(db, core_knowledge_ids)
        core_knowledge_points = [
            {
                "id": k.id,
                "title": k.title,
                "description": k.description,
                "domain": k.domain,
                "difficulty_level": k.difficulty_level
            }
            for k in core_knowledge
        ]
        
        # Step 5: Recursively get all prerequisites
        prerequisite_ids = get_recursive_prerequisites(db, core_knowledge_ids)
        
        # Step 6: Get prerequisite knowledge details
        prerequisite_knowledge = get_knowledge_details(db, prerequisite_ids)
        
        # Step 7: For each prerequisite, get best learning resources
        prerequisites = []
        for knowledge in prerequisite_knowledge:
            resources = get_best_resources_for_knowledge(db, knowledge.id, limit=3)
            
            prereq = PrerequisiteKnowledge(
                id=knowledge.id,
                title=knowledge.title,
                description=knowledge.description,
                domain=knowledge.domain,
                difficulty_level=knowledge.difficulty_level,
                estimated_hours=knowledge.estimated_hours,
                learning_resources=resources
            )
            prerequisites.append(prereq)
        
        # Sort prerequisites by difficulty level and domain
        prerequisites.sort(key=lambda x: (x.difficulty_level, x.domain))
        
        logger.info(f"Found {len(core_knowledge_ids)} core knowledge points and {len(prerequisites)} prerequisites")
        
        return VideoPrerequisitesResponse(
            success=True,
            message=f"Found {len(prerequisites)} prerequisite knowledge points",
            video_id=resource_id,
            video_title=resource.title,
            core_knowledge_points=core_knowledge_points,
            prerequisites=prerequisites,
            analysis_method=analysis_method
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get video prerequisites: {e}")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video prerequisites: {str(e)}"
        ) 