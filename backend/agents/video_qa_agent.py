from textwrap import dedent
from typing import Optional, Dict

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from pydantic import BaseModel

from db.session import db_url


class VideoTranscriptRequest(BaseModel):
    """视频转录文本请求模型"""
    video_id: str
    timestamp: float  # 时间点（秒）
    question: str


class VideoTranscriptResponse(BaseModel):
    """视频转录文本响应模型"""
    success: bool
    context_transcript: str
    answer: str
    timestamp_range: Dict[str, float]
    error: Optional[str] = None


def get_video_transcript_context(video_id: str, timestamp: float) -> Dict:
    """
    获取视频在指定时间点附近的转录文本上下文
    
    Args:
        video_id: YouTube视频ID
        timestamp: 时间点（秒）
    
    Returns:
        包含上下文转录文本的字典
    """
    try:
        from db.session import SessionLocal
        from db.youtube_service import get_video_transcript_from_file
        
        # 创建数据库会话
        db = SessionLocal()
        try:
            # 获取完整转录文本
            transcript_data = get_video_transcript_from_file(db, video_id)
            if not transcript_data:
                return {
                    "success": False,
                    "error": f"未找到视频 {video_id} 的转录文本",
                    "context_transcript": "",
                    "timestamp_range": {}
                }
            
            # 定义时间范围：前20秒，后5秒
            start_time = max(0, timestamp - 20)
            end_time = timestamp + 5
            
            # 筛选时间范围内的转录片段
            context_segments = []
            for segment in transcript_data:
                segment_start = segment.get('start', 0)
                segment_end = segment_start + segment.get('duration', 0)
                
                # 如果片段与时间范围有重叠，就包含进来
                if segment_start <= end_time and segment_end >= start_time:
                    context_segments.append({
                        'start': segment_start,
                        'end': segment_end,
                        'text': segment.get('text', ''),
                        'duration': segment.get('duration', 0)
                    })
            
            # 构建上下文文本
            if not context_segments:
                return {
                    "success": False,
                    "error": f"在时间点 {timestamp}s 附近未找到转录文本",
                    "context_transcript": "",
                    "timestamp_range": {"start": start_time, "end": end_time}
                }
            
            # 按时间排序并构建连续文本
            context_segments.sort(key=lambda x: x['start'])
            context_text_parts = []
            
            for segment in context_segments:
                # 格式化时间戳
                start_min = int(segment['start'] // 60)
                start_sec = int(segment['start'] % 60)
                
                context_text_parts.append(
                    f"[{start_min:02d}:{start_sec:02d}] {segment['text']}"
                )
            
            context_transcript = "\\n".join(context_text_parts)
            
            return {
                "success": True,
                "context_transcript": context_transcript,
                "timestamp_range": {
                    "start": start_time,
                    "end": end_time,
                    "target": timestamp
                },
                "segments_count": len(context_segments)
            }
            
        finally:
            db.close()
            
    except Exception as e:
        return {
            "success": False,
            "error": f"获取转录文本失败: {str(e)}",
            "context_transcript": "",
            "timestamp_range": {}
        }


def answer_video_question(request: VideoTranscriptRequest) -> VideoTranscriptResponse:
    """
    基于视频转录文本回答用户问题
    
    Args:
        request: 包含视频ID、时间点和问题的请求
    
    Returns:
        包含答案的响应
    """
    try:
        # 获取上下文转录文本
        context_result = get_video_transcript_context(request.video_id, request.timestamp)
        
        if not context_result["success"]:
            return VideoTranscriptResponse(
                success=False,
                context_transcript="",
                answer="",
                timestamp_range={},
                error=context_result["error"]
            )
        
        context_transcript = context_result["context_transcript"]
        timestamp_range = context_result["timestamp_range"]
        
        # 使用OpenAI模型分析并回答问题
        model = OpenAIChat(id="gpt-4o")
        
        # 构建分析prompt
        analysis_prompt = f"""
你是一个视频内容分析助手。用户正在观看一个YouTube视频，并在特定时间点提出了问题。

**视频信息:**
- 视频ID: {request.video_id}
- 用户关注的时间点: {request.timestamp}秒 ({int(request.timestamp//60):02d}:{int(request.timestamp%60):02d})

**相关转录文本上下文 (时间范围: {timestamp_range.get('start', 0):.1f}s - {timestamp_range.get('end', 0):.1f}s):**
{context_transcript}

**用户问题:**
{request.question}

请基于提供的转录文本上下文，准确回答用户的问题。注意：
1. 重点关注用户指定时间点附近的内容
2. 如果问题与转录文本相关，请引用具体的时间点和内容
3. 如果转录文本中没有足够信息回答问题，请诚实说明
4. 保持回答简洁明了，重点突出

回答:
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
            answer = f"基于时间点 {request.timestamp}秒 ({int(request.timestamp//60):02d}:{int(request.timestamp%60):02d}) 的转录内容:\\n\\n{context_transcript}\\n\\n针对问题 '{request.question}'，请根据上述转录内容自行分析。"
        
        return VideoTranscriptResponse(
            success=True,
            context_transcript=context_transcript,
            answer=answer,
            timestamp_range=timestamp_range
        )
        
    except Exception as e:
        return VideoTranscriptResponse(
            success=False,
            context_transcript="",
            answer="",
            timestamp_range={},
            error=f"处理问题失败: {str(e)}"
        )


def get_video_qa_agent(
    model_id: str = "gpt-4o",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """
    创建视频问答Agent
    
    Args:
        model_id: OpenAI模型ID
        user_id: 用户ID
        session_id: 会话ID
        debug_mode: 调试模式
    
    Returns:
        配置好的视频问答Agent
    """
    return Agent(
        name="Video Q&A Agent",
        agent_id="video_qa_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        # 暂时不使用自定义工具，改为在instructions中说明如何处理
        tools=[],
        # Agent描述
        description=dedent("""\
            你是VideoQA，一个专门分析YouTube视频内容并回答用户时间点相关问题的智能助手。
            
            你可以帮助用户理解视频在特定时间点的内容，回答相关问题，并提供准确的上下文信息。
        """),
        # Agent指令
        instructions=dedent("""\
            作为VideoQA，你的主要任务是帮助用户理解YouTube视频内容并回答他们在特定时间点的问题。

            **工作流程：**
            
            1. **理解用户请求**
               - 识别用户提供的视频ID (例如: dQw4w9WgXcQ)
               - 确定用户关注的时间点（秒数或MM:SS格式）
               - 理解用户的具体问题
            
            2. **处理视频问答**
               - 当用户提供视频ID和时间点时，告知用户需要使用API接口
               - 建议用户使用 /v1/video-qa/direct 接口进行查询
               - 或者如果你已经有视频的转录文本，直接基于提供的内容回答
            
            3. **提供准确回答**
               - 基于转录文本上下文回答问题
               - 引用具体的时间点和内容
               - 如果信息不足，诚实说明限制
               - 保持回答简洁明了
            
            4. **增强用户体验**
               - 提供时间戳引用，方便用户定位
               - 建议相关的后续问题
               - 如果需要，解释视频内容的背景
            
            **重要提醒：**
            - 始终基于实际的转录文本内容回答
            - 不要编造视频中没有的信息
            - 如果转录文本质量差或缺失，要诚实告知
            - 重点关注用户指定的时间点附近内容
            
            **当前用户信息：**
            - 用户ID: {current_user_id}
            - 如果用户分享姓名，记录到记忆中以便个性化服务
        """),
        # 启用状态信息
        add_state_in_messages=True,
        # 存储配置
        storage=PostgresAgentStorage(table_name="video_qa_agent_sessions", db_url=db_url),
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