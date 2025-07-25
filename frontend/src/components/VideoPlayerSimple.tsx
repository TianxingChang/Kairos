"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
import { useAppStore } from "@/store";
import type { VideoPlayerControl } from "@/types";

const ReactPlayer = dynamic(() => import("react-player"), {
  ssr: false,
});

export function VideoPlayerSimple() {
  const { currentVideo, setCurrentVideoTime } = useAppStore();
  const [mounted, setMounted] = useState(false);
  const [playerReady, setPlayerReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState(0);
  const playerRef = useRef<{ 
    getCurrentTime: () => number;
    seekTo: (time: number, type?: string) => void;
    getInternalPlayer: () => {
      playVideo?: () => void;
      pauseVideo?: () => void;
    };
  } | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 智能同步播放器时间到 store
  const updateVideoTime = useCallback((forceUpdate = false) => {
    if (!playerRef.current) return;
    
    const currentTime = Math.floor(playerRef.current.getCurrentTime());
    
    // 立即更新条件：强制更新 或 时间变化超过10秒
    if (forceUpdate || currentTime - lastUpdateTime >= 10) {
      setCurrentVideoTime(currentTime);
      setLastUpdateTime(currentTime);
    }
  }, [lastUpdateTime, setCurrentVideoTime]);

  // 定期检查时间更新（播放时每秒检查，暂停时不检查）
  useEffect(() => {
    if (!mounted || !playerReady) return;
    
    let interval: NodeJS.Timeout;
    
    if (isPlaying) {
      interval = setInterval(() => {
        updateVideoTime();
      }, 1000);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [mounted, playerReady, isPlaying, updateVideoTime]);

  // 暴露播放器控制方法给全局使用
  useEffect(() => {
    if (!mounted || !playerReady) return;
    
    const videoPlayerControl: VideoPlayerControl = {
      seekTo: (time: number) => {
        if (playerRef.current) {
          playerRef.current.seekTo(time, 'seconds');
          // 跳转后立即更新时间
          setTimeout(() => updateVideoTime(true), 100);
        }
      },
      getCurrentTime: () => {
        if (playerRef.current) {
          return playerRef.current.getCurrentTime();
        }
        return 0;
      },
      play: () => {
        if (playerRef.current) {
          const internalPlayer = playerRef.current.getInternalPlayer();
          internalPlayer?.playVideo?.();
          setIsPlaying(true);
        }
      },
      pause: () => {
        if (playerRef.current) {
          const internalPlayer = playerRef.current.getInternalPlayer();
          internalPlayer?.pauseVideo?.();
          setIsPlaying(false);
          // 暂停时立即更新时间
          updateVideoTime(true);
        }
      }
    };
    window.videoPlayer = videoPlayerControl;
  }, [mounted, playerReady, updateVideoTime]);

  if (!mounted) {
    return (
      <div className="w-full h-full bg-gray-200 rounded-xl flex items-center justify-center">
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full rounded-xl overflow-hidden">
      <ReactPlayer
        ref={playerRef}
        url={currentVideo.url}
        width="100%"
        height="100%"
        controls
        playing={false}
        style={{ 
          borderRadius: '0.75rem',
          overflow: 'hidden'
        }}
        onProgress={(state) => {
          // 暂停状态下的任何进度变化都视为拖动，立即更新
          if (!isPlaying) {
            setCurrentVideoTime(Math.floor(state.playedSeconds));
            setLastUpdateTime(Math.floor(state.playedSeconds));
          }
          // 播放状态下由定时器控制更新频率
        }}
        onPlay={() => {
          setIsPlaying(true);
          updateVideoTime(true); // 开始播放时立即更新一次
        }}
        onPause={() => {
          setIsPlaying(false);
          updateVideoTime(true); // 暂停时立即更新
        }}
        onSeek={() => {
          // 拖动结束时确保更新（双重保险）
          setTimeout(() => updateVideoTime(true), 50);
        }}
        onReady={() => {
          console.log('Video player ready:', currentVideo.url);
          setPlayerReady(true);
          updateVideoTime(true); // 播放器准备好时更新一次
        }}
        onError={(error) => {
          console.error('Video player error:', error);
        }}
      />
    </div>
  );
}