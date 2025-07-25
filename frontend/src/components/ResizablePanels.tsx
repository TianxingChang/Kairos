"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Home, Video, MessageCircle, NotebookPen, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { VideoPlayer } from "./VideoPlayer";
import { ChatPanel } from "./ChatPanel";
import { useAppStore } from "@/store";
import { motion, AnimatePresence } from "framer-motion";

export function ResizablePanels() {
  const router = useRouter();
  const { currentVideo, currentMode, setCurrentMode } = useAppStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="h-screen w-full flex flex-col">
      {/* Top Bar */}
      <div className="h-16 border-b bg-background/95 backdrop-blur-sm flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push('/')}
          >
            <Home className="w-4 h-4 mr-2" />
            重新选择视频
          </Button>
        </div>
        
        <div className="flex items-center space-x-2 text-sm text-muted-foreground">
          <Video className="w-4 h-4" />
          <span className="max-w-md truncate">{currentVideo.title}</span>
        </div>
        
        <motion.div 
          className="flex items-center space-x-2"
          layout
          transition={{ duration: 0.2 }}
        >
          <AnimatePresence mode="wait">
            {!sidebarOpen ? (
              // 折叠状态：显示提问和笔记按钮
              <motion.div
                key="collapsed"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
                className="flex items-center space-x-2"
              >
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setCurrentMode("chat");
                    setSidebarOpen(true);
                  }}
                >
                  <MessageCircle className="w-4 h-4 mr-1" />
                  提问
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setCurrentMode("notes");
                    setSidebarOpen(true);
                  }}
                >
                  <NotebookPen className="w-4 h-4 mr-1" />
                  笔记
                </Button>
              </motion.div>
            ) : (
              // 展开状态：显示模式切换按钮 + 折叠按钮
              <motion.div
                key="expanded"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
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
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSidebarOpen(false)}
                >
                  <ChevronRight className="w-4 h-4 mr-1" />
                  折叠
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Main Content */}
      <div className="flex-1">
        <AnimatePresence mode="wait">
          {sidebarOpen ? (
            // 侧边栏展开时：使用可调整大小的面板
            <motion.div
              key="panels"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="h-full"
            >
              <PanelGroup direction="horizontal" className="h-full">
                <Panel defaultSize={65} minSize={35}>
                  <div className="h-full px-4 py-6 overflow-y-auto">
                    <VideoPlayer />
                  </div>
                </Panel>
                <PanelResizeHandle className="w-px bg-border hover:bg-border/80 transition-colors duration-200 cursor-col-resize" />
                <Panel defaultSize={35} minSize={25} maxSize={65}>
                  <ChatPanel />
                </Panel>
              </PanelGroup>
            </motion.div>
          ) : (
            // 侧边栏折叠时：全屏视频播放器
            <motion.div
              key="fullscreen"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="h-full px-6 py-6 sm:px-8 md:px-12 lg:px-16 xl:px-20 2xl:px-24 3xl:px-32 overflow-y-auto"
            >
              <VideoPlayer />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
