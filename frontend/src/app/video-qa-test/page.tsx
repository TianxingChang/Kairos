"use client";

import React, { useState } from "react";
import { VideoQAPanel } from "@/components/VideoQAPanel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Video, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

export default function VideoQATestPage() {
  const router = useRouter();
  const [showPanel, setShowPanel] = useState(false);
  const [testResponse, setTestResponse] = useState("");

  const handleInsertResponse = (response: string) => {
    setTestResponse(response);
    console.log("AI Response inserted:", response);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/")}
              className="flex items-center space-x-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>返回首页</span>
            </Button>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
              <Video className="w-6 h-6 text-purple-600" />
              <span>视频问答测试页面</span>
            </h1>
          </div>
        </div>

        {/* Test Instructions */}
        <Card className="p-6 mb-6 bg-white">
          <h2 className="text-lg font-semibold mb-4">测试说明</h2>
          <div className="space-y-3 text-sm text-gray-600">
            <p>
              <strong>1. 点击下方按钮</strong> 打开视频问答面板
            </p>
            <p>
              <strong>2. 上传视频</strong> (可以使用示例: https://www.youtube.com/watch?v=dQw4w9WgXcQ)
            </p>
            <p>
              <strong>3. 输入时间点</strong> (例如: 0:30 或 30)
            </p>
            <p>
              <strong>4. 提出问题</strong> (例如: "这个时间点在说什么?")
            </p>
            <p>
              <strong>5. 查看AI回答</strong> 并可以插入到下方文本区域
            </p>
          </div>
        </Card>

        {/* Test Controls */}
        <div className="flex gap-4 mb-6">
          <Button
            onClick={() => setShowPanel(true)}
            className="bg-purple-600 hover:bg-purple-700 text-white"
          >
            <Video className="w-4 h-4 mr-2" />
            打开视频问答面板
          </Button>
          
          <Button
            variant="outline"
            onClick={() => setTestResponse("")}
          >
            清空测试结果
          </Button>
        </div>

        {/* Test Results */}
        <Card className="p-6 bg-white">
          <h3 className="text-lg font-semibold mb-4">测试结果</h3>
          <div className="min-h-[200px] p-4 border border-gray-200 rounded-lg bg-gray-50">
            {testResponse ? (
              <div className="space-y-2">
                <div className="text-sm text-gray-500">AI回答:</div>
                <div className="text-gray-900 whitespace-pre-wrap">{testResponse}</div>
              </div>
            ) : (
              <div className="text-gray-400 text-center py-8">
                AI回答将显示在这里...
              </div>
            )}
          </div>
        </Card>

        {/* API Status */}
        <Card className="p-6 mt-6 bg-white">
          <h3 className="text-lg font-semibold mb-4">API连接状态</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>后端API: http://localhost:8000</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span>视频问答接口: /v1/frontend/video-qa/ask</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <span>YouTube上传接口: /v1/frontend/youtube/upload</span>
            </div>
          </div>
        </Card>

        {/* Video QA Panel */}
        {showPanel && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="w-full max-w-4xl">
              <VideoQAPanel
                onClose={() => setShowPanel(false)}
                onInsertResponse={handleInsertResponse}
                currentVideoTime={30} // 示例时间
                videoId="dQw4w9WgXcQ" // 示例视频ID
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}