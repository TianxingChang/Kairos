"""
Question diagnosis service module.
Provides core logic for analyzing user questions and identifying relevant knowledge points.
"""

import json
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from difflib import SequenceMatcher

from db.models import LearningResource, Knowledge, VideoSegment

logger = logging.getLogger(__name__)


class QuestionDiagnosisService:
    """Service for diagnosing user questions and identifying relevant knowledge points."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_contextual_knowledge_points(self, resource_id: int) -> List[Dict[str, Any]]:
        """
        Get all knowledge points associated with a specific learning resource.
        
        Args:
            resource_id: ID of the learning resource
            
        Returns:
            List of knowledge points with their details
        """
        try:
            # Query video segments to get associated knowledge points
            segments = self.db.query(VideoSegment).filter(
                VideoSegment.resource_id == resource_id
            ).all()
            
            if not segments:
                logger.warning(f"No video segments found for resource {resource_id}")
                return []
            
            # Get unique knowledge IDs from segments
            knowledge_ids = list(set(segment.knowledge_id for segment in segments))
            
            # Query knowledge points
            knowledge_points = self.db.query(Knowledge).filter(
                Knowledge.id.in_(knowledge_ids),
                Knowledge.is_active == True
            ).all()
            
            result = []
            for kp in knowledge_points:
                result.append({
                    "knowledge_id": kp.id,
                    "title": kp.title,
                    "description": kp.description,
                    "domain": kp.domain,
                    "difficulty_level": kp.difficulty_level,
                    "search_keywords": kp.search_keywords
                })
            
            logger.info(f"Found {len(result)} contextual knowledge points for resource {resource_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting contextual knowledge points for resource {resource_id}: {str(e)}")
            return []
    
    def get_global_knowledge_points(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all active knowledge points from the database for global search.
        
        Args:
            limit: Maximum number of knowledge points to return
            
        Returns:
            List of all knowledge points with their details
        """
        try:
            # Query all active knowledge points
            knowledge_points = self.db.query(Knowledge).filter(
                Knowledge.is_active == True
            ).limit(limit).all()
            
            result = []
            for kp in knowledge_points:
                result.append({
                    "knowledge_id": kp.id,
                    "title": kp.title,
                    "description": kp.description,
                    "domain": kp.domain,
                    "difficulty_level": kp.difficulty_level,
                    "search_keywords": kp.search_keywords
                })
            
            logger.info(f"Found {len(result)} global knowledge points")
            return result
            
        except Exception as e:
            logger.error(f"Error getting global knowledge points: {str(e)}")
            return []
    
    def keyword_based_prefilter(self, user_question: str, knowledge_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用关键词匹配对知识点进行预筛选，提高匹配准确性。
        """
        try:
            # 清理用户问题，提取关键词
            question_keywords = self._extract_keywords(user_question)
            logger.info(f"从问题中提取的关键词: {question_keywords}")
            
            scored_knowledge = []
            for kp in knowledge_points:
                score = self._calculate_keyword_similarity(question_keywords, kp)
                if score > 0.05:  # 降低筛选阈值，从0.1降到0.05
                    kp_with_score = kp.copy()
                    kp_with_score['keyword_score'] = score
                    scored_knowledge.append(kp_with_score)
            
            # 按关键词匹配分数排序
            scored_knowledge.sort(key=lambda x: x['keyword_score'], reverse=True)
            
            # 返回前20个最相关的知识点
            filtered_knowledge = scored_knowledge[:20]
            logger.info(f"关键词预筛选结果: {len(filtered_knowledge)} 个知识点")
            
            return filtered_knowledge
            
        except Exception as e:
            logger.error(f"关键词预筛选失败: {str(e)}")
            return knowledge_points[:20]  # 降级方案
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 移除标点符号，保持中英文字符
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        
        # 分别处理中文和英文
        words = []
        
        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]+', clean_text)
        words.extend([w.lower() for w in english_words if len(w) > 1])
        
        # 提取中文词汇（简单的基于常见分隔的分词）
        chinese_text = re.sub(r'[a-zA-Z0-9\s]', '', clean_text)
        
        # 基于常见术语进行分词
        technical_terms = [
            'PPO', 'ppo', 'clip', 'CNN', 'cnn', 'Transformer', 'transformer',
            '算法', '函数', '策略', '更新', '幅度', '神经网络', '卷积', '池化', 
            '梯度下降', '学习率', '强化学习', '机器学习', '深度学习',
            '注意力', '机制', '价值函数', '价值', '函数', '监督学习',
            '概念', '作用', '实现', '基础', '模型', '训练', '优化',
            'Q-learning', 'q-learning', 'DQN', 'dqn', 'A3C', 'a3c',
            'DDPG', 'ddpg', 'SAC', 'sac', 'TD3', 'td3', 'MDP', 'mdp',
            '马尔可夫', '决策过程', '环境', '智能体', 'agent', 'reward',
            '奖励', '动作', 'action', 'state', '状态', 'policy'
        ]
        
        # 检查文本中是否包含这些术语
        for term in technical_terms:
            if term.lower() in text.lower() or term in text:
                words.append(term.lower())
        
        # 添加单个中文字符作为关键词（长度大于1的）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', chinese_text)
        for char_group in chinese_chars:
            if len(char_group) >= 2:  # 至少2个字符的词
                words.append(char_group)
        
        # 定义停用词
        stopwords = {'的', '是', '在', '有', '和', '与', '或', '但', '可以', '能够', '什么', '为什么', '如何', '怎么', 
                    '吗', '呢', '了', '着', '过', '来', '去', '上', '下', '中', '里', '外', '前', '后', '左', '右',
                    '一个', '这个', '那个', '我们', '它们', '他们', '她们'}
        
        # 过滤停用词和重复词
        keywords = list(set([word for word in words if word not in stopwords and len(word) > 1]))
        
        return keywords
    
    def _calculate_keyword_similarity(self, question_keywords: List[str], knowledge_point: Dict[str, Any]) -> float:
        """计算问题关键词与知识点的相似度"""
        score = 0.0
        
        # 构建知识点的关键词集合
        kp_text = f"{knowledge_point.get('title', '')} {knowledge_point.get('description', '')} {knowledge_point.get('search_keywords', '')}"
        kp_keywords = self._extract_keywords(kp_text)
        
        # 精确匹配分数
        for q_word in question_keywords:
            for kp_word in kp_keywords:
                if q_word == kp_word:
                    score += 1.0
                elif q_word in kp_word or kp_word in q_word:
                    score += 0.5
                # 模糊相似度匹配
                elif len(q_word) > 2 and len(kp_word) > 2:
                    similarity = SequenceMatcher(None, q_word, kp_word).ratio()
                    if similarity > 0.7:
                        score += similarity * 0.3
        
        # 特殊处理：如果问题包含算法相关词汇，且知识点包含相关基础概念
        algorithm_terms = ['算法', 'ppo', 'q-learning', 'dqn', 'ddpg', 'sac', 'a3c']
        rl_basic_terms = ['强化学习', '基础', 'reinforcement', 'learning']
        
        question_lower = ' '.join(question_keywords).lower()
        kp_text_lower = kp_text.lower()
        
        if any(term in question_lower for term in algorithm_terms):
            if any(term in kp_text_lower for term in rl_basic_terms):
                score += 0.3  # 给予额外分数
        
        # 归一化分数
        if question_keywords:
            score = score / len(question_keywords)
        
        return min(score, 1.0)
    
    def build_diagnosis_prompt(
        self, 
        user_question: str, 
        contextual_knowledge_points: List[Dict[str, Any]]
    ) -> str:
        """
        Build the LLM prompt for diagnosing the user's question.
        
        Args:
            user_question: The user's natural language question
            contextual_knowledge_points: List of candidate knowledge points from current context
            
        Returns:
            Formatted prompt string for LLM analysis
        """
        # Format knowledge points for the prompt
        knowledge_list = []
        for i, kp in enumerate(contextual_knowledge_points, 1):
            knowledge_list.append(
                f"{i}. ID: {kp['knowledge_id']}\n"
                f"   标题: {kp['title']}\n"
                f"   描述: {kp.get('description', '无描述')}\n"
                f"   领域: {kp.get('domain', '未知')}\n"
                f"   关键词: {kp.get('search_keywords', '无关键词')}"
            )
        
        knowledge_context = "\n\n".join(knowledge_list) if knowledge_list else "无相关知识点"
        
        prompt = f"""# 用户问题智能诊断任务

## 任务描述
你是一个智能学习助手，需要分析用户在学习过程中提出的问题，并准确识别这个问题与哪些知识点相关。

## 用户问题
"{user_question}"

## 当前学习上下文中的候选知识点
{knowledge_context}

## 分析要求
请分析用户的问题，并从上述候选知识点中识别出与问题最相关的知识点。对于每个相关的知识点，请：

1. 评估其与用户问题的相关性（0.0-1.0分）
2. 解释为什么这个知识点与问题相关
3. 按相关性从高到低排序

## 输出格式
请严格按照以下JSON格式输出结果：

```json
{{
  "diagnosed_knowledge_points": [
    {{
      "knowledge_id": 123,
      "title": "知识点标题",
      "relevance_score": 0.95,
      "explanation": "详细解释为什么这个知识点与用户问题相关"
    }}
  ],
  "contextual_candidate_knowledge_points": [
    {{
      "knowledge_id": 124,
      "title": "候选知识点标题"
    }}
  ]
}}
```

## 注意事项
- 只选择相关性评分在0.2以上的知识点作为诊断结果
- 对于教育相关的概念问题，应该适当放宽匹配标准
- 如果问题中包含算法、技术概念等关键词，即使相关性不是最高也应该考虑匹配
- 确保explanation简洁明了，说明知识点与问题的关联性
- 如果问题涉及基础概念，优先匹配基础知识点
- 如果没有找到相关的知识点，diagnosed_knowledge_points可以为空数组
- contextual_candidate_knowledge_points应包含所有输入的候选知识点
- 相关性评分标准：0.8-1.0为高度相关，0.5-0.8为中度相关，0.2-0.5为低度相关但仍有价值
"""
        
        return prompt
    
    def parse_llm_response(self, llm_response: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse the LLM response to extract diagnosed knowledge points.
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            Tuple of (diagnosed_knowledge_points, contextual_candidate_knowledge_points)
        """
        try:
            # Try to extract JSON from the response
            # First, try to find JSON block in ```json ... ``` format
            import re
            json_match = re.search(r'```json\s*\n(.*?)\n```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in LLM response")
            
            # Parse JSON
            parsed_data = json.loads(json_str)
            
            diagnosed_points = parsed_data.get("diagnosed_knowledge_points", [])
            contextual_points = parsed_data.get("contextual_candidate_knowledge_points", [])
            
            # Validate diagnosed points structure
            for point in diagnosed_points:
                required_fields = ["knowledge_id", "title", "relevance_score", "explanation"]
                for field in required_fields:
                    if field not in point:
                        raise ValueError(f"Missing required field '{field}' in diagnosed knowledge point")
                
                # Ensure relevance_score is within valid range
                if not (0.0 <= point["relevance_score"] <= 1.0):
                    raise ValueError(f"Invalid relevance_score: {point['relevance_score']}")
            
            # Validate contextual points structure
            for point in contextual_points:
                required_fields = ["knowledge_id", "title"]
                for field in required_fields:
                    if field not in point:
                        raise ValueError(f"Missing required field '{field}' in contextual knowledge point")
            
            logger.info(f"Successfully parsed LLM response: {len(diagnosed_points)} diagnosed, {len(contextual_points)} contextual")
            return diagnosed_points, contextual_points
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            logger.error(f"LLM response was: {llm_response}")
            raise ValueError(f"Failed to parse LLM response: {str(e)}")
    
    def diagnose_user_question(
        self, 
        user_question: str, 
        contextual_knowledge_points: List[Dict[str, Any]],
        min_relevance_threshold: float = 0.2
    ) -> Tuple[List[Dict], List[Dict], bool]:
        """
        Perform two-stage diagnosis: contextual first, then global if needed.
        
        Args:
            user_question: The user's natural language question
            contextual_knowledge_points: Knowledge points from current context
            min_relevance_threshold: Minimum relevance score for contextual diagnosis
            
        Returns:
            Tuple of (diagnosed_points, contextual_points, used_global_search)
        """
        try:
            # Stage 1: Contextual diagnosis with keyword pre-filtering
            if contextual_knowledge_points:
                # 关键词预筛选
                filtered_contextual = self.keyword_based_prefilter(user_question, contextual_knowledge_points)
                
                prompt = self.build_diagnosis_prompt(user_question, filtered_contextual)
                llm_response = self._call_llm(prompt)
                
                if llm_response:
                    diagnosed_points, contextual_points = self.parse_llm_response(llm_response)
                    
                    # Check if contextual diagnosis was successful
                    if diagnosed_points:
                        max_relevance = max(point.get("relevance_score", 0) for point in diagnosed_points)
                        if max_relevance >= min_relevance_threshold:
                            logger.info(f"Contextual diagnosis successful with max relevance: {max_relevance}")
                            return diagnosed_points, contextual_points, False
                        else:
                            logger.info(f"Contextual diagnosis insufficient (max relevance: {max_relevance:.2f}), trying global search")
                    else:
                        logger.info("No diagnosed points found in contextual diagnosis, trying global search")
            
            # Stage 2: Global diagnosis (fallback) with enhanced filtering
            logger.info("Performing global knowledge search with enhanced filtering")
            global_knowledge_points = self.get_global_knowledge_points()
            
            if not global_knowledge_points:
                logger.warning("No global knowledge points available")
                return [], contextual_knowledge_points, True
            
            # 对全局知识点也进行关键词预筛选
            filtered_global = self.keyword_based_prefilter(user_question, global_knowledge_points)
            
            global_prompt = self.build_diagnosis_prompt(user_question, filtered_global)
            global_response = self._call_llm(global_prompt)
            
            if global_response:
                global_diagnosed, global_contextual = self.parse_llm_response(global_response)
                logger.info(f"Global diagnosis completed with {len(global_diagnosed)} diagnosed points")
                return global_diagnosed, global_contextual, True
            
            # If both stages fail, return contextual results as fallback
            logger.warning("Both contextual and global diagnosis failed, returning contextual results")
            return diagnosed_points if 'diagnosed_points' in locals() else [], contextual_knowledge_points, False
            
        except Exception as e:
            logger.error(f"Error in two-stage diagnosis: {str(e)}")
            raise
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with the given prompt and return response.
        
        Args:
            prompt: The formatted prompt string
            
        Returns:
            LLM response content or empty string if failed
        """
        try:
            from agents.selector import SmartModelSelector
            from agno.models.message import Message
            import asyncio
            
            model_selector = SmartModelSelector()
            messages = [Message(content=prompt, role="user")]
            
            # Create event loop if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run async function in sync context
            result = loop.run_until_complete(model_selector.get_response(messages))
            
            if result and len(result) == 2:
                response, model_name = result
                llm_response = response.content if response else ""
                logger.info(f"LLM response from {model_name}: {len(llm_response)} characters")
                # 添加调试日志
                logger.debug(f"LLM full response: {llm_response}")
                return llm_response
            
            return ""
            
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            return ""
    
    def validate_knowledge_points_exist(self, knowledge_ids: List[int]) -> List[int]:
        """
        Validate that knowledge points exist in the database.
        
        Args:
            knowledge_ids: List of knowledge point IDs to validate
            
        Returns:
            List of valid knowledge point IDs
        """
        try:
            existing_ids = self.db.query(Knowledge.id).filter(
                Knowledge.id.in_(knowledge_ids),
                Knowledge.is_active == True
            ).all()
            
            valid_ids = [row[0] for row in existing_ids]
            
            if len(valid_ids) != len(knowledge_ids):
                invalid_ids = set(knowledge_ids) - set(valid_ids)
                logger.warning(f"Invalid knowledge point IDs found: {invalid_ids}")
            
            return valid_ids
            
        except Exception as e:
            logger.error(f"Error validating knowledge point IDs: {str(e)}")
            return []