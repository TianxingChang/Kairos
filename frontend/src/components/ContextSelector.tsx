"use client";

import { useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAppStore } from "@/store";
import type { ContextItem } from "@/types";
import { X, Clock, FileText, Video, BookOpen } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ContextSelectorProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

export function ContextSelector({ isOpen, setIsOpen }: ContextSelectorProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  const { selectedContexts, currentVideo, currentVideoTime, addContext, removeContext } =
    useAppStore();

  // 点击外部关闭菜单 & ESC 键关闭菜单
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, setIsOpen]);

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

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const availableContexts: ContextItem[] = [
    {
      id: "current-video-time",
      type: "video",
      title: `视频时间点提问`,
      description: currentVideo.title,
      timestamp: currentVideoTime,
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

  const handleAddContext = (context: ContextItem) => {
    if (!selectedContexts.find((ctx) => ctx.id === context.id)) {
      addContext(context);
    }
    setIsOpen(false);
  };

  const handleJumpToTime = (timestamp: number) => {
    // 使用全局播放器控制方法跳转到指定时间
    if (typeof window !== 'undefined' && window.videoPlayer) {
      window.videoPlayer.seekTo(timestamp);
    }
  };

  return (
    <div className="relative">
      {/* Context 显示区域 */}
      {selectedContexts.length > 0 && (
        <div className="mb-3 space-y-2">
          <AnimatePresence>
            {selectedContexts.map((context) => {
              // 为"当前视频时间点"动态更新显示内容
              const isCurrentVideoTime = context.id === "current-video-time";
              const displayTitle = isCurrentVideoTime 
                ? `视频时间点提问`
                : context.title;
              const displayTimestamp = isCurrentVideoTime 
                ? currentVideoTime 
                : context.timestamp;
              

              return (
                <motion.div
                  key={context.id}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="flex items-center gap-2 px-3 py-2 bg-muted rounded-lg text-sm"
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
                    className="h-5 w-5 ml-auto"
                    onClick={() => removeContext(context.id)}
                  >
                    <X className="w-3 h-3" />
                  </Button>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}

      {/* 弹出菜单 */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={menuRef}
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
  );
}
