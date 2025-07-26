from textwrap import dedent
from typing import Optional, Dict, List

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from pydantic import BaseModel

from db.session import db_url


class FullVideoTranscriptRequest(BaseModel):
    """完整视频转录文本请求模型"""
    video_id: str
    question: str


class FullVideoTranscriptResponse(BaseModel):
    """完整视频转录文本响应模型"""
    success: bool
    full_transcript: str
    answer: str
    video_info: Dict
    error: Optional[str] = None


def get_full_video_transcript(video_id: str) -> Dict:
    """
    获取完整视频的转录文本
    
    Args:
        video_id: YouTube视频ID
    
    Returns:
        包含完整转录文本的字典
    """
    try:
        from db.session import SessionLocal
        from db.youtube_service import get_video_transcript_from_file, get_video_info
        
        # 创建数据库会话
        db = SessionLocal()
        try:
            # 获取视频信息
            video_info = get_video_info(db, video_id)
            # 不再要求必须有视频信息，如果没有就使用默认值
            if not video_info:
                print(f"数据库中没有视频 {video_id} 的信息，使用默认值")
                video_info = type('MockVideo', (), {
                    'video_id': video_id,
                    'title': '未知标题',
                    'channel_name': '未知频道',
                    'duration': 0
                })()
            
            # 获取完整转录文本
            transcript_data = get_video_transcript_from_file(db, video_id)
            if not transcript_data:
                return {
                    "success": False,
                    "error": f"未找到视频 {video_id} 的转录文本",
                    "full_transcript": "",
                    "video_info": {
                        "video_id": video_id,
                        "title": video_info.title,
                        "channel": video_info.channel_name,
                        "duration": video_info.duration
                    }
                }
            
            # 构建完整转录文本，按时间顺序排列
            transcript_segments = []
            total_segments = len(transcript_data)
            
            for segment in transcript_data:
                segment_start = segment.get('start', 0)
                segment_text = segment.get('text', '').strip()
                
                if segment_text:  # 只包含有文本的片段
                    # 格式化时间戳
                    start_min = int(segment_start // 60)
                    start_sec = int(segment_start % 60)
                    
                    transcript_segments.append({
                        'start': segment_start,
                        'text': segment_text,
                        'formatted_time': f"{start_min:02d}:{start_sec:02d}"
                    })
            
            # 按时间排序
            transcript_segments.sort(key=lambda x: x['start'])
            
            # 构建格式化的完整转录文本
            full_transcript_parts = []
            for segment in transcript_segments:
                full_transcript_parts.append(
                    f"[{segment['formatted_time']}] {segment['text']}"
                )
            
            full_transcript = "\\n".join(full_transcript_parts)
            
            # 计算统计信息
            total_duration = video_info.duration if video_info.duration else 0
            text_segments_count = len(transcript_segments)
            
            return {
                "success": True,
                "full_transcript": full_transcript,
                "video_info": {
                    "video_id": video_id,
                    "title": video_info.title,
                    "channel": video_info.channel_name,
                    "duration": total_duration,
                    "total_segments": total_segments,
                    "text_segments": text_segments_count
                },
                "transcript_stats": {
                    "total_segments": total_segments,
                    "text_segments": text_segments_count,
                    "duration_minutes": round(total_duration / 60, 1) if total_duration else 0,
                    "transcript_length": len(full_transcript)
                }
            }
            
        finally:
            db.close()
            
    except Exception as e:
        return {
            "success": False,
            "error": f"获取完整转录文本失败: {str(e)}",
            "full_transcript": "",
            "video_info": {}
        }


def answer_full_video_question(request: FullVideoTranscriptRequest) -> FullVideoTranscriptResponse:
    """
    基于完整视频转录文本回答用户问题
    
    Args:
        request: 包含视频ID和问题的请求
    
    Returns:
        包含答案的响应
    """
    try:
        # 获取完整转录文本
        transcript_result = get_full_video_transcript(request.video_id)
        
        if not transcript_result["success"]:
            return FullVideoTranscriptResponse(
                success=False,
                full_transcript="",
                answer="",
                video_info={},
                error=transcript_result["error"]
            )
        
        full_transcript = transcript_result["full_transcript"]
        video_info = transcript_result["video_info"]
        transcript_stats = transcript_result.get("transcript_stats", {})
        
        # 检查转录文本长度，如果太长需要处理
        max_context_length = 20000  # 控制上下文长度
        if len(full_transcript) > max_context_length:
            # 截取前部分并添加说明
            truncated_transcript = full_transcript[:max_context_length]
            last_newline = truncated_transcript.rfind('\\n')
            if last_newline > 0:
                truncated_transcript = truncated_transcript[:last_newline]
            
            full_transcript = truncated_transcript + "\\n\\n[注意: 转录文本过长，已截取前半部分用于分析]"
        
        # 使用OpenAI模型分析并回答问题
        model = OpenAIChat(id="gpt-4o")
        
        # 构建分析prompt
        analysis_prompt = f"""
你是一个专业的视频内容分析助手。用户正在询问关于整个YouTube视频的问题。

**视频信息:**
- 视频ID: {request.video_id}
- 标题: {video_info.get('title', '未知')}
- 频道: {video_info.get('channel', '未知')}
- 时长: {transcript_stats.get('duration_minutes', 0)} 分钟
- 转录片段数: {transcript_stats.get('text_segments', 0)}

**完整视频转录文本:**
{full_transcript}

**用户问题:**
{request.question}

请基于提供的完整视频转录文本，全面回答用户的问题。注意：

1. **全局分析**: 从整个视频的角度分析问题，不局限于特定时间点
2. **引用时间戳**: 当引用具体内容时，请标注相关的时间点 [MM:SS]
3. **结构化回答**: 如果问题涉及多个方面，请分点回答
4. **关键信息提取**: 突出视频中与问题相关的核心内容
5. **诚实回答**: 如果转录文本中没有足够信息，请诚实说明
6. **总结性观点**: 如果适合，可以提供对整个视频主题的总结

请提供详细、有用的回答:
"""
        
        # 获取AI回答
        try:
            from agno.models.message import Message
            
            # 创建消息对象
            message = Message(role="user", content=analysis_prompt)
            response = model.response([message])
            
            if hasattr(response, 'content'):
                answer = response.content
            elif hasattr(response, 'get_content_as_string'):
                answer = response.get_content_as_string()
            else:
                answer = str(response)
                
        except Exception as model_error:
            # 如果OpenAI调用失败，返回基础分析
            print(f"OpenAI调用失败: {model_error}")
            answer = f"""基于视频《{video_info.get('title', '未知')}》的完整转录内容分析：

问题: {request.question}

转录文本概览:
- 视频时长: {transcript_stats.get('duration_minutes', 0)} 分钟  
- 文本片段: {transcript_stats.get('text_segments', 0)} 个

完整转录内容:
{full_transcript}

请根据上述完整转录内容自行分析回答问题。由于AI服务暂时不可用，建议您查看转录文本中的相关部分。"""
        
        return FullVideoTranscriptResponse(
            success=True,
            full_transcript=full_transcript,
            answer=answer,
            video_info=video_info
        )
        
    except Exception as e:
        return FullVideoTranscriptResponse(
            success=False,
            full_transcript="",
            answer="",
            video_info={},
            error=f"处理问题失败: {str(e)}"
        )


def get_full_video_qa_agent(
    model_id: str = "gpt-4o",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """
    创建完整视频问答Agent
    
    Args:
        model_id: OpenAI模型ID
        user_id: 用户ID
        session_id: 会话ID
        debug_mode: 调试模式
    
    Returns:
        配置好的完整视频问答Agent
    """
    return Agent(
        name="Full Video Q&A Agent",
        agent_id="full_video_qa_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        tools=[],
        # Agent描述
        description=dedent("""\
            你是FullVideoQA，一个专门分析YouTube视频完整内容并回答用户问题的智能助手。
            
            你可以帮助用户理解整个视频的内容，回答关于视频主题、结构、关键观点的问题，并提供全面的分析。
        """),
        # Agent指令
        instructions=dedent("""\
            作为FullVideoQA，你的主要任务是帮助用户理解YouTube视频的完整内容并回答他们关于整个视频的问题。

            **工作流程：**
            
            1. **理解用户请求**
               - 识别用户提供的视频ID
               - 理解用户关于整个视频的问题
               - 确定问题的范围和深度
            
            2. **全面分析视频内容**
               - 基于完整的转录文本进行分析
               - 识别视频的主要主题和结构
               - 提取关键信息和观点
               - 理解内容的逻辑关系
            
            3. **提供全面回答**
               - 从整体角度回答问题
               - 引用具体的时间点和内容片段
               - 提供结构化的分析
               - 总结关键观点和结论
            
            4. **增强分析深度**
               - 识别视频的主要论点和支撑证据
               - 分析内容的逻辑结构
               - 提供背景信息和解释
               - 建议相关的深入问题
            
            **专业能力：**
            - 内容总结和概括
            - 主题分析和观点提取
            - 结构化信息组织
            - 关键时间点定位
            - 教育内容解释
            
            **回答原则：**
            - 基于完整转录文本回答，不编造信息
            - 引用具体时间戳支持观点
            - 提供结构化和逻辑清晰的回答
            - 如果信息不足，诚实说明限制
            - 关注用户问题的核心需求
            
            **当前用户信息：**
            - 用户ID: {current_user_id}
            - 专注于为用户提供完整、准确的视频内容分析
        """),
        # 启用状态信息
        add_state_in_messages=True,
        # 存储配置
        storage=PostgresAgentStorage(table_name="full_video_qa_agent_sessions", db_url=db_url),
        # 历史记录配置
        add_history_to_messages=True,
        num_history_runs=3,
        read_chat_history=True,
        # 记忆配置
        memory=Memory(
            model=OpenAIChat(id=model_id),
            db=PostgresMemoryDb(table_name="user_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # 格式化设置
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )