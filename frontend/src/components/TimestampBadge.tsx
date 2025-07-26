"use client";

import { useCallback } from "react";

interface TimestampBadgeProps {
  timestamp: number;
  className?: string;
}

export function TimestampBadge({ timestamp, className = "" }: TimestampBadgeProps) {
  const seekToVideoTime = useCallback(() => {
    // 使用全局视频播放器控制
    if (typeof window !== "undefined" && window.videoPlayer) {
      window.videoPlayer.seekTo(timestamp);
    }
  }, [timestamp]);

  // 格式化时间戳为 MM:SS 格式
  const formatTimestamp = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

  return (
    <span
      onClick={seekToVideoTime}
      className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-full cursor-pointer transition-colors duration-200 select-none ${className}`}
      title={`跳转到 ${formatTimestamp(timestamp)}`}
    >
      ⏰ {formatTimestamp(timestamp)}
    </span>
  );
}
