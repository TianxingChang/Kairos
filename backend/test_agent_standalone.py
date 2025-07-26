#!/usr/bin/env python3
"""
独立测试完整视频问答Agent功能（不依赖数据库）
"""

from agents.full_video_qa_agent import get_full_video_qa_agent, answer_full_video_question, FullVideoTranscriptRequest

def test_full_video_qa_agent_standalone():
    """测试Full Video QA Agent的独立功能"""
    print("=== 测试Full Video QA Agent（独立模式）===")
    
    try:
        # 创建Agent
        agent = get_full_video_qa_agent(
            user_id="test_user",
            session_id="test_session",
            debug_mode=True
        )
        
        print("✅ Agent创建成功!")
        print(f"Agent名称: {agent.name}")
        print(f"Agent ID: {agent.agent_id}")
        
        # 模拟一个包含转录文本的消息
        test_message = """
我正在分析一个YouTube视频，想要询问关于整个视频的问题。

**视频信息:**
- 标题: Never Gonna Give You Up
- 频道: RickAstleyVEVO
- 时长: 212 秒
- 转录片段数: 50

**完整视频转录文本:**
[00:00] We're no strangers to love
[00:05] You know the rules and so do I
[00:10] A full commitment's what I'm thinking of
[00:15] You wouldn't get this from any other guy
[00:20] I just wanna tell you how I'm feeling
[00:25] Gotta make you understand
[00:30] Never gonna give you up
[00:32] Never gonna let you down
[00:35] Never gonna run around and desert you

**我的问题:**
这个视频的主要主题是什么？歌词表达了什么情感？

请基于上述完整的视频转录文本，全面回答我的问题。
"""
        
        # 获取Agent回答
        print("\n发送消息给Agent...")
        response = agent.run(test_message)
        
        # 提取回答
        if hasattr(response, 'content'):
            answer = response.content
        elif hasattr(response, 'get_content_as_string'):
            answer = response.get_content_as_string()
        else:
            answer = str(response)
        
        print("✅ Agent回答成功!")
        print(f"回答长度: {len(answer)}")
        print(f"回答内容: {answer}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_answer_full_video_question_function():
    """测试answer_full_video_question函数的独立功能"""
    print("\n=== 测试answer_full_video_question函数（模拟数据）===")
    
    try:
        # 创建测试请求
        request = FullVideoTranscriptRequest(
            video_id="test_video_id",
            question="这个视频的主要内容是什么？"
        )
        
        print("✅ 请求对象创建成功!")
        print(f"视频ID: {request.video_id}")
        print(f"问题: {request.question}")
        
        # 注意：这个函数会尝试访问数据库，所以可能会失败
        # 但我们可以看到错误信息来了解问题所在
        result = answer_full_video_question(request)
        
        print(f"函数调用结果: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 函数测试失败（这是预期的，因为没有数据库连接）: {e}")
        return False

if __name__ == "__main__":
    print("开始独立测试Full Video QA Agent功能...")
    print("=" * 60)
    
    # 测试Agent创建和对话
    agent_success = test_full_video_qa_agent_standalone()
    
    # 测试函数调用（可能失败）
    function_success = test_answer_full_video_question_function()
    
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print(f"Agent创建和对话: {'✅ 成功' if agent_success else '❌ 失败'}")
    print(f"函数调用: {'✅ 成功' if function_success else '❌ 失败（预期，因数据库问题）'}")
    
    if agent_success:
        print("\n✅ Full Video QA Agent核心功能正常!")
        print("Agent可以正确处理包含完整转录文本的对话")
        print("前端可以通过/ask-full-agent端点使用此功能")
    else:
        print("\n❌ Agent功能需要检查")