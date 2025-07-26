"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
import { useAppStore } from "@/store";
import type { VideoPlayerControl } from "@/types";
import html2canvas from "html2canvas";

const ReactPlayer = dynamic(() => import("react-player"), {
  ssr: false,
});

// 工具函数：提取YouTube视频ID
function extractYouTubeVideoId(url: string): string | null {
  const regex =
    /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
  const match = url.match(regex);
  return match ? match[1] : null;
}

// ReactPlayer专用截图方案
async function reactPlayerScreenshot(
  currentTime: number,
  video: { url: string; title: string; description: string },
  playerRef: React.RefObject<{ getCurrentTime: () => number; getInternalPlayer: () => unknown }>,
  containerRef: React.RefObject<HTMLDivElement>
): Promise<string> {
  console.log("🎬 ReactPlayer专用截图开始...");

  // 方案1：ReactPlayer原生video元素访问
  try {
    console.log("✅ 方案1：ReactPlayer原生video元素截图");
    const screenshot = await captureReactPlayerFrame(playerRef, currentTime, video.title);
    if (screenshot) return screenshot;
  } catch (error) {
    console.log("❌ 方案1失败:", error);
  }

  // 方案2：深度DOM查找video元素
  try {
    console.log("🔍 方案2：深度DOM查找video元素");
    const screenshot = await deepDOMVideoCapture(containerRef, currentTime, video.title);
    if (screenshot) return screenshot;
  } catch (error) {
    console.log("❌ 方案2失败:", error);
  }

  // 方案3：ReactPlayer wrapper element截图
  try {
    console.log("📦 方案3：ReactPlayer wrapper截图");
    const screenshot = await captureReactPlayerWrapper(playerRef, currentTime, video.title);
    if (screenshot) return screenshot;
  } catch (error) {
    console.log("❌ 方案3失败:", error);
  }

  // 方案4：HTML2Canvas + ReactPlayer特殊处理
  try {
    if (containerRef.current) {
      console.log("🎯 方案4：HTML2Canvas + ReactPlayer特殊处理");
      const screenshot = await capturePlayerWithHtml2Canvas(
        containerRef.current,
        currentTime,
        video.title
      );
      if (screenshot) return screenshot;
    }
  } catch (error) {
    console.log("❌ 方案4失败:", error);
  }

  // 方案5：YouTube API + 时间叠加（针对YouTube视频）
  try {
    if (video.url && (video.url.includes("youtube.com") || video.url.includes("youtu.be"))) {
      console.log("📺 方案5：YouTube缩略图增强");
      const videoId = extractYouTubeVideoId(video.url);
      if (videoId) {
        const screenshot = await tryMultipleYoutubeThumbnails(videoId, currentTime, video.title);
        if (screenshot) return screenshot;
      }
    }
  } catch (error) {
    console.log("❌ 方案5失败:", error);
  }

  // 兜底方案：精美占位符
  console.log("🎨 所有方案失败，使用精美占位符");
  return createBeautifulPlaceholder(currentTime, video.title);
}

// ReactPlayer专用方案1：原生video元素访问
async function captureReactPlayerFrame(
  playerRef: React.RefObject<{ getCurrentTime: () => number; getInternalPlayer: () => unknown }>,
  currentTime: number,
  videoTitle: string
): Promise<string | null> {
  if (!playerRef.current) return null;

  try {
    console.log("🔍 尝试获取ReactPlayer内部播放器...");
    const internalPlayer = playerRef.current.getInternalPlayer();

    console.log("📋 内部播放器类型:", internalPlayer?.constructor?.name);
    console.log("📋 内部播放器对象:", internalPlayer);

    // 直接检查是否是video元素
    if (internalPlayer instanceof HTMLVideoElement) {
      console.log("✅ 找到HTMLVideoElement，尝试截图");
      return await captureVideoElementFrame(internalPlayer, currentTime, videoTitle);
    }

    // 检查是否是iframe（YouTube等）
    if (internalPlayer instanceof HTMLIFrameElement) {
      console.log("📺 检测到iframe，无法直接访问视频内容");
      return null;
    }

    // 检查是否有video属性或方法
    if (internalPlayer && typeof internalPlayer === "object") {
      const playerObj = internalPlayer as Record<string, unknown>;

      // 尝试查找video相关属性
      if (playerObj.video && playerObj.video instanceof HTMLVideoElement) {
        console.log("✅ 找到player.video元素");
        return await captureVideoElementFrame(playerObj.video, currentTime, videoTitle);
      }

      // 尝试查找其他可能的video引用
      for (const key of Object.keys(playerObj)) {
        const value = playerObj[key];
        if (value instanceof HTMLVideoElement) {
          console.log(`✅ 找到${key}中的video元素`);
          return await captureVideoElementFrame(value, currentTime, videoTitle);
        }
      }
    }
  } catch (error) {
    console.error("ReactPlayer内部访问失败:", error);
  }

  return null;
}

// ReactPlayer专用方案2：深度DOM查找
async function deepDOMVideoCapture(
  containerRef: React.RefObject<HTMLDivElement>,
  currentTime: number,
  videoTitle: string
): Promise<string | null> {
  if (!containerRef.current) return null;

  try {
    // 在容器内深度查找所有video元素
    const videoElements = containerRef.current.querySelectorAll("video");
    console.log(`🔍 在容器内找到 ${videoElements.length} 个video元素`);

    for (let i = 0; i < videoElements.length; i++) {
      const video = videoElements[i];
      console.log(`📹 尝试video元素 ${i + 1}:`, {
        src: video.src,
        currentSrc: video.currentSrc,
        readyState: video.readyState,
        videoWidth: video.videoWidth,
        videoHeight: video.videoHeight,
        paused: video.paused,
        currentTime: video.currentTime,
      });

      // 检查video是否准备好
      if (video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
        console.log(`✅ video元素 ${i + 1} 准备就绪，尝试截图`);
        const screenshot = await captureVideoElementFrame(video, currentTime, videoTitle);
        if (screenshot) return screenshot;
      }
    }
  } catch (error) {
    console.error("深度DOM查找失败:", error);
  }

  return null;
}

// ReactPlayer专用方案3：wrapper元素截图
async function captureReactPlayerWrapper(
  playerRef: React.RefObject<{ getCurrentTime: () => number; getInternalPlayer: () => unknown }>,
  currentTime: number,
  videoTitle: string
): Promise<string | null> {
  if (!playerRef.current) return null;

  try {
    // ReactPlayer通常会有wrapper属性
    const playerObj = playerRef.current as Record<string, unknown>;
    const wrapper = playerObj.wrapper;

    if (wrapper && wrapper instanceof HTMLElement) {
      console.log("📦 找到ReactPlayer wrapper元素");

      // 在wrapper中查找video元素
      const videoElement = wrapper.querySelector("video");
      if (videoElement && videoElement instanceof HTMLVideoElement) {
        console.log("✅ 在wrapper中找到video元素");
        return await captureVideoElementFrame(videoElement, currentTime, videoTitle);
      }

      // 如果没有video元素，尝试截取整个wrapper
      console.log("📸 尝试截取整个wrapper");
      return await html2canvas(wrapper, {
        useCORS: true,
        allowTaint: true,
        scale: 1,
        logging: false,
        backgroundColor: "#000000",
      }).then((canvas) => {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          addTimeOverlay(ctx, canvas, currentTime, videoTitle);
        }
        return canvas.toDataURL("image/png");
      });
    }
  } catch (error) {
    console.error("ReactPlayer wrapper截图失败:", error);
  }

  return null;
}

// 通用video元素截图
async function captureVideoElementFrame(
  videoElement: HTMLVideoElement,
  currentTime: number,
  videoTitle: string
): Promise<string | null> {
  try {
    console.log("📹 开始截取video元素帧:", {
      videoWidth: videoElement.videoWidth,
      videoHeight: videoElement.videoHeight,
      currentTime: videoElement.currentTime,
      readyState: videoElement.readyState,
      paused: videoElement.paused,
    });

    // 确保video已经加载
    if (videoElement.readyState < 2) {
      console.log("⏳ 等待video加载...");
      await new Promise((resolve) => {
        const checkLoaded = () => {
          if (videoElement.readyState >= 2) {
            resolve(null);
          } else {
            setTimeout(checkLoaded, 100);
          }
        };
        checkLoaded();
      });
    }

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    if (!ctx) {
      console.error("无法创建canvas context");
      return null;
    }

    // 设置canvas尺寸
    canvas.width = videoElement.videoWidth || videoElement.clientWidth || 800;
    canvas.height = videoElement.videoHeight || videoElement.clientHeight || 450;

    console.log("🎨 Canvas尺寸:", canvas.width, "x", canvas.height);

    // 绘制当前视频帧
    ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    // 添加时间叠加层
    await addTimeOverlay(ctx, canvas, currentTime, videoTitle);

    const dataURL = canvas.toDataURL("image/png");
    console.log("✅ 视频帧截图成功");
    return dataURL;
  } catch (error) {
    console.error("视频元素截图失败:", error);
    return null;
  }
}

// 方案1：直接截取video元素 (已被captureVideoElementFrame替代)
async function _captureVideoFrame(
  videoElement: HTMLVideoElement,
  currentTime: number,
  videoTitle: string
): Promise<string | null> {
  try {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    if (!ctx) return null;

    // 设置canvas尺寸
    canvas.width = videoElement.videoWidth || videoElement.clientWidth || 800;
    canvas.height = videoElement.videoHeight || videoElement.clientHeight || 450;

    // 绘制视频帧
    ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    // 添加时间标记
    await addTimeOverlay(ctx, canvas, currentTime, videoTitle);

    return canvas.toDataURL("image/png");
  } catch (error) {
    console.error("Video frame capture failed:", error);
    return null;
  }
}

// 方案2：HTML2Canvas截取播放器
async function capturePlayerWithHtml2Canvas(
  container: HTMLElement,
  currentTime: number,
  videoTitle: string
): Promise<string | null> {
  try {
    const canvas = await html2canvas(container, {
      useCORS: true,
      allowTaint: true,
      scale: 1,
      logging: false,
      backgroundColor: "#000000",
      ignoreElements: (element) => {
        // 忽略某些UI元素
        return element.classList.contains("ignore-screenshot");
      },
    });

    // 添加时间标记
    const ctx = canvas.getContext("2d");
    if (ctx) {
      await addTimeOverlay(ctx, canvas, currentTime, videoTitle);
    }

    return canvas.toDataURL("image/png");
  } catch (error) {
    console.error("HTML2Canvas capture failed:", error);
    return null;
  }
}

// 方案3：尝试多种YouTube缩略图
async function tryMultipleYoutubeThumbnails(
  videoId: string,
  currentTime: number,
  videoTitle: string
): Promise<string | null> {
  const thumbnailUrls = [
    `https://i.ytimg.com/vi/${videoId}/maxresdefault.jpg`,
    `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
    `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`,
    `https://i.ytimg.com/vi/${videoId}/sddefault.jpg`,
  ];

  for (const url of thumbnailUrls) {
    try {
      const enhanced = await createEnhancedThumbnail(url, currentTime, videoTitle);
      if (enhanced) return enhanced;
    } catch (error) {
      console.log(`缩略图 ${url} 加载失败`, error);
    }
  }

  return null;
}

// 方案4：Screen Capture API (未使用)
async function _tryScreenCapture(currentTime: number, videoTitle: string): Promise<string | null> {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      return null;
    }

    // 请求屏幕共享
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
    });

    // 创建video元素来显示流
    const video = document.createElement("video");
    video.srcObject = stream;
    video.play();

    return new Promise((resolve) => {
      video.addEventListener("loadedmetadata", () => {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        if (!ctx) {
          resolve(null);
          return;
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // 绘制帧
        ctx.drawImage(video, 0, 0);

        // 停止流
        stream.getTracks().forEach((track) => track.stop());

        // 添加时间标记
        addTimeOverlay(ctx, canvas, currentTime, videoTitle).then(() => {
          resolve(canvas.toDataURL("image/png"));
        });
      });
    });
  } catch (error) {
    console.error("Screen capture failed:", error);
    return null;
  }
}

// 添加时间叠加层
async function addTimeOverlay(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  currentTime: number,
  videoTitle: string
): Promise<void> {
  // 添加半透明遮罩
  ctx.fillStyle = "rgba(0, 0, 0, 0.1)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // 时间格式化
  const minutes = Math.floor(currentTime / 60);
  const seconds = Math.floor(currentTime % 60);
  const timeText = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  // 右下角时间戳
  const timeBoxWidth = 120;
  const timeBoxHeight = 40;
  const margin = 20;

  ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
  ctx.fillRect(
    canvas.width - timeBoxWidth - margin,
    canvas.height - timeBoxHeight - margin,
    timeBoxWidth,
    timeBoxHeight
  );

  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 18px Arial";
  ctx.textAlign = "center";
  ctx.fillText(
    timeText,
    canvas.width - timeBoxWidth / 2 - margin,
    canvas.height - timeBoxHeight / 2 - margin + 6
  );

  // 左上角视频标题
  const maxTitleLength = 50;
  const shortTitle =
    videoTitle.length > maxTitleLength
      ? videoTitle.substring(0, maxTitleLength) + "..."
      : videoTitle;

  ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
  ctx.fillRect(margin, margin, shortTitle.length * 8 + 20, 35);

  ctx.fillStyle = "#ffffff";
  ctx.font = "14px Arial";
  ctx.textAlign = "left";
  ctx.fillText(shortTitle, margin + 10, margin + 22);

  // 截图标识
  ctx.fillStyle = "rgba(37, 99, 235, 0.9)";
  ctx.fillRect(canvas.width - 100 - margin, margin, 100, 30);

  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 12px Arial";
  ctx.textAlign = "center";
  ctx.fillText("📸 截图", canvas.width - 50 - margin, margin + 20);
}

// 工具函数：创建增强的YouTube缩略图
async function createEnhancedThumbnail(
  thumbnailUrl: string,
  currentTime: number,
  _videoTitle: string
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";

    img.onload = () => {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");

      canvas.width = img.width;
      canvas.height = img.height;

      if (ctx) {
        // 绘制缩略图
        ctx.drawImage(img, 0, 0);

        // 添加半透明遮罩
        ctx.fillStyle = "rgba(0, 0, 0, 0.4)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // 添加时间标记
        const minutes = Math.floor(currentTime / 60);
        const seconds = Math.floor(currentTime % 60);
        const timeText = `${minutes}:${seconds.toString().padStart(2, "0")}`;

        // 中央时间显示
        ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
        ctx.fillRect(canvas.width / 2 - 100, canvas.height / 2 - 40, 200, 80);

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 36px Arial";
        ctx.textAlign = "center";
        ctx.fillText(timeText, canvas.width / 2, canvas.height / 2 + 5);

        ctx.font = "16px Arial";
        ctx.fillText("视频截图", canvas.width / 2, canvas.height / 2 + 30);

        // 右下角时间戳
        ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
        ctx.fillRect(canvas.width - 120, canvas.height - 40, 110, 30);

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 16px Arial";
        ctx.textAlign = "center";
        ctx.fillText(timeText, canvas.width - 65, canvas.height - 20);

        const dataURL = canvas.toDataURL("image/png");
        resolve(dataURL);
      } else {
        reject(new Error("无法创建canvas上下文"));
      }
    };

    img.onerror = () => {
      reject(new Error("缩略图加载失败"));
    };

    img.src = thumbnailUrl;
  });
}

// 工具函数：创建美观的占位符截图
function createBeautifulPlaceholder(currentTime: number, videoTitle: string): string {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");

  canvas.width = 800;
  canvas.height = 450;

  if (!ctx) {
    throw new Error("无法创建canvas上下文");
  }

  // 创建渐变背景
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  gradient.addColorStop(0, "#667eea");
  gradient.addColorStop(1, "#764ba2");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // 添加视频图标
  ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
  ctx.beginPath();
  ctx.arc(canvas.width / 2, canvas.height / 2 - 40, 40, 0, 2 * Math.PI);
  ctx.fill();

  ctx.fillStyle = "#667eea";
  ctx.beginPath();
  ctx.moveTo(canvas.width / 2 - 15, canvas.height / 2 - 55);
  ctx.lineTo(canvas.width / 2 + 20, canvas.height / 2 - 40);
  ctx.lineTo(canvas.width / 2 - 15, canvas.height / 2 - 25);
  ctx.closePath();
  ctx.fill();

  // 添加标题
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 24px Arial";
  ctx.textAlign = "center";
  ctx.fillText("视频截图", canvas.width / 2, canvas.height / 2 + 20);

  // 添加精确时间信息
  const totalMinutes = Math.floor(currentTime / 60);
  const totalSeconds = Math.floor(currentTime % 60);
  const milliseconds = Math.floor((currentTime % 1) * 100);
  const timeText = `${totalMinutes}:${totalSeconds.toString().padStart(2, "0")}.${milliseconds
    .toString()
    .padStart(2, "0")}`;

  ctx.font = "18px Arial";
  ctx.fillText(`播放时间: ${timeText}`, canvas.width / 2, canvas.height / 2 + 50);

  // 添加视频标题
  const shortTitle = videoTitle.length > 40 ? videoTitle.substring(0, 40) + "..." : videoTitle;
  ctx.font = "16px Arial";
  ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
  ctx.fillText(shortTitle, canvas.width / 2, canvas.height / 2 + 80);

  return canvas.toDataURL("image/png");
}

export function VideoPlayerSimple() {
  const { currentVideo, setCurrentVideoTime } = useAppStore();
  const [mounted, setMounted] = useState(false);
  const [playerReady, setPlayerReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState(0);
  const playerRef = useRef<{
    getCurrentTime: () => number;
    seekTo: (time: number, type?: string) => void;
    getInternalPlayer: () => unknown;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 智能同步播放器时间到 store
  const updateVideoTime = useCallback(
    (forceUpdate = false) => {
      if (!playerRef.current) return;

      const currentTime = Math.floor(playerRef.current.getCurrentTime());

      // 立即更新条件：强制更新 或 时间变化超过10秒
      if (forceUpdate || currentTime - lastUpdateTime >= 10) {
        setCurrentVideoTime(currentTime);
        setLastUpdateTime(currentTime);
      }
    },
    [lastUpdateTime, setCurrentVideoTime]
  );

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
          playerRef.current.seekTo(time, "seconds");
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
          const internalPlayer = playerRef.current.getInternalPlayer() as any;
          internalPlayer?.playVideo?.();
          setIsPlaying(true);
        }
      },
      pause: () => {
        if (playerRef.current) {
          const internalPlayer = playerRef.current.getInternalPlayer() as any;
          internalPlayer?.pauseVideo?.();
          setIsPlaying(false);
          // 暂停时立即更新时间
          updateVideoTime(true);
        }
      },
      captureFrame: async () => {
        if (!playerRef.current) {
          throw new Error("播放器未准备就绪");
        }

        const currentTime = playerRef.current.getCurrentTime();
        console.log(`📸 开始高级截图，时间: ${currentTime.toFixed(2)}秒`);

        // 使用ReactPlayer专用截图方案
        return await reactPlayerScreenshot(currentTime, currentVideo, playerRef, containerRef);
      },
    };
    window.videoPlayer = videoPlayerControl;
  }, [mounted, playerReady, updateVideoTime, currentVideo]);

  if (!mounted) {
    return (
      <div className="w-full h-full bg-gray-200 rounded-xl flex items-center justify-center">
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full rounded-xl overflow-hidden">
      <ReactPlayer
        ref={playerRef}
        url={currentVideo.url}
        width="100%"
        height="100%"
        controls
        playing={false}
        config={{
          file: {
            attributes: {
              crossOrigin: "anonymous",
            },
          },
          youtube: {
            playerVars: {
              enablejsapi: 1,
              origin: typeof window !== "undefined" ? window.location.origin : "",
            },
          },
        }}
        style={{
          borderRadius: "0.75rem",
          overflow: "hidden",
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
          console.log("Video player ready:", currentVideo.url);
          setPlayerReady(true);
          updateVideoTime(true); // 播放器准备好时更新一次
        }}
        onError={(error) => {
          console.error("Video player error:", error);
        }}
      />
    </div>
  );
}
