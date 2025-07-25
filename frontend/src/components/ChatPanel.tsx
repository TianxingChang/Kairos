"use client";

import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { MessageCircle, NotebookPen, ArrowUp, AtSign } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppStore } from "@/store";
import { useChat, useAutoResize, useScrollToBottom } from "@/hooks";
import { ContextSelector } from "./ContextSelector";
import { LoadingDots } from "./ui/loading-dots";

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
    setCurrentMode,
    contextMenuOpen,
    setContextMenuOpen,
    toggleContextMenu,
    currentVideo,
    selectedContexts,
    addContext,
  } = useAppStore();

  // 使用hooks
  const { isSending, sendToWebAgent } = useChat();

  // 记录加载开始时间
  useEffect(() => {
    if (isSending && !loadingStartTimeRef.current) {
      loadingStartTimeRef.current = new Date();
    } else if (!isSending) {
      loadingStartTimeRef.current = null;
    }
  }, [isSending]);
  const messagesEndRef = useScrollToBottom<HTMLDivElement>({
    dependencies: [messages, isSending, mounted],
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
    if (!chatInput.trim() || isSending) return;

    const userMessage = chatInput.trim();
    setChatInput("");

    try {
      // 默认使用 web search agent
      await sendToWebAgent(userMessage);
    } catch (error) {
      console.error("Error sending message:", error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Card className="h-full flex flex-col">
      {/* 头部切换按钮 */}
      <div className="flex border-b">
        <Button
          variant={currentMode === "chat" ? "default" : "ghost"}
          className="flex-1 rounded-none"
          onClick={() => setCurrentMode("chat")}
        >
          <MessageCircle className="w-4 h-4 mr-2" />
          提问
        </Button>
        <Button
          variant={currentMode === "notes" ? "default" : "ghost"}
          className="flex-1 rounded-none"
          onClick={() => setCurrentMode("notes")}
        >
          <NotebookPen className="w-4 h-4 mr-2" />
          笔记
        </Button>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {currentMode === "chat" ? (
          <>
            {/* 聊天消息区域 */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <AnimatePresence>
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                    className={`flex ${message.isUser ? "justify-end" : "justify-start"}`}
                  >
                    <motion.div
                      initial={{ scale: 0.8 }}
                      animate={{ scale: 1 }}
                      transition={{ duration: 0.2, delay: 0.1 }}
                      className={`max-w-[80%] min-w-[120px] rounded-lg px-3 py-2 ${
                        message.isUser ? "bg-primary text-primary-foreground" : "bg-muted"
                      }`}
                    >
                      <p className="text-sm break-words whitespace-pre-wrap leading-relaxed">
                        {message.content}
                      </p>
                      <p className="text-xs opacity-70 mt-1">
                        {mounted ? message.timestamp.toLocaleTimeString() : ""}
                      </p>
                    </motion.div>
                  </motion.div>
                ))}

                {/* 加载消息 */}
                {isSending && (
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

            <Separator />

            {/* 输入区域 */}
            <div className="p-4 border-t bg-background/95 backdrop-blur-sm">
              {/* Context 选择器和显示 */}
              <div className="relative mb-3">
                <ContextSelector isOpen={contextMenuOpen} setIsOpen={setContextMenuOpen} />
              </div>

              {/* 输入框容器 */}
              <div className="relative bg-background border border-border/50 rounded-2xl focus-within:border-primary/50 transition-colors shadow-sm">
                {/* @ 按钮 */}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 absolute left-2 top-1/2 -translate-y-1/2 z-10"
                  onClick={toggleContextMenu}
                >
                  <AtSign className="w-4 h-4" />
                </Button>

                <Textarea
                  ref={textareaRef}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="询问关于这个视频的问题..."
                  className="min-h-[44px] max-h-[72px] resize-none border-0 bg-transparent pl-12 py-3 pr-12 focus-visible:ring-0 focus-visible:ring-offset-0 scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent"
                  style={{ height: "44px" }}
                />
                <motion.div
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  whileHover={!isSending ? { scale: 1.05 } : {}}
                  whileTap={!isSending ? { scale: 0.95 } : {}}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  <Button
                    onClick={handleSendMessage}
                    disabled={!chatInput.trim() || isSending}
                    className={`h-8 w-14 rounded-xl border-0 transition-all duration-200 ${
                      chatInput.trim() && !isSending
                        ? "bg-[#5B9BD5] hover:bg-[#4A8BC2] shadow-md"
                        : "bg-gray-300"
                    } disabled:cursor-not-allowed`}
                  >
                    {isSending ? (
                      <LoadingDots size="sm" className="text-white" />
                    ) : (
                      <ArrowUp
                        className={`w-4 h-4 ${
                          chatInput.trim() && !isSending ? "text-white" : "text-gray-500"
                        }`}
                      />
                    )}
                  </Button>
                </motion.div>
              </div>
            </div>
          </>
        ) : (
          /* 笔记区域 */
          <div className="flex-1 p-4">
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="在这里记录你的笔记..."
              className="h-full resize-none"
            />
          </div>
        )}
      </div>
    </Card>
  );
}
