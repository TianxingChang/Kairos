"use client";

import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { ArrowUp, X, Clock, Bot, AtSign, Video, FileText, BookOpen } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { LoadingDots } from "@/components/ui/loading-dots";
import { useAppStore } from "@/store";
import { useAutoResize } from "@/hooks";
import { aiService } from "@/services/aiService";
import type { ContextItem } from "@/types";

interface AIQueryPanelProps {
  onClose: () => void;
  onInsertResponse: (response: string) => void;
  currentVideoTime?: number;
}

interface Message {
  id: string;
  type: "user" | "ai";
  content: string;
  timestamp?: number;
  createdAt: Date;
}

export function AIQueryPanel({ onClose, onInsertResponse, currentVideoTime }: AIQueryPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [contextMenuOpen, setContextMenuOpen] = useState(false);
  const [selectedContexts, setSelectedContexts] = useState<ContextItem[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);

  // 获取store状态
  const { currentVideo, currentVideoTime: globalVideoTime } = useAppStore();

  // 使用传入的currentVideoTime或全局的currentVideoTime
  const videoTime = currentVideoTime ?? globalVideoTime;

  // 使用自动调整高度的hook
  useAutoResize(inputRef, inputValue);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 点击外部关闭上下文菜单
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
        setContextMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setContextMenuOpen(false);
      }
    }

    if (contextMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [contextMenuOpen]);

  // 监听选中文本作为上下文的事件
  useEffect(() => {
    const handleSelectionContext = (event: CustomEvent) => {
      const { selectedText } = event.detail;

      if (selectedText && selectedText.trim()) {
        // 创建一个选中文本的上下文项
        const selectionContext: ContextItem = {
          id: `selection-${Date.now()}`,
          type: "note",
          title: "选中文本",
          description:
            selectedText.length > 50 ? selectedText.substring(0, 50) + "..." : selectedText,
        };

        // 添加到已选择的上下文中
        setSelectedContexts((prev) => {
          // 先移除之前的选中文本上下文（如果有）
          const filtered = prev.filter((ctx) => !ctx.id.startsWith("selection-"));
          return [...filtered, selectionContext];
        });
      }
    };

    window.addEventListener("add-selection-context", handleSelectionContext as EventListener);

    return () => {
      window.removeEventListener("add-selection-context", handleSelectionContext as EventListener);
    };
  }, []);

  const formatTime = (seconds?: number) => {
    if (!seconds) return "";
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  };

  const getContextIcon = (type: ContextItem["type"]) => {
    switch (type) {
      case "video":
        return <Video className="w-4 h-4" />;
      case "knowledge_point":
        return <BookOpen className="w-4 h-4" />;
      case "note":
        return <FileText className="w-4 h-4" />;
      case "file":
        return <FileText className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const toggleContextMenu = () => {
    setContextMenuOpen(!contextMenuOpen);
  };

  const handleAddContext = (context: ContextItem) => {
    if (!selectedContexts.find((ctx) => ctx.id === context.id)) {
      setSelectedContexts((prev) => [...prev, context]);
    }
    setContextMenuOpen(false);
  };

  const removeContext = (contextId: string) => {
    setSelectedContexts((prev) => prev.filter((ctx) => ctx.id !== contextId));
  };

  const handleJumpToTime = (timestamp: number) => {
    // 使用全局播放器控制方法跳转到指定时间
    if (typeof window !== "undefined" && window.videoPlayer) {
      window.videoPlayer.seekTo(timestamp);
    }
  };

  // 可用的上下文选项
  const availableContexts: ContextItem[] = [
    {
      id: "current-video-time",
      type: "video",
      title: `视频时间点写作`,
      description: currentVideo.title,
      timestamp: videoTime,
    },
    {
      id: "full-video",
      type: "video",
      title: "完整视频",
      description: currentVideo.title,
    },
    {
      id: "current-notes",
      type: "note",
      title: "当前笔记",
      description: "用户笔记内容",
    },
    ...currentVideo.prerequisites.flatMap((module) =>
      module.knowledgePoints.map((point) => ({
        id: point.id,
        type: "knowledge_point" as const,
        title: point.title,
        description: point.description,
        timestamp: point.timestamp,
      }))
    ),
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: inputValue,
      createdAt: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      // 调用 AI 服务
      const response = await aiService.query({
        message: userMessage.content,
        context: {
          videoTime: videoTime,
          selectedContexts: selectedContexts,
          previousMessages: messages.map((msg) => ({
            type: msg.type,
            content: msg.content,
          })),
        },
      });

      if (response.error) {
        throw new Error(response.error);
      }

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        type: "ai",
        content: response.response,
        createdAt: new Date(),
      };

      setMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      console.error("AI 查询失败:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "ai",
        content: "抱歉，AI 写作助手暂时不可用，请稍后再试。",
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const insertResponseToEditor = (response: string) => {
    onInsertResponse(response);
  };

  return (
    <div className="w-full max-w-2xl mx-auto border border-border rounded-lg bg-background shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <h3 className="font-semibold text-sm">AI 写作助手</h3>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <div className="h-64 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-8">
            <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>让 AI 帮你写作和扩展内容</p>
            <p className="text-xs mt-1">可以使用 @ 引用相关内容</p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                message.type === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted border border-border"
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              {message.type === "ai" && (
                <div className="mt-2 pt-2 border-t border-border/50">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => insertResponseToEditor(message.content)}
                    className="h-6 text-xs px-2"
                  >
                    插入到笔记
                  </Button>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-muted border border-border rounded-lg px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                </div>
                <span className="text-muted-foreground">AI 正在写作...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border bg-background/95 backdrop-blur-sm">
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
              title="选择上下文"
            >
              <AtSign className="w-4 h-4" />
            </Button>

            {/* Context 选择器显示区域 */}
            <div className="relative flex-1 flex items-center">
              {/* 显示已选择的上下文 */}
              {selectedContexts.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  <AnimatePresence>
                    {selectedContexts.map((context) => {
                      // 为"当前视频时间点"动态更新显示内容
                      const isCurrentVideoTime = context.id === "current-video-time";
                      const displayTitle = isCurrentVideoTime ? `视频时间点写作` : context.title;
                      const displayTimestamp = isCurrentVideoTime ? videoTime : context.timestamp;

                      return (
                        <motion.div
                          key={context.id}
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.2 }}
                          className="flex items-center gap-2 px-2 py-1 bg-muted rounded-md text-xs"
                        >
                          {getContextIcon(context.type)}
                          <span className="font-medium">{displayTitle}</span>
                          {displayTimestamp !== undefined && (
                            <span
                              className="text-muted-foreground flex items-center gap-1 cursor-pointer hover:text-primary transition-colors"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleJumpToTime(displayTimestamp);
                              }}
                              title="点击跳转到此时间点"
                            >
                              <Clock className="w-3 h-3" />
                              {formatTime(displayTimestamp)}
                            </span>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-4 w-4 ml-auto"
                            onClick={() => removeContext(context.id)}
                          >
                            <X className="w-2.5 h-2.5" />
                          </Button>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                </div>
              )}

              {/* 时间显示 */}
              {selectedContexts.length === 0 && videoTime !== undefined && (
                <span className="text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded">
                  当前：{formatTime(videoTime)}
                </span>
              )}

              {/* 弹出菜单 */}
              <AnimatePresence>
                {contextMenuOpen && (
                  <motion.div
                    ref={contextMenuRef}
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="absolute bottom-full left-0 mb-2 z-30"
                  >
                    <Card className="w-80 max-h-80 overflow-y-auto p-4">
                      <h3 className="font-semibold mb-3">选择上下文</h3>
                      <div className="space-y-2">
                        {availableContexts.map((context) => {
                          const isSelected = selectedContexts.find((ctx) => ctx.id === context.id);
                          return (
                            <Button
                              key={context.id}
                              variant={isSelected ? "secondary" : "ghost"}
                              className="w-full justify-start h-auto p-3"
                              onClick={() => handleAddContext(context)}
                              disabled={!!isSelected}
                            >
                              <div className="flex items-center gap-3 w-full">
                                {getContextIcon(context.type)}
                                <div className="flex-1 text-left">
                                  <div className="font-medium">{context.title}</div>
                                  {context.description && (
                                    <div className="text-xs text-muted-foreground">
                                      {context.description}
                                    </div>
                                  )}
                                </div>
                                {context.timestamp !== undefined && (
                                  <span
                                    className="text-xs text-muted-foreground flex items-center gap-1 cursor-pointer hover:text-primary transition-colors"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleJumpToTime(context.timestamp!);
                                    }}
                                    title="点击跳转到此时间点"
                                  >
                                    <Clock className="w-3 h-3" />
                                    {formatTime(context.timestamp)}
                                  </span>
                                )}
                              </div>
                            </Button>
                          );
                        })}
                      </div>
                    </Card>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* 轻微分割线 */}
          <div className="h-px bg-border/30 mx-3" />

          {/* 输入框区域 */}
          <form onSubmit={handleSubmit}>
            <div className="flex items-end gap-3 px-3 pb-3 pt-2 border-0 shadow-none">
              {/* 输入框 */}
              <div className="flex-1 relative border-0 shadow-none">
                <Textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="描述你想要写的内容..."
                  className="w-full min-h-[24px] max-h-[120px] resize-none border-none outline-none bg-transparent p-0 text-sm placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 focus:border-none focus:outline-none focus:shadow-none hover:border-none hover:shadow-none shadow-none scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent leading-6"
                  style={{
                    height: "24px",
                    border: "none",
                    outline: "none",
                    boxShadow: "none",
                    borderRadius: "0",
                  }}
                  disabled={isLoading}
                />
              </div>

              {/* 发送按钮 */}
              <motion.div
                className="flex-shrink-0"
                whileHover={!isLoading ? { scale: 1.02 } : {}}
                whileTap={!isLoading ? { scale: 0.98 } : {}}
                transition={{ duration: 0.15, ease: "easeOut" }}
              >
                <Button
                  type="submit"
                  disabled={!inputValue.trim() || isLoading}
                  size="sm"
                  className={`h-7 w-7 p-0 rounded-md border-0 transition-all duration-150 ${
                    inputValue.trim() && !isLoading
                      ? "bg-[#5B9BD5] hover:bg-[#4A8BC2] shadow-sm"
                      : "bg-gray-300 hover:bg-gray-400"
                  } disabled:cursor-not-allowed`}
                >
                  {isLoading ? (
                    <LoadingDots size="sm" className="text-white" />
                  ) : (
                    <ArrowUp
                      className={`w-4 h-4 ${
                        inputValue.trim() && !isLoading ? "text-white" : "text-gray-500"
                      }`}
                    />
                  )}
                </Button>
              </motion.div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
