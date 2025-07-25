"use client";

import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { MessageCircle, NotebookPen, ArrowUp, AtSign, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppStore } from "@/store/appStore";
import { ContextSelector } from "./ContextSelector";

export function ChatPanel() {
  const [chatInput, setChatInput] = useState("");
  const [mounted, setMounted] = useState(false);
  const [contextMenuOpen, setContextMenuOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    addMessage,
    notes,
    setNotes,
    currentMode,
    setCurrentMode,
    currentVideoTime,
    setCurrentVideoTime,
  } = useAppStore();

  useEffect(() => {
    setMounted(true);

    // 模拟视频播放时间更新
    const interval = setInterval(() => {
      setCurrentVideoTime(currentVideoTime + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [currentVideoTime, setCurrentVideoTime]);

  // 自动调整textarea高度
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const scrollHeight = textarea.scrollHeight;
      const maxHeight = 72; // 约3行的高度
      textarea.style.height = Math.min(scrollHeight, maxHeight) + "px";
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [chatInput]);

  // 自动滚动到最新消息
  useEffect(() => {
    if (messagesEndRef.current && mounted) {
      messagesEndRef.current.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    }
  }, [messages, mounted]);

  const handleSendMessage = async () => {
    if (!chatInput.trim() || isSending) return;

    setIsSending(true);
    const userMessage = chatInput.trim();

    addMessage({
      content: userMessage,
      isUser: true,
    });

    setChatInput("");

    try {
      const agentType = webSearchEnabled ? 'web_agent' : 'agno_assist';
      const response = await fetch(`/api/v1/agents/${agentType}/runs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          stream: false,
          model: 'gpt-4.1',
          user_id: 'user_1',
          session_id: 'session_1'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const aiResponse = await response.text();
      
      addMessage({
        content: aiResponse,
        isUser: false,
      });
    } catch (error) {
      console.error('Error sending message:', error);
      addMessage({
        content: '抱歉，发生了错误。请稍后再试。',
        isUser: false,
      });
    } finally {
      setIsSending(false);
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
          聊天
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
                    className={`flex ${
                      message.isUser ? "justify-end" : "justify-start"
                    }`}
                  >
                    <motion.div
                      initial={{ scale: 0.8 }}
                      animate={{ scale: 1 }}
                      transition={{ duration: 0.2, delay: 0.1 }}
                      className={`max-w-[80%] min-w-[120px] rounded-lg px-3 py-2 ${
                        message.isUser
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
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
              </AnimatePresence>
              {/* 滚动目标 */}
              <div ref={messagesEndRef} />
            </div>

            <Separator />

            {/* 输入区域 */}
            <div className="p-4 border-t bg-background/95 backdrop-blur-sm">
              {/* Web Search 开关 */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <Button
                    variant={webSearchEnabled ? "default" : "outline"}
                    size="sm"
                    onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                    className="h-8"
                  >
                    <Search className="w-4 h-4 mr-1" />
                    Web搜索
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    {webSearchEnabled ? "启用网络搜索" : "使用本地助手"}
                  </span>
                </div>
              </div>

              {/* Context 选择器和显示 */}
              <div className="relative">
                <ContextSelector
                  isOpen={contextMenuOpen}
                  setIsOpen={setContextMenuOpen}
                />
              </div>

              {/* 输入框容器 */}
              <div className="relative bg-background border border-border/50 rounded-2xl focus-within:border-primary/50 transition-colors shadow-sm">
                {/* @ 按钮 */}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 absolute left-2 top-1/2 -translate-y-1/2 z-10"
                  onClick={() => setContextMenuOpen(!contextMenuOpen)}
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
                      chatInput.trim()
                        ? "bg-[#5B9BD5] hover:bg-[#4A8BC2] shadow-md"
                        : "bg-gray-300"
                    } disabled:cursor-not-allowed`}
                  >
                    <ArrowUp
                      className={`w-4 h-4 ${
                        chatInput.trim() ? "text-white" : "text-gray-500"
                      }`}
                    />
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
