"use client";

import { useEffect, useState, useRef } from "react";
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

  // 定期同步播放器时间到 store
  useEffect(() => {
    if (!mounted || !playerReady) return;
    
    const interval = setInterval(() => {
      if (playerRef.current) {
        const currentTime = playerRef.current.getCurrentTime();
        setCurrentVideoTime(Math.floor(currentTime));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [setCurrentVideoTime, mounted, playerReady]);

  // 暴露播放器控制方法给全局使用
  useEffect(() => {
    if (!mounted || !playerReady) return;
    
    const videoPlayerControl: VideoPlayerControl = {
      seekTo: (time: number) => {
        if (playerRef.current) {
          playerRef.current.seekTo(time, 'seconds');
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
        }
      },
      pause: () => {
        if (playerRef.current) {
          const internalPlayer = playerRef.current.getInternalPlayer();
          internalPlayer?.pauseVideo?.();
        }
      }
    };
    window.videoPlayer = videoPlayerControl;
  }, [mounted, playerReady]);

  if (!mounted) {
    return (
      <div className="aspect-video w-full bg-gray-200 flex items-center justify-center">
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div className="aspect-video w-full">
      <ReactPlayer
        ref={playerRef}
        url={currentVideo.url}
        width="100%"
        height="100%"
        controls
        playing={false}
        onProgress={(state) => {
          setCurrentVideoTime(Math.floor(state.playedSeconds));
        }}
        onReady={() => {
          console.log('Video player ready:', currentVideo.url);
          setPlayerReady(true);
        }}
        onError={(error) => {
          console.error('Video player error:', error);
        }}
      />
    </div>
  );
}