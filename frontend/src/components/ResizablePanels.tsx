"use client";

import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { VideoPlayer } from "./VideoPlayer";
import { ChatPanel } from "./ChatPanel";

export function ResizablePanels() {
  return (
    <div className="h-screen w-full">
      <PanelGroup direction="horizontal" className="min-h-screen rounded-lg border">
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
  );
}
