import json
from textwrap import dedent
from typing import Optional

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools import Toolkit
from pydantic import BaseModel, Field

from db.session import db_url
from tools.vtt_parser import VTTTool
from tools.knowledge_extractor import KnowledgeExtractionTool
from tools.simple_database_tool import SimpleDatabaseTool


class TranscriptAnalysisTool(Toolkit):
    """Custom toolkit for transcript analysis."""
    
    def __init__(self):
        self.vtt_tool = VTTTool()
        self.knowledge_tool = KnowledgeExtractionTool()
        self.database_tool = SimpleDatabaseTool()
        
        tools = [self.analyze_transcript, self.analyze_and_store_transcript]
        super().__init__(name="transcript_analyzer", tools=tools)
        
    def analyze_transcript(self, file_path: str) -> str:
        """Analyze a VTT transcript file and return knowledge segments with time ranges.
        
        Args:
            file_path (str): Path to the VTT transcript file to analyze.
            
        Returns:
            str: JSON string containing knowledge segments with time ranges, summary, and metadata.
        """
        try:
            # Step 1: Parse VTT file
            vtt_result = self.vtt_tool.parse_vtt_file(file_path)
            
            if not vtt_result["success"]:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to parse VTT file: {vtt_result['error']}",
                    "knowledge_segments": {},
                    "transcript_summary": "",
                    "total_duration": "00:00:00.000"
                })
            
            # Convert segments data to VTTSegment objects for knowledge extraction
            from tools.vtt_parser import VTTSegment
            segments = []
            for seg_data in vtt_result["segments"]:
                segment = VTTSegment(
                    start_time=seg_data["start_time"],
                    end_time=seg_data["end_time"],
                    text=seg_data["text"],
                    start_seconds=seg_data["start_seconds"],
                    end_seconds=seg_data["end_seconds"]
                )
                segments.append(segment)
            
            # Step 2: Extract knowledge points
            analysis_result = self.knowledge_tool.analyze_transcript(segments)
            
            if not analysis_result["success"]:
                return json.dumps({
                    "success": False,
                    "error": f"Knowledge extraction failed: {analysis_result['error']}",
                    "knowledge_segments": {},
                    "transcript_summary": "",
                    "total_duration": "00:00:00.000"
                })
            
            # Step 3: Format final output
            final_result = self.knowledge_tool.format_for_json_output(analysis_result)
            final_result["success"] = True
            
            return json.dumps(final_result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Unexpected error during transcript analysis: {str(e)}",
                "knowledge_segments": {},
                "transcript_summary": "",
                "total_duration": "00:00:00.000"
            })
    
    def analyze_and_store_transcript(self, file_path: str, domain: str = "深度学习") -> str:
        """Analyze VTT transcript file, extract knowledge segments, and store them in database.
        
        Args:
            file_path (str): Path to the VTT transcript file to analyze.
            domain (str): Knowledge domain for categorization (default: "深度学习").
            
        Returns:
            str: JSON string containing storage results, knowledge points, and video segments.
        """
        return self.database_tool.analyze_and_store_simple(file_path, domain)


def get_transcript_analyzer(
    model = None,
    model_id: str = None,  # 改为None，优先使用传入的model
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Create and configure the transcript analyzer agent."""
    # 如果没有提供模型实例，则调用selector来获取正确的模型
    if model is None:
        from agents.selector import _get_model
        model = _get_model(model_id)
    
    return Agent(
        name="Transcript Analyzer",
        agent_id="transcript_analyzer",
        user_id=user_id,
        session_id=session_id,
        model=model,
        # Tools available to the agent
        tools=[TranscriptAnalysisTool()],
        # Description of the agent
        description=dedent("""\
            You are TranscriptMaster, an advanced AI agent specialized in analyzing video transcripts to extract knowledge structures and learning segments.
            
            Your goal is to help educators and learners understand the knowledge flow in educational videos by identifying distinct learning concepts and their time boundaries.
        """),
        # Instructions for the agent
        instructions=dedent("""\
            As TranscriptMaster, your mission is to analyze video transcript files and extract meaningful knowledge segments. Follow this systematic approach:

            1. **Understand the Request:**
               - Identify if the user wants to analyze a specific VTT transcript file
               - Clarify the file path if not clearly provided
               - Understand any specific analysis requirements (subject area, detail level, etc.)

            2. **File Analysis Process:**
               - Use the `analyze_transcript` tool for basic analysis without database storage
               - Use the `analyze_and_store_transcript` tool to process VTT files AND store results in database
               - The tools will parse the VTT format and extract timing information
               - Knowledge points will be identified using advanced content analysis
               - Each knowledge segment will be mapped to specific time ranges
               - Database storage includes knowledge point reuse and video segment creation

            3. **Result Interpretation:**
               - Review the extracted knowledge segments for logical flow
               - Ensure time boundaries make sense and don't overlap inappropriately
               - Verify that knowledge points are meaningful and well-described
               - Check that the summary accurately reflects the content

            4. **Response Format:**
               - Present results in a clear, structured format
               - Include the JSON output with knowledge segments and time ranges
               - Provide context about the analysis (subject area, difficulty level, main topics)
               - Explain any limitations or areas where manual review might be helpful

            5. **Quality Assurance:**
               - If analysis fails or produces incomplete results, explain the limitations
               - Suggest alternative approaches or manual verification steps
               - Provide guidance on how to use the extracted segments effectively

            6. **Educational Context:**
               - Consider the educational value of each knowledge segment
               - Highlight important concepts that require more attention
               - Suggest learning pathways based on the knowledge structure
               - Identify prerequisite knowledge or related concepts

            **Expected Output Format:**
            ```json
            {
              "knowledge_segments": {
                "概念名称": {
                  "description": "详细描述",
                  "start": "00:00:12.500",
                  "end": "00:00:34.240",
                  "importance_level": 4,
                  "keywords": ["关键词1", "关键词2"],
                  "related_concepts": ["相关概念1", "相关概念2"]
                }
              },
              "transcript_summary": "整体内容摘要",
              "total_duration": "01:23:45.000",
              "subject_area": "学科领域",
              "difficulty_level": "难度等级",
              "main_topics": ["主要话题列表"]
            }
            ```

            **Common Use Cases:**
            - Educational video segmentation for online learning platforms
            - Creating chapter markers for long-form educational content
            - Generating study guides with time-based references
            - Analyzing lecture content for curriculum development
            - Supporting accessibility through structured content navigation

            Additional Information:
            - Always prioritize educational value and learning outcomes in your analysis
            - Be prepared to handle various languages and subject domains
            - Maintain accuracy while providing actionable insights\
        """),
        # Disable state formatting to prevent recursion issues
        add_state_in_messages=False,
        # -*- Storage -*-
        # Storage chat history and session state in a Postgres table
        storage=PostgresAgentStorage(table_name="transcript_analyzer_sessions", db_url=db_url),
        # -*- History -*-
        # Send the last 3 messages from the chat history
        add_history_to_messages=True,
        num_history_runs=3,
        # Add a tool to read the chat history if needed
        read_chat_history=True,
        # -*- Memory -*-
        # Enable agentic memory where the Agent can personalize responses to the user
        memory=Memory(
            model=model, # 使用传入的模型实例
            db=PostgresMemoryDb(table_name="user_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # -*- Other settings -*-
        # Format responses using markdown
        markdown=True,
        # Add the current date and time to the instructions
        add_datetime_to_instructions=True,
        # Show debug logs
        debug_mode=debug_mode,
    )