"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ArrowUp, AtSign } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppStore } from "@/store";
import { useChat, useAutoResize, useScrollToBottom } from "@/hooks";
import { ContextSelector } from "./ContextSelector";
import { LoadingDots } from "./ui/loading-dots";
import { ChatMessage } from "./ChatMessage";
import { TiptapEditor } from "./TiptapEditor";
import { useCallback } from "react";

export function ChatPanel() {
  const [chatInput, setChatInput] = useState("");
  const [mounted, setMounted] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const loadingStartTimeRef = useRef<Date | null>(null);

  // 获取store状态
  const {
    messages,
    notes,
    setNotes,
    currentMode,
    contextMenuOpen,
    setContextMenuOpen,
    toggleContextMenu,
    currentVideo,
    currentVideoTime,
    selectedContexts,
    addContext,
    addMessage,
  } = useAppStore();

  // 使用hooks
  const { isSending, sendToWebAgent } = useChat();
  
  // 本地状态管理
  const [isVideoQASending, setIsVideoQASending] = useState(false);
  
  // 统一的发送状态
  const isAnySending = isSending || isVideoQASending;

  // 记录加载开始时间
  useEffect(() => {
    if (isAnySending && !loadingStartTimeRef.current) {
      loadingStartTimeRef.current = new Date();
    } else if (!isAnySending) {
      loadingStartTimeRef.current = null;
    }
  }, [isAnySending]);
  const messagesEndRef = useScrollToBottom<HTMLDivElement>({
    dependencies: [messages, isAnySending, mounted],
  });
  useAutoResize(textareaRef, chatInput);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 默认添加当前视频时间点上下文（仅在首次初始化时）
  useEffect(() => {
    // 只在首次挂载且没有初始化过且没有选择任何上下文时添加
    if (mounted && !hasInitialized && selectedContexts.length === 0) {
      const defaultContext = {
        id: "current-video-time",
        type: "video" as const,
        title: `视频时间点提问`, // 与ContextSelector显示保持一致
        description: currentVideo.title,
        timestamp: 0, // 初始为 0，会动态更新
      };
      addContext(defaultContext);
      setHasInitialized(true);
    }
  }, [mounted, hasInitialized, selectedContexts.length, currentVideo.title, addContext]);

  const handleSendMessage = async () => {
    if (!chatInput.trim() || isAnySending) return;

    const userMessage = chatInput.trim();
    setChatInput("");

    try {
      // 检查是否有视频相关上下文（时间点或完整视频）
      const videoTimeContext = selectedContexts.find(ctx => 
        ctx.type === 'video' && ctx.timestamp !== undefined
      );
      
      const fullVideoContext = selectedContexts.find(ctx => 
        ctx.type === 'video' && ctx.id === 'full-video'
      );

      if ((videoTimeContext || fullVideoContext) && currentVideo.videoId) {
        // 使用视频QA功能
        if (videoTimeContext) {
          await handleVideoQA(userMessage, videoTimeContext);
        } else if (fullVideoContext) {
          await handleFullVideoQA(userMessage, fullVideoContext);
        }
      } else {
        // 默认使用 web search agent
        await sendToWebAgent(userMessage);
      }
    } catch (error) {
      console.error("Error sending message:", error);
    }
  };

  const handleVideoQA = async (question: string, context: any) => {
    // 使用一个本地状态来管理video QA的loading，但这里我们直接使用useChat的isSending
    // 因为我们需要修改useChat来支持自定义的发送逻辑
    
    // 方案1: 创建一个包装函数来统一处理状态
    return await sendVideoQAMessage(question, context);
  };

  const handleFullVideoQA = async (question: string, context: any) => {
    // 处理完整视频问答
    return await sendFullVideoQAMessage(question, context);
  };

  // 使用useChat模式的video QA发送函数
  const sendVideoQAMessage = useCallback(async (question: string, context: any) => {
    if (isAnySending) return;

    setIsVideoQASending(true);

    try {
      const { videoQAService } = await import('@/services/videoQAService');
      
      const timestamp = context.timestamp || currentVideoTime || 0;
      
      // 添加用户消息
      addMessage({
        content: `@视频时间点(${formatTime(timestamp)}) ${question}`,
        isUser: true,
      });

      const response = await videoQAService.askQuestion({
        video_id: currentVideo.videoId,
        timestamp: timestamp,
        question: question,
        user_id: 'frontend_user',
        context_before: 20,
        context_after: 5,
      });

      if (response.success) {
        // 添加AI回复
        addMessage({
          content: response.answer,
          isUser: false,
        });
      } else {
        throw new Error(response.error || '视频问答失败');
      }
    } catch (error) {
      console.error('Video QA failed:', error);
      
      // 添加错误消息
      addMessage({
        content: '抱歉，视频问答失败。请稍后再试。',
        isUser: false,
      });
    } finally {
      setIsVideoQASending(false);
    }
  }, [isAnySending, addMessage, currentVideoTime, currentVideo.videoId]);

  // 完整视频QA发送函数
  const sendFullVideoQAMessage = useCallback(async (question: string, context: any) => {
    if (isAnySending) return;

    setIsVideoQASending(true);

    try {
      const { videoQAService } = await import('@/services/videoQAService');
      
      // 添加用户消息
      addMessage({
        content: `@完整视频 ${question}`,
        isUser: true,
      });

      // 使用askFullVideoQuestionWithAgent来获得更好的分析能力
      const response = await videoQAService.askFullVideoQuestionWithAgent({
        video_id: currentVideo.videoId,
        question: question,
        user_id: 'frontend_user',
        session_id: `session_${Date.now()}`,
      });

      if (response.success) {
        // 添加AI回复
        addMessage({
          content: response.answer,
          isUser: false,
        });
      } else {
        throw new Error(response.error || '完整视频问答失败');
      }
    } catch (error) {
      console.error('Full Video QA failed:', error);
      
      // 添加错误消息
      addMessage({
        content: '抱歉，完整视频问答失败。请稍后再试。',
        isUser: false,
      });
    } finally {
      setIsVideoQASending(false);
    }
  }, [isAnySending, addMessage, currentVideo.videoId]);

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 截图功能
  const handleScreenshot = useCallback(async (): Promise<string> => {
    if (typeof window !== "undefined" && window.videoPlayer) {
      try {
        return await window.videoPlayer.captureFrame();
      } catch (error) {
        console.error("截图失败:", error);
        throw error;
      }
    } else {
      throw new Error("视频播放器未准备就绪");
    }
  }, []);

  return (
    <div className="h-full flex flex-col bg-background border-l max-h-full overflow-hidden">
      {currentMode === "chat" ? (
        <>
          {/* 聊天消息区域 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <AnimatePresence>
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} mounted={mounted} />
              ))}

              {/* 加载消息 */}
              {isAnySending && (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="flex justify-start"
                >
                  <motion.div
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.2, delay: 0.1 }}
                    className="max-w-[80%] min-w-[120px] rounded-lg px-3 py-2 bg-muted"
                  >
                    <div className="flex items-center space-x-2">
                      <LoadingDots size="sm" className="text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">正在思考...</span>
                    </div>
                    <p className="text-xs opacity-70 mt-1">
                      {mounted && loadingStartTimeRef.current
                        ? loadingStartTimeRef.current.toLocaleTimeString()
                        : ""}
                    </p>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
            {/* 滚动目标 */}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div className="p-4 bg-background/95 backdrop-blur-sm">
            {/* Cursor风格完整输入框 */}
            <div className="relative bg-background border border-border rounded-lg transition-all duration-200 shadow-sm hover:shadow-md">
              {/* 上方工具栏 */}
              <div className="flex items-center gap-3 px-3 pt-3 pb-2 min-h-[32px]">
                {/* @ 按钮 */}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 rounded-md hover:bg-muted flex-shrink-0"
                  onClick={toggleContextMenu}
                >
                  <AtSign className="w-4 h-4" />
                </Button>

                {/* Context 选择器显示区域 */}
                <div className="relative flex-1 flex items-center">
                  <ContextSelector isOpen={contextMenuOpen} setIsOpen={setContextMenuOpen} />
                </div>
              </div>

              {/* 轻微分割线 */}
              <div className="h-px bg-border/30 mx-3" />

              {/* 输入框区域 */}
              <div className="flex items-end gap-3 px-3 pb-3 pt-2 border-0 shadow-none">
                {/* 输入框 */}
                <div className="flex-1 relative border-0 shadow-none">
                  <Textarea
                    ref={textareaRef}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="询问关于这个视频的问题..."
                    className="w-full min-h-[24px] max-h-[120px] resize-none border-none outline-none bg-transparent p-0 text-sm placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 focus:border-none focus:outline-none focus:shadow-none hover:border-none hover:shadow-none shadow-none scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent leading-6"
                    style={{
                      height: "24px",
                      border: "none",
                      outline: "none",
                      boxShadow: "none",
                      borderRadius: "0",
                    }}
                  />
                </div>

                {/* 发送按钮 */}
                <motion.div
                  className="flex-shrink-0"
                  whileHover={!isAnySending ? { scale: 1.02 } : {}}
                  whileTap={!isAnySending ? { scale: 0.98 } : {}}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                >
                  <Button
                    onClick={handleSendMessage}
                    disabled={!chatInput.trim() || isAnySending}
                    size="sm"
                    className={`h-7 w-7 p-0 rounded-md border-0 transition-all duration-150 ${
                      chatInput.trim() && !isAnySending
                        ? "bg-[#5B9BD5] hover:bg-[#4A8BC2] shadow-sm"
                        : "bg-gray-300 hover:bg-gray-400"
                    } disabled:cursor-not-allowed`}
                  >
                    {isAnySending ? (
                      <LoadingDots size="sm" className="text-white" />
                    ) : (
                      <ArrowUp
                        className={`w-4 h-4 ${
                          chatInput.trim() && !isAnySending ? "text-white" : "text-gray-500"
                        }`}
                      />
                    )}
                  </Button>
                </motion.div>
              </div>
            </div>
          </div>
        </>
      ) : (
        /* 笔记区域 */
        <div className="flex-1 min-h-0 overflow-hidden">
          <TiptapEditor
            content={notes}
            onChange={setNotes}
            placeholder="开始写作，按空格键使用AI，按 / 键使用命令"
            className="h-full"
            onScreenshot={handleScreenshot}
          />
        </div>
      )}
    </div>
  );
}
