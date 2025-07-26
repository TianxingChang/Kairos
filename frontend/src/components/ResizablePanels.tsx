"use client";

import React, { useState, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Home, Video, MessageCircle, NotebookPen, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { VideoPlayer } from "./VideoPlayer";
import { ChatPanel } from "./ChatPanel";
import { useAppStore } from "@/store";
import { motion, AnimatePresence } from "framer-motion";

// VideoPlayer容器组件，避免重新渲染
const VideoPlayerContainer = React.memo(() => {
  return <VideoPlayer />;
});
VideoPlayerContainer.displayName = "VideoPlayerContainer";

export function ResizablePanels() {
  const router = useRouter();
  const { currentVideo, currentMode, setCurrentMode } = useAppStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [videoWidth, setVideoWidth] = useState(72);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const toggleSidebar = (mode: "chat" | "notes") => {
    setCurrentMode(mode);
    setSidebarOpen(true);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!sidebarOpen) return;
      setIsDragging(true);
      e.preventDefault();
    },
    [sidebarOpen]
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;

      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const newWidth = ((e.clientX - rect.left) / rect.width) * 100;

      // 限制宽度范围
      const clampedWidth = Math.max(30, Math.min(80, newWidth));
      setVideoWidth(clampedWidth);
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // 添加全局鼠标事件监听
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    } else {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div className="h-screen w-full flex flex-col">
      {/* Top Bar */}
      <div className="h-16 border-b bg-background/95 backdrop-blur-sm flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center">
          <Button variant="outline" size="sm" onClick={() => router.push("/")}>
            <Home className="w-4 h-4 mr-2" />
            重新选择视频
          </Button>
        </div>

        <div className="flex items-center space-x-2 text-sm text-muted-foreground">
          <Video className="w-4 h-4" />
          <span className="max-w-md truncate">{currentVideo.title}</span>
        </div>

        <motion.div
          className="flex items-center space-x-2 relative"
          layout
          transition={{ duration: 0.3, ease: "easeInOut" }}
        >
          <AnimatePresence mode="popLayout">
            {!sidebarOpen ? (
              // 折叠状态：显示提问和笔记按钮
              <motion.div
                key="collapsed"
                layout
                initial={{ x: 30, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: -30, opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="flex items-center space-x-2"
              >
                <Button variant="outline" size="sm" onClick={() => toggleSidebar("chat")}>
                  <MessageCircle className="w-4 h-4 mr-1" />
                  提问
                </Button>
                <Button variant="outline" size="sm" onClick={() => toggleSidebar("notes")}>
                  <NotebookPen className="w-4 h-4 mr-1" />
                  笔记
                </Button>
              </motion.div>
            ) : (
              // 展开状态：显示模式切换按钮 + 折叠按钮
              <motion.div
                key="expanded"
                layout
                initial={{ x: -30, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: 30, opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="flex items-center space-x-2"
              >
                <Button
                  variant={currentMode === "chat" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCurrentMode("chat")}
                >
                  <MessageCircle className="w-4 h-4 mr-1" />
                  提问
                </Button>
                <Button
                  variant={currentMode === "notes" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCurrentMode("notes")}
                >
                  <NotebookPen className="w-4 h-4 mr-1" />
                  笔记
                </Button>
                <div className="w-px h-4 bg-border mx-1" />
                <Button variant="ghost" size="sm" onClick={closeSidebar}>
                  <ChevronRight className="w-4 h-4 mr-1" />
                  收起
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Main Content */}
      <div ref={containerRef} className="flex-1 overflow-hidden relative">
        {/* 拖拽时的全屏遮罩 */}
        {isDragging && <div className="absolute inset-0 z-50 cursor-col-resize bg-transparent" />}

        <motion.div
          animate={{ x: sidebarOpen ? 0 : 0 }}
          transition={{ duration: isDragging ? 0 : 0.4, ease: "easeInOut" }}
          className="h-full w-full flex"
        >
          {/* 视频区域 - 始终存在，避免重新渲染 */}
          <motion.div
            animate={{
              width: sidebarOpen ? `${videoWidth}%` : "100%",
            }}
            transition={{ duration: isDragging ? 0 : 0.4, ease: "easeInOut" }}
            className="h-full overflow-y-auto"
          >
            <div
              className={`h-full transition-all duration-300 ${
                sidebarOpen
                  ? "px-4 py-6"
                  : "px-6 py-6 sm:px-8 md:px-12 lg:px-16 xl:px-20 2xl:px-24 3xl:px-32"
              }`}
            >
              <VideoPlayerContainer />
            </div>
          </motion.div>

          {/* 分割线和侧边栏 - 从右侧滑入 */}
          <motion.div
            animate={{
              width: sidebarOpen ? `${100 - videoWidth}%` : "0%",
            }}
            transition={{ duration: isDragging ? 0 : 0.4, ease: "easeInOut" }}
            className="h-full overflow-hidden flex"
          >
            {sidebarOpen && (
              <>
                <div
                  className="w-px bg-border cursor-col-resize flex-shrink-0 relative"
                  onMouseDown={handleMouseDown}
                >
                  {/* 扩大拖拽区域 */}
                  <div className="absolute inset-y-0 -left-1 -right-1 w-3" />
                </div>
                <div className="flex-1 overflow-hidden">
                  <ChatPanel />
                </div>
              </>
            )}
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
