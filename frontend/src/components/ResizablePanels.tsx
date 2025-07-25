"use client";

import { Button } from "@/components/ui/button";
import { Home, Video } from "lucide-react";
import { useRouter } from "next/navigation";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { VideoPlayer } from "./VideoPlayer";
import { ChatPanel } from "./ChatPanel";
import { useAppStore } from "@/store";

export function ResizablePanels() {
  const router = useRouter();
  const { currentVideo } = useAppStore();

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
        
        <div className="text-sm text-muted-foreground">
          AI 视频学习助手
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1">
        <PanelGroup direction="horizontal" className="h-full">
          <Panel defaultSize={65} minSize={30}>
            <div className="h-full p-6 overflow-y-auto">
              <VideoPlayer />
            </div>
          </Panel>
          <PanelResizeHandle />
          <Panel defaultSize={35} minSize={25}>
            <div className="h-full">
              <ChatPanel />
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
}
