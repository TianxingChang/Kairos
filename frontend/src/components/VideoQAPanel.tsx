"use client";

import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ArrowUp, X, Clock, Bot, Video, AlertCircle, CheckCircle, Upload, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { LoadingDots } from "@/components/ui/loading-dots";
import { useAppStore } from "@/store";
import { useAutoResize } from "@/hooks";
import { videoQAService, type VideoQAResponse, type FullVideoResponse } from "@/services/videoQAService";

interface VideoQAPanelProps {
  onClose: () => void;
  onInsertResponse: (response: string) => void;
  currentVideoTime?: number;
  videoId?: string;
}

interface Message {
  id: string;
  type: "user" | "ai" | "system";
  content: string;
  timestamp?: number;
  videoInfo?: {
    video_id: string;
    timestamp: number;
    formatted_time: string;
  };
  contextInfo?: {
    context_transcript: string;
    duration: number;
  };
  createdAt: Date;
}

type TabType = "qa" | "full-qa" | "upload";

type QAMode = "timestamp" | "full" | "full-agent";

export function VideoQAPanel({
  onClose,
  onInsertResponse,
  currentVideoTime,
  videoId: propVideoId,
}: VideoQAPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("qa");
  const [qaMode, setQaMode] = useState<QAMode>("timestamp");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [timestampInput, setTimestampInput] = useState("");
  const [videoIdInput, setVideoIdInput] = useState(propVideoId || "");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{
    status: 'idle' | 'uploading' | 'processing' | 'ready' | 'error';
    message: string;
    videoId?: string;
  }>({ status: 'idle', message: '' });

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  // 如果有当前视频时间，自动填充时间戳
  useEffect(() => {
    if (videoTime !== undefined && !timestampInput) {
      setTimestampInput(formatTime(videoTime));
    }
  }, [videoTime, timestampInput]);

  // 如果有传入的videoId，自动填充
  useEffect(() => {
    if (propVideoId && !videoIdInput) {
      setVideoIdInput(propVideoId);
    }
  }, [propVideoId, videoIdInput]);

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  };

  const parseTimeToSeconds = (timeStr: string): number => {
    try {
      return videoQAService.parseTimestampToSeconds(timeStr);
    } catch {
      // 如果解析失败，尝试直接转换为数字
      const num = parseFloat(timeStr);
      return isNaN(num) ? 0 : num;
    }
  };

  const handleVideoQA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !videoIdInput.trim() || isLoading) return;

    // 时间点模式需要时间戳
    if (qaMode === "timestamp" && !timestampInput.trim()) return;

    const timestamp = qaMode === "timestamp" ? parseTimeToSeconds(timestampInput) : 0;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: inputValue,
      timestamp: qaMode === "timestamp" ? timestamp : undefined,
      videoInfo: qaMode === "timestamp" ? {
        video_id: videoIdInput,
        timestamp,
        formatted_time: timestampInput,
      } : {
        video_id: videoIdInput,
        timestamp: 0,
        formatted_time: "完整视频",
      },
      createdAt: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      if (qaMode === "timestamp") {
        // 时间点问答
        const response: VideoQAResponse = await videoQAService.askQuestion({
          video_id: videoIdInput,
          timestamp,
          question: inputValue,
          user_id: 'frontend_user',
        });

        if (!response.success) {
          throw new Error(response.error || '问答失败');
        }

        const aiResponse: Message = {
          id: (Date.now() + 1).toString(),
          type: "ai",
          content: response.answer,
          videoInfo: {
            video_id: response.video_info.video_id,
            timestamp,
            formatted_time: response.timestamp_info.target_formatted,
          },
          contextInfo: {
            context_transcript: response.context_transcript,
            duration: response.timestamp_info.context_duration,
          },
          createdAt: new Date(),
        };

        setMessages((prev) => [...prev, aiResponse]);
      } else {
        // 完整视频问答 - 默认使用Agent模式以获得更好的分析能力
        const useAgent = qaMode === "full-agent" || qaMode === "full"; // 两种完整视频模式都使用Agent
        
        const response: FullVideoResponse = useAgent
          ? await videoQAService.askFullVideoQuestionWithAgent({
              video_id: videoIdInput,
              question: inputValue,
              user_id: 'frontend_user',
              session_id: `session_${Date.now()}`, // 确保提供session_id
            })
          : await videoQAService.askFullVideoQuestion({
              video_id: videoIdInput,
              question: inputValue,
              user_id: 'frontend_user',
            });

        if (!response.success) {
          throw new Error(response.error || '完整视频问答失败');
        }

        const aiResponse: Message = {
          id: (Date.now() + 1).toString(),
          type: "ai",
          content: response.answer,
          videoInfo: {
            video_id: response.video_info.video_id,
            timestamp: 0,
            formatted_time: qaMode === "full-agent" ? "Agent完整视频" : "完整视频",
          },
          contextInfo: {
            context_transcript: response.full_transcript,
            duration: response.video_info.duration || 0,
          },
          createdAt: new Date(),
        };

        setMessages((prev) => [...prev, aiResponse]);
      }
    } catch (error) {
      console.error("视频问答失败:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "ai",
        content: `抱歉，视频问答失败: ${error instanceof Error ? error.message : '未知错误'}`,
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleYouTubeUpload = async () => {
    if (!youtubeUrl.trim() || isUploading) return;

    setIsUploading(true);
    setUploadStatus({ status: 'uploading', message: '正在上传视频...' });

    try {
      const response = await videoQAService.uploadYouTubeVideo({
        url: youtubeUrl,
        user_id: 'frontend_user',
      });

      if (!response.success) {
        throw new Error(response.error || '上传失败');
      }

      // 自动填充视频ID
      setVideoIdInput(response.video_id);
      
      if (response.status === 'ready') {
        setUploadStatus({
          status: 'ready',
          message: `视频已准备就绪: ${response.video_info?.title || response.video_id}`,
          videoId: response.video_id,
        });
        // 自动切换到问答Tab
        setActiveTab('qa');
      } else if (response.status === 'processing') {
        setUploadStatus({
          status: 'processing',
          message: response.message,
          videoId: response.video_id,
        });
        // 开始轮询状态
        pollVideoStatus(response.video_id);
      }

    } catch (error) {
      console.error("YouTube上传失败:", error);
      setUploadStatus({
        status: 'error',
        message: `上传失败: ${error instanceof Error ? error.message : '未知错误'}`,
      });
    } finally {
      setIsUploading(false);
    }
  };

  const pollVideoStatus = async (videoId: string) => {
    try {
      const status = await videoQAService.pollVideoStatus(videoId, 20, 10000);
      
      if (status.status === 'ready') {
        setUploadStatus({
          status: 'ready',
          message: `视频已准备就绪: ${status.video_info?.title || videoId}`,
          videoId,
        });
        // 自动切换到问答Tab
        setActiveTab('qa');
      } else {
        setUploadStatus({
          status: 'error',
          message: '视频处理失败或超时',
        });
      }
    } catch (error) {
      setUploadStatus({
        status: 'error',
        message: '状态检查失败',
      });
    }
  };

  const extractVideoIdFromUrl = () => {
    const videoId = videoQAService.extractVideoId(youtubeUrl);
    if (videoId) {
      setVideoIdInput(videoId);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleVideoQA(e);
    }
  };

  const insertResponseToEditor = (response: string) => {
    onInsertResponse(response);
  };

  const getStatusIcon = () => {
    switch (uploadStatus.status) {
      case 'uploading':
      case 'processing':
        return <LoadingDots size="sm" />;
      case 'ready':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto border border-border rounded-lg bg-background shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <Video className="h-5 w-5 text-primary" />
          <h3 className="font-semibold text-sm">视频时间点问答</h3>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        <Button
          variant={activeTab === "qa" ? "secondary" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("qa")}
          className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary"
        >
          视频问答
        </Button>
        <Button
          variant={activeTab === "upload" ? "secondary" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("upload")}
          className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary"
        >
          上传视频
        </Button>
      </div>

      {/* Content */}
      {activeTab === "qa" ? (
        <>
          {/* QA Mode Selector */}
          <div className="p-4 border-b border-border bg-muted/20">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium">问答模式:</span>
            </div>
            <div className="flex gap-2">
              <Button
                variant={qaMode === "timestamp" ? "default" : "outline"}
                size="sm"
                onClick={() => setQaMode("timestamp")}
                className="text-xs"
              >
                <Clock className="w-3 h-3 mr-1" />
                时间点问答
              </Button>
              <Button
                variant={qaMode === "full" ? "default" : "outline"}
                size="sm"
                onClick={() => setQaMode("full")}
                className="text-xs"
              >
                <Video className="w-3 h-3 mr-1" />
                完整视频(Agent)
              </Button>
              <Button
                variant={qaMode === "full-agent" ? "default" : "outline"}
                size="sm"
                onClick={() => setQaMode("full-agent")}
                className="text-xs"
              >
                <Bot className="w-3 h-3 mr-1" />
                高级Agent
              </Button>
            </div>
          </div>
          {/* Messages */}
          <div className="h-64 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-muted-foreground text-sm py-8">
                <Video className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>
                  {qaMode === "timestamp" && "基于视频时间点内容回答问题"}
                  {qaMode === "full" && "基于完整视频内容回答问题"}
                  {qaMode === "full-agent" && "使用智能Agent进行完整视频问答"}
                </p>
                <p className="text-xs mt-1">
                  {qaMode === "timestamp" && "输入视频ID、时间点和问题开始对话"}
                  {(qaMode === "full" || qaMode === "full-agent") && "输入视频ID和问题开始对话"}
                </p>
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
                  {message.videoInfo && message.type === "user" && (
                    <div className="mb-2 pb-2 border-b border-border/30 text-xs opacity-80">
                      <div className="flex items-center gap-2">
                        <Video className="w-3 h-3" />
                        <span>{message.videoInfo.video_id}</span>
                        <Clock className="w-3 h-3" />
                        <span>{message.videoInfo.formatted_time}</span>
                      </div>
                    </div>
                  )}
                  
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  
                  {message.contextInfo && (
                    <div className="mt-2 pt-2 border-t border-border/30 text-xs opacity-80">
                      <details className="cursor-pointer">
                        <summary className="font-medium">查看转录上下文</summary>
                        <div className="mt-1 p-2 bg-muted/50 rounded text-xs font-mono whitespace-pre-wrap">
                          {message.contextInfo.context_transcript}
                        </div>
                      </details>
                    </div>
                  )}
                  
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
                    <LoadingDots size="sm" />
                    <span className="text-muted-foreground">AI 正在分析视频内容...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* QA Input */}
          <div className="p-4 border-t border-border bg-background/95 backdrop-blur-sm">
            <form onSubmit={handleVideoQA} className="space-y-3">
              {/* Video ID and Timestamp (conditional) */}
              <div className="flex gap-2">
                <Input
                  placeholder="视频ID (例如: dQw4w9WgXcQ)"
                  value={videoIdInput}
                  onChange={(e) => setVideoIdInput(e.target.value)}
                  className="flex-1"
                  disabled={isLoading}
                />
                {qaMode === "timestamp" && (
                  <Input
                    placeholder="时间点 (例如: 1:23)"
                    value={timestampInput}
                    onChange={(e) => setTimestampInput(e.target.value)}
                    className="w-24"
                    disabled={isLoading}
                  />
                )}
              </div>

              {/* Question Input */}
              <div className="flex gap-2">
                <Textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    qaMode === "timestamp" 
                      ? "请输入你关于这个时间点的问题..."
                      : "请输入你关于整个视频的问题..."
                  }
                  className="flex-1 min-h-[40px] max-h-[120px] resize-none"
                  disabled={isLoading}
                />
                <Button
                  type="submit"
                  disabled={
                    !inputValue.trim() || 
                    !videoIdInput.trim() || 
                    (qaMode === "timestamp" && !timestampInput.trim()) || 
                    isLoading
                  }
                  size="sm"
                  className="h-10 w-10 p-0"
                >
                  {isLoading ? (
                    <LoadingDots size="sm" />
                  ) : (
                    <ArrowUp className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </form>
          </div>
        </>
      ) : (
        /* Upload Tab */
        <div className="p-4 space-y-4">
          <div className="text-center py-8">
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-semibold mb-2">上传 YouTube 视频</h3>
            <p className="text-sm text-muted-foreground mb-4">
              粘贴 YouTube 链接，我们会自动处理转录文本
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex gap-2">
              <Input
                placeholder="YouTube 视频链接"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                className="flex-1"
                disabled={isUploading}
              />
              <Button
                onClick={extractVideoIdFromUrl}
                variant="outline"
                size="sm"
                disabled={!youtubeUrl.trim()}
                title="提取视频ID"
              >
                <Search className="w-4 h-4" />
              </Button>
            </div>

            <Button
              onClick={handleYouTubeUpload}
              disabled={!youtubeUrl.trim() || isUploading}
              className="w-full"
            >
              {isUploading ? (
                <>
                  <LoadingDots size="sm" className="mr-2" />
                  处理中...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  上传并处理视频
                </>
              )}
            </Button>

            {uploadStatus.message && (
              <div className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
                uploadStatus.status === 'error' ? 'bg-red-50 text-red-700 border border-red-200' :
                uploadStatus.status === 'ready' ? 'bg-green-50 text-green-700 border border-green-200' :
                'bg-blue-50 text-blue-700 border border-blue-200'
              }`}>
                {getStatusIcon()}
                <span>{uploadStatus.message}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}